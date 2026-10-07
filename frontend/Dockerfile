# Build stage: compile Vite bundle.
FROM node:26-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# VITE_API_BASE_URL is baked into the bundle. Prod nginx reverse-proxies /api
# back to the backend service so the SPA uses a same-origin relative URL.
ENV VITE_API_BASE_URL=/api
# Supabase client config is also baked at build time (Vite compile-time
# substitution). Compose passes these from the root .env; the publishable key
# is public by design. Without them the bundle falls back to a dead
# placeholder host and every auth call fails with "Failed to fetch".
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_PUBLISHABLE_KEY
ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL \
    VITE_SUPABASE_PUBLISHABLE_KEY=$VITE_SUPABASE_PUBLISHABLE_KEY
RUN npm run build

# Serve stage: lean nginx with SPA fallback + /api proxy.
FROM nginx:1.31.6-alpine
# Pull latest alpine patches over the pinned baseline so any CVEs fixed after the
# image was published are applied. Trivy scan gates merges on CRITICAL CVEs.
RUN apk --no-cache upgrade
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Drop root: run as the unprivileged nginx user (uid 101, present in the base
# image). Make the paths the master/workers write to owned by that user, and
# serve on 8080 since non-root cannot bind privileged ports. The base image's
# `user nginx;` directive is ignored (with a harmless warning) when already
# running as nginx.
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid
USER nginx
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
