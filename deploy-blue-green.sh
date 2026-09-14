#!/bin/bash
# Blue-Green Deployment for SashaInfinity LMS
# Zero-downtime deployment with automatic rollback

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

cd /www/wwwroot/sasha_lms/sasha_lms/sasha_lms

# Load environment (POSTGRES_PASSWORD etc.) — fail closed if missing.
# A hardcoded DB password here drifted from the live volume's password and
# triggered the 2026-08-15 data-loss incident. Never hardcode it again.
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
else
    echo "[ERROR] .env not found — POSTGRES_PASSWORD is required" >&2
    exit 1
fi
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set in .env}"

BLUE_PORT=8081
GREEN_PORT=8082
NGINX_BLUE_CONF="/tmp/lms-blue.conf"
NGINX_GREEN_CONF="/tmp/lms-green.conf"
HEALTH_URL="http://localhost"
MAX_WAIT=60

# Detect current active
get_active_color() {
    if curl -sf "http://localhost:${BLUE_PORT}/health" > /dev/null 2>&1; then
        echo "blue"
    elif curl -sf "http://localhost:${GREEN_PORT}/health" > /dev/null 2>&1; then
        echo "green"
    else
        echo "none"
    fi
}

CURRENT=$(get_active_color)
DEPLOY_COLOR=$([ "$CURRENT" = "blue" ] && echo "green" || echo "blue")
OLD_COLOR=$CURRENT

log_info "Current active: $CURRENT, Deploying: $DEPLOY_COLOR"

# Step 1: Build frontend
log_step "Building frontend..."
cd frontend
npm install --legacy-peer-deps
npm run build --legacy-peer-deps
cd ..

# Step 2: Build production image with new tag
log_step "Building production image..."
TAG=$(date +%s)
docker build -f Dockerfile.production -t sashainfinity-lms:${TAG} --build-arg NODE_ENV=production .
docker tag sashainfinity-lms:${TAG} sashainfinity-lms:latest

# Step 3: Create deploy-specific compose override
log_step "Creating deploy config for ${DEPLOY_COLOR}..."

DEPLOY_PORT=$([ "$DEPLOY_COLOR" = "green" ] && echo "8082" || echo "8081")

