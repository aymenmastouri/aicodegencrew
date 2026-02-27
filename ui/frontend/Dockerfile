# =============================================================================
# AICodeGenCrew Frontend - SECURE Multi-Stage Build
# Angular compiled to minified+hashed JS. No source in final image.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: BUILD — compile Angular to production bundle
# ---------------------------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts

# Copy source and build production
COPY . .
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: FINAL — nginx serves only compiled assets
# ---------------------------------------------------------------------------
FROM nginx:alpine AS final

# Remove unnecessary tools that could be used to inspect
RUN rm -rf /usr/bin/wget /usr/bin/curl /usr/sbin/apk \
    && rm -rf /var/cache/apk/*

# Copy only the compiled Angular bundle (minified + tree-shaken + hashed)
COPY --from=build /app/dist/dashboard/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# No source code, no node_modules, no TypeScript — only .js/.css/.html
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
