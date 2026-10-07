FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js vitest.config.js ./
COPY src/ ./src/
# Verify the UI before packaging; only static output reaches the runtime image.
RUN npm test && npm run build

FROM nginx:1.28-alpine AS runtime
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist/ /usr/share/nginx/html/
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/frontend-health || exit 1
# Custom config uses /tmp for writable files; no root entrypoint setup is needed.
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