cat > docker-compose.${DEPLOY_COLOR}.yml << EOF
version: '3.8'
services:
  sashainfinity-lms-${DEPLOY_COLOR}:
    image: sashainfinity-lms:${TAG}
    container_name: sashainfinity-lms-${DEPLOY_COLOR}
    ports:
      - "${DEPLOY_PORT}:80"
    environment:
      - DATABASE_URL=postgresql://tutor:\${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env}@postgres:5432/tutor_lms
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=\${SECRET_KEY}
      - JWT_SECRET=\${JWT_SECRET}
      - ADMIN_PASSWORD=\${ADMIN_PASSWORD}
      - ADMIN_EMAIL=\${ADMIN_EMAIL:-admin@sashainfinity.com}
      - ADMIN_USERNAME=\${ADMIN_USERNAME:-sashainfinity_admin}
      - RAZORPAY_KEY=\${RAZORPAY_KEY}
      - RAZORPAY_SECRET=\${RAZORPAY_SECRET}
      - SMTP_HOST=\${SMTP_HOST}
      - SMTP_PORT=\${SMTP_PORT:-587}
      - SMTP_USER=\${SMTP_USER}
      - SMTP_PASSWORD=\${SMTP_PASSWORD}
      - EMAIL_FROM=\${EMAIL_FROM:-noreply@sashainfinity.com}
      - BUNNY_LIBRARY_ID=\${BUNNY_LIBRARY_ID:-618286}
      - BUNNY_API_KEY=\${BUNNY_API_KEY}
      - BUNNY_CDN_HOSTNAME=\${BUNNY_CDN_HOSTNAME:-vz-60dda74a-f32.b-cdn.net}
      - BUNNY_TOKEN_AUTH_KEY=\${BUNNY_TOKEN_AUTH_KEY:-}
      - BUNNY_SIGNED_URL_TTL=\${BUNNY_SIGNED_URL_TTL:-3600}
      - ENVIRONMENT=production
      - DEBUG=false
      - AUTO_VERIFY_EMAIL=\${AUTO_VERIFY_EMAIL:-false}
      - FRONTEND_URL=\${FRONTEND_URL:-https://lms.sashainfinity.com}
      - BACKEND_URL=\${BACKEND_URL:-https://backend.sashainfinity.com}
      - DOMAIN=\${DOMAIN:-sashainfinity.com}
      - ENABLE_API_RATE_LIMITING=\${ENABLE_API_RATE_LIMITING:-true}
      - ENABLE_SECURITY_HEADERS=\${ENABLE_SECURITY_HEADERS:-true}
      - MIN_PASSWORD_LENGTH=\${MIN_PASSWORD_LENGTH:-12}
      - SESSION_TIMEOUT_MINUTES=\${SESSION_TIMEOUT_MINUTES:-30}
      - MAX_FILE_SIZE=\${MAX_FILE_SIZE:-10485760}
      - SCAN_UPLOADED_FILES=\${SCAN_UPLOADED_FILES:-true}
      - CORS_ORIGINS=\${CORS_ORIGINS:-["https://lms.sashainfinity.com", "https://backend.sashainfinity.com"]}
      - ALLOWED_HOSTS=\${ALLOWED_HOSTS:-["lms.sashainfinity.com", "backend.sashainfinity.com", "localhost"]}
      - PYTHONPATH=/app/backend
      - PYTHONUNBUFFERED=1
      - PYTHONDONTWRITEBYTECODE=1
    volumes:
      - ./uploads:/app/uploads
      - ./certificates:/app/certificates
      - ./logs:/var/log/sashainfinity
      - ./ssl:/etc/nginx/ssl
    networks:
      - sasha_lms_app-network
      - app-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://127.0.0.1/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

networks:
  sasha_lms_app-network:
    external: true
EOF

# Step 4: Start new container
log_step "Starting ${DEPLOY_COLOR} container..."
DEPLOY_PORT=$([ "$DEPLOY_COLOR" = "green" ] && echo "8082" || echo "8081")

docker run -d \
  --name sashainfinity-lms-${DEPLOY_COLOR} \
  --network sasha_lms_app-network \
  -p ${DEPLOY_PORT}:80 \
  -e DATABASE_URL="postgresql://tutor:${POSTGRES_PASSWORD}@postgres:5432/tutor_lms" \
  -e REDIS_URL="redis://sashainfinity-redis:6379/0" \
  --env-file .env \
  -v /www/wwwroot/sasha_lms/sasha_lms/sasha_lms/uploads:/app/uploads \
  -v /www/wwwroot/sasha_lms/sasha_lms/sasha_lms/certificates:/app/certificates \
  -v /www/wwwroot/sasha_lms/sasha_lms/sasha_lms/logs:/var/log/sashainfinity \
  -v /www/wwwroot/sasha_lms/sasha_lms/sasha_lms/ssl:/etc/nginx/ssl \
  --restart unless-stopped \
  sashainfinity-lms:${TAG}

# Step 5: Health check
log_step "Waiting for ${DEPLOY_COLOR} to be healthy..."
for i in $(seq 1 $MAX_WAIT); do
    if curl -sf "http://localhost:${DEPLOY_PORT}/health" > /dev/null 2>&1; then
        log_info "✓ ${DEPLOY_COLOR} is healthy!"
        HEALTHY=true
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

if [ "$HEALTHY" != true ]; then
    log_error "❌ ${DEPLOY_COLOR} failed health check! Rolling back..."
    docker stop sashainfinity-lms-${DEPLOY_COLOR} 2>/dev/null || true
    docker rm sashainfinity-lms-${DEPLOY_COLOR} 2>/dev/null || true
    log_info "Rollback complete. ${OLD_COLOR} still serving traffic."
    exit 1
fi

# Step 6: Switch nginx to new container
log_step "Switching nginx to ${DEPLOY_COLOR}..."

# Check actual nginx config location for sashainfinity.com
if [ -f /etc/nginx/sites-enabled/sashainfinity ]; then
    NGINX_CONF="/etc/nginx/sites-enabled/sashainfinity"
elif [ -f /etc/nginx/sites-enabled/lms ]; then
    NGINX_CONF="/etc/nginx/sites-enabled/lms"
elif [ -f /etc/nginx/conf.d/lms.conf ]; then
    NGINX_CONF="/etc/nginx/conf.d/lms.conf"
elif [ -f /etc/nginx/conf.d/sashainfinity.conf ]; then
    NGINX_CONF="/etc/nginx/conf.d/sashainfinity.conf"
else
    NGINX_CONF="/etc/nginx/sites-enabled/sashainfinity"
    log_warn "Using default nginx config path: ${NGINX_CONF}"
fi

# Update nginx upstream - replace port (handle both with and without trailing slash)
sed -i "s|proxy_pass http://127\.0\.0\.1:[0-9]*;|proxy_pass http://127.0.0.1:${DEPLOY_PORT};|g" ${NGINX_CONF} 2>/dev/null || true
sed -i "s|proxy_pass http://127\.0\.0\.1:[0-9]*/|proxy_pass http://127.0.0.1:${DEPLOY_PORT}/|g" ${NGINX_CONF} 2>/dev/null || true

# Test nginx config
if nginx -t 2>/dev/null; then
    systemctl reload nginx 2>/dev/null || nginx -s reload 2>/dev/null || true
    log_info "✓ Nginx switched to ${DEPLOY_COLOR}"
else
    log_error "❌ Nginx config test failed! Rolling back..."
    docker stop sashainfinity-lms-${DEPLOY_COLOR}
    docker rm sashainfinity-lms-${DEPLOY_COLOR}
    exit 1
fi

# Step 7: Verify traffic
log_step "Verifying traffic switch..."
sleep 3
if curl -sf "${HEALTH_URL}/health" > /dev/null 2>&1; then
    log_info "✓ Traffic flowing to ${DEPLOY_COLOR}"
else
    log_error "❌ Health check failed after switch! Rolling back..."
    # Switch back
    OLD_PORT=$([ "$DEPLOY_COLOR" = "green" ] && echo "8081" || echo "8082")
    sed -i "s|proxy_pass http://127\.0\.0\.1:[0-9]*;|proxy_pass http://127.0.0.1:${OLD_PORT};|g" ${NGINX_CONF}
    sed -i "s|proxy_pass http://127\.0\.0\.1:[0-9]*/|proxy_pass http://127.0.0.1:${OLD_PORT}/|g" ${NGINX_CONF}
    nginx -s reload 2>/dev/null || true
    docker stop sashainfinity-lms-${DEPLOY_COLOR}
    docker rm sashainfinity-lms-${DEPLOY_COLOR}
    log_info "Rollback complete."
    exit 1
fi

# Step 8: Stop old container (keep as backup for manual rollback)
log_warn "Keeping ${OLD_COLOR} container running as backup. Stop manually when confident:"
echo "  docker stop sashainfinity-lms-${OLD_COLOR} && docker rm sashainfinity-lms-${OLD_COLOR}"

# Cleanup old images
docker image prune -af --filter "label!=sashainfinity-keep" 2>/dev/null || true

log_info "🚀 Deployment to ${DEPLOY_COLOR} complete!"
echo "Active: sashainfinity-lms-${DEPLOY_COLOR} on port ${DEPLOY_PORT}"
echo "Backup: sashainfinity-lms-${OLD_COLOR} (running, ready for rollback)"
echo ""
echo "To rollback manually:"
echo "  1. Switch nginx back: sed -i 's|:${PORT}/|:${OLD_PORT}/|' ${NGINX_CONF}"
echo "  2. Reload: nginx -s reload"
echo "  3. Stop ${DEPLOY_COLOR}: docker stop sashainfinity-lms-${DEPLOY_COLOR}"
