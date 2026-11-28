#!/usr/bin/env bash
# Live class health check (about 10 s, read-only, starts nothing, prints no secrets).
# Run before a class or from cron:  bash e2e/live-class/healthcheck.sh
# Exit code 0 = all good, 1 = at least one check failed (each failure says what to do).
# Paths can be overridden with env vars for another host.
DEPLOY="${LC_DEPLOY_DIR:-/www/wwwroot/sasha_lms/sasha_lms/sasha_lms/deploy}"
WAF_SRC="${LC_WAF_SRC:-/opt/incubaseos/waf/Caddyfile}"
WAF_CONTAINER="${LC_WAF_CONTAINER:-incubaseos-coraza-1}"
LIVE_URL="${LC_LIVE_URL:-https://liveclass.sashainfinity.com}"
SITE_URL="${LC_SITE_URL:-https://sileos.sashainfinity.com}"

fail=0
ok()  { printf '  OK    %s\n' "$1"; }
bad() { printf '  FAIL  %s\n        -> %s\n' "$1" "$2"; fail=1; }
check() { # name, fix, command...
  local name="$1" fix="$2"; shift 2
  if "$@" >/dev/null 2>&1; then ok "$name"; else bad "$name" "$fix"; fi
}

echo "Live class health check ($(date '+%F %T'))"

echo "Video stack"
for c in sasha-jitsi-prosody sasha-jitsi-jicofo sasha-jitsi-jvb sasha-jitsi-web sasha-jitsi-jibri; do
  check "$c is running and healthy" "cd $DEPLOY && docker compose -p sasha-live -f compose.live.yml --env-file .env.live up -d  (always with --env-file)" \
    bash -c "[ \"\$(docker inspect -f '{{.State.Health.Status}}' $c 2>/dev/null)\" = healthy ]"
done

echo "Recording"
check "recorder joined the recording pool (Jibri brewery)" "restart it: docker restart sasha-jitsi-jibri, then look at: docker logs sasha-jitsi-jibri" \
  bash -c "docker logs sasha-jitsi-jibri 2>&1 | grep -q 'Joined MUC: jibribrewery'"
check "recorder login domain exists in prosody (recorder.meet.jitsi)" "set XMPP_HIDDEN_DOMAIN=recorder.meet.jitsi in $DEPLOY/.env.live and recreate prosody" \
  bash -c "docker exec sasha-jitsi-prosody grep -q 'VirtualHost \"recorder.meet.jitsi\"' /config/conf.d/jitsi-meet.cfg.lua"
check "Jicofo waits long enough for the recorder (reply-timeout 60 s)" "restore $DEPLOY/jitsi/jicofo/custom-jicofo.conf and restart jicofo" \
  grep -q 'reply-timeout = 60 seconds' "$DEPLOY/jitsi/jicofo/custom-jicofo.conf"
check "sound loopback module snd_aloop is loaded" "modprobe snd_aloop (it is persisted in /etc/modules-load.d/snd_aloop.conf)" \
  bash -c "lsmod | grep -q '^snd_aloop'"

echo "Moderator rights (students must not be moderators)"
check "token_affiliation module is configured in prosody" "set XMPP_MUC_MODULES=token_affiliation in $DEPLOY/.env.live and recreate prosody" \
  bash -c "docker exec sasha-jitsi-prosody grep -q token_affiliation /config/conf.d/jitsi-meet.cfg.lua"
check "Jicofo does not auto-promote users (override file is loaded)" "restore $DEPLOY/jitsi/jicofo/custom-jicofo.conf (authentication.enabled=false, enable-auto-owner=false) and restart jicofo" \
  bash -c "docker exec sasha-jitsi-jicofo grep -q 'enable-auto-owner = false' /config/custom-jicofo.conf && docker exec sasha-jitsi-jicofo grep -A1 'authentication' /config/custom-jicofo.conf | grep -q 'enabled = false' && docker logs sasha-jitsi-jicofo 2>&1 | grep -q 'Authentication service disabled'"

echo "Firewall and code submissions"
check "firewall container is running" "start $WAF_CONTAINER from the incubaseos project" \
  bash -c "[ \"\$(docker inspect -f '{{.State.Running}}' $WAF_CONTAINER 2>/dev/null)\" = true ]"
check "coding rule 1009001 is in the RUNNING firewall" "see SILEOS_KNOWLEDGE_BASE.md, section 9 (firewall rule for code)" \
  bash -c "docker exec $WAF_CONTAINER grep -q 'id:1009001' /etc/caddy/Caddyfile"
check "coding rule 1009001 is in the firewall SOURCE file (survives a rebuild)" "re-add the rule to $WAF_SRC" \
  grep -q 'id:1009001' "$WAF_SRC"
check "firewall still blocks an attack (path traversal gets 403)" "the firewall engine may be off: check SecRuleEngine in $WAF_SRC" \
  bash -c "[ \"\$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 '$SITE_URL/?q=<script>alert(1)</script>')\" = 403 ]"

echo "Public reachability"
check "call page answers over the public domain" "check nginx and Cloudflare for $LIVE_URL" \
  bash -c "[ \"\$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 $LIVE_URL/)\" = 200 ]"
check "call page can be embedded by the LMS (frame-ancestors lists sileos)" "add the LMS host to frame-ancestors in /etc/nginx/sites-enabled/sashainfinity-liveclass.conf" \
  bash -c "curl -sI --max-time 15 $LIVE_URL/ | grep -i content-security-policy | grep -q sileos.sashainfinity.com"
check "LMS site answers" "check the dev stack: docker compose ps" \
  bash -c "[ \"\$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 $SITE_URL/)\" = 200 ]"

echo
if [ "$fail" -eq 0 ]; then echo "ALL CHECKS PASSED"; else echo "SOME CHECKS FAILED (see FAIL lines above)"; fi
exit "$fail"
