"""Authenticate every generated demo role and check access boundaries over HTTP.

Uses local synthetic credentials only. Never prints passwords, OTPs or tokens.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse
import httpx
import pyotp

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8014")
    args = parser.parse_args()
    parsed = urlparse(args.base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.username or parsed.password:
        parser.error("Only loopback HTTP demo servers are accepted")
    rows = json.loads((ROOT / ".local/saas-demo/campus-role-logins.json").read_text(encoding="utf-8"))
    results = []
    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=20, follow_redirects=False) as client:
        for account in rows:
            body = {"email": account["email"], "password": account["password"]}
            if account.get("authenticator_setup_key"):
                body["otp_code"] = pyotp.TOTP(account["authenticator_setup_key"]).now()
            login = client.post("/api/v1/auth/login", json=body)
            result = {"role": account["role"], "login_status": login.status_code, "checks": []}
            if login.status_code == 200:
                token = login.json()["access_token"]
                headers = {"Authorization": "Bearer " + token}
                expected = 200 if account["account_role"] in {"admin", "superadmin"} else 403
                for path, status in [("/api/v1/auth/me", 200), ("/api/v1/admin/operations/runtime", expected)]:
                    response = client.get(path, headers=headers)
                    result["checks"].append({"path": path, "status": response.status_code, "expected": status,
                                             "passed": response.status_code == status})
            result["passed"] = login.status_code == 200 and all(c["passed"] for c in result["checks"])
            results.append(result)
    report = {"base_url": args.base_url, "passed": all(r["passed"] for r in results), "accounts": results,
              "scope": "Synthetic password/MFA login, own profile, global admin access boundary; not every feature acceptance"}
    path = ROOT / ".local/saas-demo/http-acceptance.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "accounts": len(results), "report": str(path)}))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
