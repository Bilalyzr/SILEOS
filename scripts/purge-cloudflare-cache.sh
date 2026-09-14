#!/bin/bash
# Purge Cloudflare cache after deployment
# Usage: ./scripts/purge-cloudflare-cache.sh

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check for Cloudflare credentials
if [ -z "$CLOUDFLARE_ZONE_ID" ] || [ -z "$CLOUDFLARE_API_TOKEN" ]; then
    echo "Error: CLOUDFLARE_ZONE_ID and CLOUDFLARE_API_TOKEN must be set"
    echo "Add these to your .env file or environment:"
    echo "  CLOUDFLARE_ZONE_ID=your_zone_id"
    echo "  CLOUDFLARE_API_TOKEN=your_api_token"
    exit 1
fi

echo "Purging Cloudflare cache for sashainfinity.com..."

# Purge everything
RESPONSE=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/purge_cache" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}')

# Check response
if echo "$RESPONSE" | grep -q '"success":true'; then
    echo "✓ Cache purged successfully"
else
    echo "✗ Failed to purge cache"
    echo "Response: $RESPONSE"
    exit 1
fi
