"""
One-off backfill: mirror EXISTING Postgres users into Firebase Authentication.

Existing accounts (registered before the live /register -> Firebase sync was
added) are not present in Firebase, so they can't be managed there. This script
imports them, preserving their current password by importing the bcrypt hash
directly (Firebase's user-import API supports BCRYPT). Users keep logging in
with the same password — no reset required.

Social-login accounts (Google/LinkedIn) have a random non-bcrypt `user_pass`,
so they're imported WITHOUT a password hash — they continue to sign in via
their provider; this just makes sure the account record exists.

Stable uid: we key each Firebase user as `sasha-<postgres_id>` so re-running is
idempotent (import upserts by uid). Accounts already created in Firebase under a
different uid but the same email surface as EMAIL_EXISTS and are skipped.

Run inside the backend container:
    docker-compose exec backend python backfill_firebase_users.py --dry-run
    docker-compose exec backend python backfill_firebase_users.py
"""
import argparse
import sys

from app.core.database import SessionLocal
from app.core.firebase_admin import _ensure_initialized
from app.models.user import User


def main():
    parser = argparse.ArgumentParser(description="Backfill Postgres users into Firebase Auth")
    parser.add_argument("--dry-run", action="store_true", help="List what would be imported, change nothing")
    args = parser.parse_args()

    if not _ensure_initialized():
        print("ERROR: Firebase Admin SDK not available. "
              "Check FIREBASE_CREDENTIALS_PATH points at a valid service-account JSON.")
        sys.exit(1)

    from firebase_admin import auth as fb_auth

    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Found {len(users)} users in Postgres.")

        records = []
        with_pw = 0
        for u in users:
            if not u.user_email:
                continue
            pw = u.user_pass or ""
            kwargs = dict(
                uid=f"sasha-{u.id}",
                email=u.user_email,
                display_name=u.display_name or None,
                email_verified=bool(u.is_verified),
                disabled=not bool(u.is_active),
            )
            # Only bcrypt hashes ($2a/$2b/$2y) can be imported as passwords.
            if pw.startswith("$2"):
                # Firebase's bcrypt importer expects the `$2a$` identifier.
                # passlib emits `$2b$`; for standard (<72 byte ASCII) passwords
                # `$2a$` and `$2b$` verify identically, so normalize the prefix.
                normalized = "$2a$" + pw[4:] if pw[:4] in ("$2b$", "$2y$") else pw
                kwargs["password_hash"] = normalized.encode("utf-8")
                with_pw += 1
            records.append(fb_auth.ImportUserRecord(**kwargs))

        print(f"Prepared {len(records)} records ({with_pw} with importable bcrypt passwords, "
              f"{len(records) - with_pw} social/no-password).")

        if args.dry_run:
            print("\n[dry-run] sample of first 10:")
            for r in records[:10]:
                has_pw = "pw" if r.password_hash else "no-pw"
                print(f"  {r.uid:<12} {r.email:<40} {has_pw}")
            print("\n[dry-run] nothing was written.")
            return

        # BCRYPT importer — bcrypt hashes are self-contained (salt embedded),
        # so no separate salt/signer key is required.
        hash_alg = fb_auth.UserImportHash.bcrypt()

        total_ok = total_err = 0
        BATCH = 1000  # Firebase import_users hard limit per call
        for i in range(0, len(records), BATCH):
            batch = records[i:i + BATCH]
            result = fb_auth.import_users(batch, hash_alg=hash_alg)
            total_ok += result.success_count
            total_err += result.failure_count
            for err in result.errors:
                rec = batch[err.index]
                print(f"  SKIP {rec.email}: {err.reason}")

        print(f"\nDone. Imported/updated: {total_ok}, skipped/failed: {total_err}")
        print("Check Firebase Console -> Authentication -> Users.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
