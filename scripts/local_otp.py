"""Print a fresh localhost-test TOTP code for the seeded admin accounts.

Local-only helper for the campus preview logins (see .local/campus-role-logins.json).
Waits for the start of a new 30s window so the printed code has maximum validity.

Usage (from the repository root):
    backend/.venv/Scripts/python scripts/local_otp.py            # both roles
    backend/.venv/Scripts/python scripts/local_otp.py superadmin # one role
    backend/.venv/Scripts/python scripts/local_otp.py --loop     # continuous ticker
"""
import sys
import time

import pyotp

ACCOUNTS = {
    "admin": (
        "Platform Admin  platform-admin@example.org",
        "BJPGXZ7D333XVMAO5QZLPYEHS3DLFHBN",
    ),
    "superadmin": (
        "Super Admin     platform-superadmin@example.org",
        "4TYTKH4GF764BPQSZ3TNHRWYTHT72HAL",
    ),
}


def fresh_code(key: str) -> str:
    """Return the code at the start of a new window (max remaining validity)."""
    remaining = 30 - int(time.time()) % 30
    if remaining < 25:
        time.sleep(remaining + 0.2)
    return pyotp.TOTP(key).now()


def main() -> None:
    args = [a.strip().lower() for a in sys.argv[1:]]
    loop = "--loop" in args
    wanted = [a for a in args if a in ACCOUNTS] or list(ACCOUNTS)

    if loop:
        print("Ctrl+C to stop. Codes rotate every 30s.")
        try:
            while True:
                stamp = time.strftime("%H:%M:%S")
                for name in wanted:
                    label, key = ACCOUNTS[name]
                    code = pyotp.TOTP(key).now()
                    left = 30 - int(time.time()) % 30
                    print(f"[{stamp}] {label}  code={code}  {left}s left")
                time.sleep(max(1, 30 - int(time.time()) % 30))
        except KeyboardInterrupt:
            return

    for name in wanted:
        label, key = ACCOUNTS[name]
        code = fresh_code(key)
        left = 30 - int(time.time()) % 30
        print(f"{label}  code={code}  (valid ~{left}s)")


if __name__ == "__main__":
    main()
