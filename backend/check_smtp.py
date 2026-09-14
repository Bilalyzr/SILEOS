"""
SMTP delivery diagnostic for Learn/auth verification email.

Run this ON THE HOST THAT RUNS THE BACKEND — that is the whole point. SMTP
credentials working from a laptop tells you nothing about whether the
production container can reach port 587; many VPS providers block outbound SMTP
by default, and that failure is invisible from anywhere else.

    docker-compose exec backend python check_smtp.py
    docker-compose exec backend python check_smtp.py --send you@example.com

Without --send it only connects, negotiates TLS and authenticates; nothing
leaves the server. With --send it delivers one real test message.
"""
import argparse
import socket
import ssl
import smtplib
import sys
from email.mime.text import MIMEText

from app.core.config import get_settings

settings = get_settings()


def ok(msg):
    print("  [ ok ] %s" % msg)


def fail(msg):
    print("  [FAIL] %s" % msg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--send",
        metavar="EMAIL",
        help="actually deliver a test message to this address",
    )
    args = parser.parse_args()

    host, port = settings.SMTP_HOST, settings.SMTP_PORT
    user, password = settings.SMTP_USER, settings.SMTP_PASSWORD

    print("\nConfiguration")
    print("  SMTP_HOST        = %r" % host)
    print("  SMTP_PORT        = %r" % port)
    print("  SMTP_USER        = %r" % user)
    print("  SMTP_PASSWORD    = %s" % ("<set, %d chars>" % len(password) if password else "<EMPTY>"))
    print("  EMAIL_FROM       = %r" % settings.EMAIL_FROM)
    print("  FRONTEND_URL     = %r" % settings.FRONTEND_URL)
    print("  AUTO_VERIFY_EMAIL= %r" % settings.AUTO_VERIFY_EMAIL)

    if not host or not user:
        print("\nSMTP is not configured. Every email is being silently dropped:")
        print("the send path logs a warning and returns success. Set SMTP_HOST")
        print("and SMTP_USER in the backend environment.")
        return 1

    if settings.AUTO_VERIFY_EMAIL:
        print("\nNote: AUTO_VERIFY_EMAIL is true, so registration marks accounts")
        print("verified and sends NO verification email at all. If users are")
        print("still being asked to verify, the running backend is not seeing")
        print("this value — check the container's env, not just the .env file.")

    print("\nConnectivity")
    try:
        ip = socket.gethostbyname(host)
        ok("DNS %s -> %s" % (host, ip))
    except Exception as e:
        fail("DNS lookup for %s: %s: %s" % (host, type(e).__name__, e))
        return 1

    try:
        server = smtplib.SMTP(host, port, timeout=20)
        ok("TCP connect to %s:%s" % (host, port))
    except Exception as e:
        fail("TCP connect to %s:%s — %s: %s" % (host, port, type(e).__name__, e))
        print("\n  This is the classic symptom of the provider blocking outbound")
        print("  port 587. Verify from this host with: nc -vz %s %s" % (host, port))
        return 1

    try:
        server.ehlo()
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        server.starttls(context=context)
        server.ehlo()
        ok("STARTTLS (certificate verification disabled — host is self-signed)")
    except Exception as e:
        fail("STARTTLS — %s: %s" % (type(e).__name__, e))
        return 1

    try:
        server.login(user, password)
        ok("AUTH as %s" % user)
    except Exception as e:
        fail("AUTH as %s — %s: %s" % (user, type(e).__name__, e))
        return 1

    if args.send:
        msg = MIMEText(
            "SMTP diagnostic from the SashaInfinity backend.\n\n"
            "If you are reading this, the backend host can deliver mail to "
            "this address, and a missing verification email is a template, "
            "trigger or spam-filter problem rather than a connectivity one.\n"
        )
        msg["Subject"] = "SashaInfinity SMTP diagnostic"
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = args.send
        try:
            refused = server.send_message(msg)
            if refused:
                fail("recipient refused: %r" % (refused,))
                return 1
            ok("test message accepted for %s" % args.send)
            print("\n  'Accepted' means this server took it, not that it was")
            print("  delivered. If it does not arrive, check the spam folder and")
            print("  then SPF/DKIM/DMARC for sashainfinity.com — that is the")
            print("  usual reason mail to Gmail vanishes without a bounce.")
        except Exception as e:
            fail("send — %s: %s" % (type(e).__name__, e))
            return 1
    else:
        print("\n  Auth works. Re-run with --send you@example.com to test delivery.")

    try:
        server.quit()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
