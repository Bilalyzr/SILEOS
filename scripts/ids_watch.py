#!/usr/bin/env python3
# =============================================================================
# ids_watch.py — lightweight IDS for SashaInfinity LMS (web + mobile API)
# =============================================================================
# Tails the app's security log and the edge nginx access log, detects abuse,
# and enforces bans by regenerating an nginx deny-list at the edge
# (deploy/nginx/conf.d/99-ids-deny.conf) followed by `nginx -s reload`.
# Covers web and mobile traffic — both hit the same edge/API.
#
# Feeds:
#   IDS_SECURITY_LOG  (default /logs/security.log)   — app SECURITY_EVENT +
#     "Response: ... Status: nnn ... IP: x" lines (real client IPs via XFF)
#   IDS_ACCESS_LOG    (default /logs/edge-nginx/access.log) — edge requests
#
# Rules (defaults, all env-tunable):
#   ATTACK_URI       instant ban   (.env/.git/wp-* probing, SQLi, traversal…)
#   SUSPICIOUS_PATTERN  instant ban (app-level SECURITY_EVENT)
#   AUTH_ABUSE       >=20 x 401/403 in 300s
#   RATE_ABUSE       >=10 x 429    in 60s
# Bans escalate: 1h -> 24h -> 30d for repeat offenders. Private/loopback IPs
# are never banned. Every decision is logged to IDS_ALERT_LOG as JSON.
#
# CLI:
#   ids_watch.py             watch mode (production)
#   ids_watch.py status      current ban table
#   ids_watch.py unban IP    lift a ban and reload edge
# =============================================================================
import fcntl
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------- config ----
def env(name, default):
    return os.environ.get(name, default)

SECURITY_LOG   = env("IDS_SECURITY_LOG", "/logs/security.log")
ACCESS_LOG     = env("IDS_ACCESS_LOG", "/logs/edge-nginx/access.log")
# The LIVE nginx (sasha_lms-nginx-1) logs access lines to stdout only —
# follow them via `docker logs` so SPA-level probes (/.env, /wp-admin …)
# that never reach the backend are still detected. Empty string disables.
NGINX_LOG_CONTAINER = env("IDS_NGINX_LOG_CONTAINER", "sasha_lms-nginx-1")
# Comma-separated: every nginx that fronts traffic gets the deny-list.
DENY_FILES     = [p.strip() for p in env(
    "IDS_DENY_FILES",
    "/deny/99-ids-deny.conf,/deny2/99-ids-deny.conf").split(",") if p.strip()]
RELOAD_CONTAINERS = [c.strip() for c in env(
    "IDS_RELOAD_CONTAINERS", "sasha-edge,sasha_lms-nginx-1").split(",") if c.strip()]
STATE_FILE     = env("IDS_STATE_FILE", "/state/state.json")
ALERT_LOG      = env("IDS_ALERT_LOG", "/logs/ids-alerts.log")
EDGE_CONTAINER = env("IDS_EDGE_CONTAINER", "sasha-edge")
DRY_RUN        = env("IDS_DRY_RUN", "0") == "1"

AUTH_FAIL_LIMIT  = int(env("IDS_AUTH_FAIL_LIMIT", 20))
AUTH_FAIL_WINDOW = int(env("IDS_AUTH_FAIL_WINDOW", 300))
RATE_LIMIT_HITS  = int(env("IDS_RATE_LIMIT_HITS", 10))
RATE_WINDOW      = int(env("IDS_RATE_WINDOW", 60))
ROTATE_MB        = int(env("IDS_ROTATE_MB", 100))

DENY_HEADER = """# =============================================================================
# MANAGED BY sasha-ids (scripts/ids_watch.py) — DO NOT EDIT BY HAND
# Banned client IPs. Changes propagate on the IDS's next nginx reload.
# Unban: docker exec sasha-ids python3 /app/ids_watch.py unban <ip>
#
# Real client IPs: traffic arrives via Cloudflare -> host nginx -> this
# nginx, so the socket peer is a private gateway address. Recover the true
# client from Cloudflare's header or the deny directives below would never
# match anything but the gateway.
# =============================================================================
set_real_ip_from 172.16.0.0/12;
set_real_ip_from 127.0.0.0/8;
real_ip_header CF-Connecting-IP;
real_ip_recursive on;
"""

# never ban loopback / private space (health checks, docker internals)
NEVER_BAN = [ipaddress.ip_network(n) for n in
             ("127.0.0.0/8", "::1/128", "10.0.0.0/8",
              "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16")]

ATTACK_URI_RE = re.compile(
    r"(\.env\b|\.git\b|wp-admin|wp-login|xmlrpc\.php|\.aws/|\.\./|"
    r"union[\s+]+select|/etc/passwd|<script|%3Cscript|php://filter|"
    r"\.sql\b|\.bak\b|/\.well-known/security)", re.I)

