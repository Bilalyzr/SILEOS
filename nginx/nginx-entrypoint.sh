#!/bin/sh
# Prerender.io token substitution script
# Runs automatically via /docker-entrypoint.d/

# Replace PRERENDER_TOKEN placeholder with actual token from environment
if [ ! -z "$PRERENDER_TOKEN" ]; then
  sed -i "s|YOUR_PRERENDER_TOKEN_HERE|$PRERENDER_TOKEN|g" /etc/nginx/conf.d/default.conf
  echo "Prerender token configured"
fi
