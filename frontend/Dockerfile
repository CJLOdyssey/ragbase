# ── Build stage ──
# Build arg for npm registry (default: npmmirror for China users)
# Override for overseas: --build-arg NPM_REGISTRY=https://registry.npmjs.org
ARG NPM_REGISTRY=https://registry.npmmirror.com
FROM node:22-alpine AS builder

WORKDIR /build

COPY package.json package-lock.json ./
RUN npm ci --registry=${NPM_REGISTRY}

COPY index.html tsconfig.json vite.config.ts ./
COPY public/ public/
COPY src/ src/

RUN npm run build

# ── Serve stage ──
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html

# Run as non-root user for security
RUN addgroup -g 1000 appgroup && adduser -u 1000 -G appgroup -D appuser && \
    sed -i 's/^user[ \t]*nginx;/user appuser;/' /etc/nginx/nginx.conf && \
    sed -i 's|^pid[ \t]*/run/nginx.pid;|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf && \
    chown -R appuser:appgroup /var/cache/nginx /var/run /usr/share/nginx/html
USER appuser

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
