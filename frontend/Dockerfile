# ===========================
#       BUILD STAGE
# ===========================
FROM node:18-alpine AS build

WORKDIR /app

# Copy package files first
COPY package*.json ./

# Install dependencies
# --legacy-peer-deps: @react-three/drei@^10 requires React 19 but the project is on React 18.
RUN npm install --legacy-peer-deps

# Copy source code (env files, if any, come along via this COPY — they
# are not required for the build to succeed; Vite will fall back to
# import.meta.env defaults when no .env* file is present)
COPY . .

# Vite inlines import.meta.env.VITE_* at build time. Receive them as build
# args (set from docker-compose build.args) and promote to ENV so the build
# picks them up. Without this the API URL fell back to a relative "/api/v1"
# that the static host can't proxy to the backend.
ARG VITE_API_URL
ARG VITE_BACKEND_URL
ARG VITE_FRONTEND_URL
ARG VITE_RAZORPAY_KEY
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN
ARG VITE_FIREBASE_PROJECT_ID
ARG VITE_FIREBASE_STORAGE_BUCKET
ARG VITE_FIREBASE_MESSAGING_SENDER_ID
ARG VITE_FIREBASE_APP_ID
ENV VITE_API_URL=$VITE_API_URL \
    VITE_BACKEND_URL=$VITE_BACKEND_URL \
    VITE_FRONTEND_URL=$VITE_FRONTEND_URL \
    VITE_RAZORPAY_KEY=$VITE_RAZORPAY_KEY \
    VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY \
    VITE_FIREBASE_AUTH_DOMAIN=$VITE_FIREBASE_AUTH_DOMAIN \
    VITE_FIREBASE_PROJECT_ID=$VITE_FIREBASE_PROJECT_ID \
    VITE_FIREBASE_STORAGE_BUCKET=$VITE_FIREBASE_STORAGE_BUCKET \
    VITE_FIREBASE_MESSAGING_SENDER_ID=$VITE_FIREBASE_MESSAGING_SENDER_ID \
    VITE_FIREBASE_APP_ID=$VITE_FIREBASE_APP_ID

# Build Vite app
RUN npm run build


# ===========================
#       RUNTIME STAGE
# ===========================
FROM node:18-alpine AS runtime

WORKDIR /app

# Simple static server
RUN npm install -g serve

# Copy built assets
COPY --from=build /app/dist ./dist

EXPOSE 3000

# serve.json (copied from public/ into dist/) disables cleanUrls: builtin lab
# pages are embedded as iframes at their literal .html URLs (embed_url from
# /virtual-labs). cleanUrls 301-strips the .html, the extensionless path
# collides with the per-lab assets directory, the SPA fallback serves the app
# shell, and the lab player shows a 404.
CMD ["serve", "-s", "dist", "-l", "tcp://0.0.0.0:3000", "-n"]