SEC_EVENT_RE  = re.compile(r"SECURITY_EVENT: (\{.*)\s*$")
RESPONSE_RE   = re.compile(r"Response: \S+ \S+ - Status: (\d{3}).*?IP: (\S+)")
REQUEST_RE    = re.compile(r"Request: (\S+) (\S+) from (\S+)")
ACCESS_RE     = re.compile(r'^(\S+) \S+ \S+ \[[^\]]+\] "(\S+) (\S+)[^"]*" (\d{3})')

BAN_STEPS = [timedelta(hours=1), timedelta(hours=24), timedelta(days=30)]

# ------------------------------------------------------------------ state ---
def now():
    return datetime.now(timezone.utc)

def iso(dt):
    return dt.isoformat()

def alert(kind, **kv):
    rec = {"ts": iso(now()), "event": kind, **kv}
    line = json.dumps(rec, default=str)
    print(f"[ids] {line}", flush=True)
    try:
        with open(ALERT_LOG, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}

def save_state(bans):
    tmp = STATE_FILE + ".tmp"
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(tmp, "w") as f:
        json.dump(bans, f, indent=1, sort_keys=True)
    os.replace(tmp, STATE_FILE)

def is_bannable(ip):
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not any(addr in net for net in NEVER_BAN)

def ban_ip(bans, ip, reason):
    if not is_bannable(ip):
        return False
    prev = bans.get(ip)
    strikes = (prev["strikes"] + 1) if prev else 1
    dur = BAN_STEPS[min(strikes - 1, len(BAN_STEPS) - 1)]
    bans[ip] = {
        "reason": reason,
        "strikes": strikes,
        "banned_at": iso(now()),
        "until": iso(now() + dur),
    }
    alert("BAN", ip=ip, reason=reason, strikes=strikes,
          until=bans[ip]["until"])
    return True

def sweep_expired(bans):
    t = now()
    expired = [ip for ip, b in bans.items()
               if datetime.fromisoformat(b["until"]) <= t]
    for ip in expired:
        del bans[ip]
        alert("EXPIRED", ip=ip)
    return bool(expired)

# ------------------------------------------------------------ enforcement ---
def render_deny(bans):
    lines = [DENY_HEADER]
    for ip in sorted(bans):
        b = bans[ip]
        lines.append(f"# {b['reason']} x{b['strikes']} until {b['until']}")
        lines.append(f"deny {ip};")
    lines.append("")
    return "\n".join(lines)

def apply_deny(bans):
    content = render_deny(bans)
    wrote = False
    for target in DENY_FILES:
        try:
            with open(target) as f:
                if f.read() == content:
                    continue  # nothing changed at this target
        except OSError:
            pass
        os.makedirs(os.path.dirname(target), exist_ok=True)
        tmp = target + ".tmp"
        with open(tmp, "w") as f:
            f.write(content)
        os.replace(tmp, target)
        wrote = True
    if not wrote:
        return False
    if DRY_RUN:
        alert("DRY_RUN_RELOAD_SKIPPED", bans=len(bans))
    else:
        for container in RELOAD_CONTAINERS:
            r = subprocess.run(["docker", "exec", container, "nginx", "-s", "reload"],
                               capture_output=True, text=True)
            if r.returncode != 0:
                alert("RELOAD_FAILED", container=container,
                      stderr=r.stderr.strip()[:300])
            else:
                alert("RELOADED", container=container, active_bans=len(bans))
    return True

# ------------------------------------------------------------------- feed ---
class LogTailer:
    """Follows a file from its end, surviving rotation/truncation."""
    def __init__(self, path):
        self.path = path
        self.f = None
        self.inode = None
        self._open_at_end()

    def _open_at_end(self):
        try:
            self.f = open(self.path, "r", errors="replace")
            self.f.seek(0, os.SEEK_END)
            self.inode = os.fstat(self.f.fileno()).st_ino
        except OSError:
            self.f = None
            self.inode = None

    def lines(self):
        if self.f is None:
            self._open_at_end()
            if self.f is None:
                return []
        try:
            if os.fstat(self.f.fileno()).st_ino != self.inode:
                raise OSError("rotated")
        except OSError:
            self._open_at_end()
            if self.f is None:
                return []
        pos_before = self.f.tell()
        out = [l for l in self.f.readlines() if l.endswith("\n")]
        # a trailing partial (newline-less) line: rewind so we re-read it whole
        consumed = self.f.tell() - pos_before
        kept = sum(len(l.encode()) for l in out)
        if consumed > kept:
            self.f.seek(pos_before + kept)
        return [l.rstrip("\n") for l in out]

