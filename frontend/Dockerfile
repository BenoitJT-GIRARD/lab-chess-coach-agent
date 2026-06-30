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
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/chess-coach-ui/browser /usr/share/nginx/html
EXPOSE 80
