FROM node:22 AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm install

COPY ./ .
RUN npm run build --deploy-url=. && ls -la dist/


FROM nginxinc/nginx-unprivileged:1.27-alpine

ENV CUSTOM_SCRIPTS_DIRECTORY=""
ENV NGINX_PORT=8080

COPY --from=builder --chown=nginx /app/dist/@datakern/frontend/browser /app
COPY nginx-default.conf.template /etc/nginx/templates/default.conf.template
COPY --chmod=755 ./docker-entrypoint.sh /custom-entrypoint.sh

ENTRYPOINT ["/custom-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