# --------------------------------------------------------------- rotation ---
class DockerLogsTailer:
    """Non-blocking follower for `docker logs -f` of an nginx container."""
    def __init__(self, container):
        self.p = subprocess.Popen(
            ["docker", "logs", "-f", "--tail", "0", container],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        fd = self.p.stdout.fileno()
        fcntl.fcntl(fd, fcntl.F_SETFL,
                    fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK)
        self.buf = b""

    def lines(self):
        try:
            chunk = self.p.stdout.read(65536)
        except (OSError, ValueError):
            return []
        if not chunk:
            return []
        self.buf += chunk
        parts = self.buf.split(b"\n")
        self.buf = parts.pop()
        return [p.decode("utf-8", "replace") for p in parts if p]


def rotate_if_huge():
    try:
        if os.path.getsize(SECURITY_LOG) > ROTATE_MB * 1024 * 1024:
            shutil.copyfile(SECURITY_LOG, SECURITY_LOG + ".1")
            with open(SECURITY_LOG, "r+") as f:
                f.truncate(0)
            alert("ROTATED", file=SECURITY_LOG, max_mb=ROTATE_MB)
    except OSError:
        pass

# ------------------------------------------------------------------ watch ---
def watch():
    alert("START", security_log=SECURITY_LOG, access_log=ACCESS_LOG,
          deny_files=DENY_FILES, reload_containers=RELOAD_CONTAINERS,
          dry_run=DRY_RUN)
    bans = load_state()
    apply_deny(bans)  # enforce persisted bans after restart

    sec_tail = LogTailer(SECURITY_LOG)
    acc_tail = LogTailer(ACCESS_LOG)
    ngx_tail = (DockerLogsTailer(NGINX_LOG_CONTAINER)
                if NGINX_LOG_CONTAINER else None)
    events = defaultdict(lambda: defaultdict(deque))  # ip -> kind -> deque[ts]

    def note(ip, kind):
        if is_bannable(ip):
            dq = events[ip][kind]
            dq.append(time.time())

    def handle_access_line(line):
        nonlocal bans
        m = ACCESS_RE.match(line)
        if not m:
            return False
        ip, method, uri, status = m.groups()
        if ATTACK_URI_RE.search(uri) and method in ("GET", "POST", "HEAD"):
            return ban_ip(bans, ip, f"attack_uri:{uri[:80]}")
        if status in ("401", "403"):
            note(ip, "auth")
        elif status == "429":
            note(ip, "rate")
        return False

    last_sweep = time.time()
    while True:
        changed = False

        for line in sec_tail.lines():
            m = SEC_EVENT_RE.search(line)
            if m:
                try:
                    ev = json.loads(m.group(1))
                    ip = ev.get("client_ip")
                    etype = ev.get("event_type", "")
                    if ip:
                        if etype == "SUSPICIOUS_PATTERN":
                            changed |= ban_ip(bans, ip, f"suspicious_pattern:{etype}")
                        else:
                            note(ip, "auth")
                except ValueError:
                    pass
                continue
            # app-level request feed: real client IPs + URIs for EVERY hit,
            # independent of which nginx fronted the request
            m = REQUEST_RE.search(line)
            if m:
                method, uri, ip = m.groups()
                if ATTACK_URI_RE.search(uri) and method in ("GET", "POST", "HEAD"):
                    changed |= ban_ip(bans, ip, f"attack_uri:{uri[:80]}")
                continue
            m = RESPONSE_RE.search(line)
            if m:
                status, ip = m.group(1), m.group(2)
                if status in ("401", "403"):
                    note(ip, "auth")
                elif status == "429":
                    note(ip, "rate")

        for line in acc_tail.lines():
            changed |= handle_access_line(line)
        if ngx_tail:
            for line in ngx_tail.lines():
                changed |= handle_access_line(line)

        t = time.time()
        for ip in list(events):
            for kind in list(events[ip]):
                dq = events[ip][kind]
                limit = AUTH_FAIL_LIMIT if kind == "auth" else RATE_LIMIT_HITS
                window = AUTH_FAIL_WINDOW if kind == "auth" else RATE_WINDOW
                cutoff = t - window
                while dq and dq[0] < cutoff:
                    dq.popleft()
                if len(dq) >= limit:
                    changed |= ban_ip(bans, ip, f"{kind}_abuse:{len(dq)}_hits")
                    del events[ip][kind]

        if t - last_sweep > 60:
            # Re-read state so out-of-band CLI changes (unban) survive the
            # watcher's own saves. Every in-watcher mutation saves first, so
            # the file is authoritative at this point.
            bans = load_state()
            if sweep_expired(bans):
                changed = True
            rotate_if_huge()
            last_sweep = t
            save_state(bans)

        if changed:
            save_state(bans)
            apply_deny(bans)

        time.sleep(2)

# -------------------------------------------------------------------- cli ---
def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "watch"
    if cmd == "status":
        bans = load_state()
        if not bans:
            print("no active bans")
            return
        t = now()
        for ip, b in sorted(bans.items()):
            left = datetime.fromisoformat(b["until"]) - t
            print(f"{ip:20s} strikes={b['strikes']} "
                  f"left={int(left.total_seconds()//60)}m reason={b['reason']}")
    elif cmd == "unban" and len(sys.argv) > 2:
        ip = sys.argv[2]
        bans = load_state()
        if bans.pop(ip, None):
            save_state(bans)
            apply_deny(bans)
            alert("UNBAN", ip=ip)
            print(f"unbanned {ip}")
        else:
            print(f"{ip} not banned")
    elif cmd == "watch":
        watch()
    else:
        print(__doc__)
        sys.exit(2)

if __name__ == "__main__":
    main()
