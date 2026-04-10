# =============================================================================
# AICodeGenCrew Frontend — Multi-Stage Build
# Build context: project root (so certs/ is accessible)
# Angular compiled to minified+hashed JS. No source in final image.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: BUILD — compile Angular to production bundle
# ---------------------------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies
COPY ui/frontend/package.json ui/frontend/package-lock.json* ./
RUN npm ci --ignore-scripts

# Copy source and build production
COPY ui/frontend/ .
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: FINAL — nginx serves only compiled assets
# ---------------------------------------------------------------------------
FROM nginx:alpine AS final

# Copy only the compiled Angular bundle (minified + tree-shaken + hashed)
COPY --from=build /app/dist/dashboard/browser /usr/share/nginx/html
COPY ui/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
