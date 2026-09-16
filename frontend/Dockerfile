# Frontend image: build the Angular app, then serve it with nginx.

# --- Stage 1: build ---
FROM node:20-alpine AS build
WORKDIR /app

# Install dependencies first (cached unless the lockfile changes).
COPY package.json package-lock.json .npmrc ./
RUN npm ci

# Build the production bundle.
COPY . .
RUN npm run build

# --- Stage 2: serve ---
# The unprivileged variant of the official image: it runs as uid 101 and listens on 8080,
# because binding port 80 is what forces a container to keep root. Serving a folder of
# static files is not a reason to hold that privilege.
FROM nginxinc/nginx-unprivileged:1.31.5-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/chess-coach-ui/browser /usr/share/nginx/html
EXPOSE 8080

# The base image already runs as this user; saying it here makes the image's privilege
# readable in the file itself, instead of in the documentation of someone else's image.
USER 101

# A container that starts and serves nothing looks healthy to an orchestrator without this.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget --spider --quiet http://127.0.0.1:8080/ || exit 1
