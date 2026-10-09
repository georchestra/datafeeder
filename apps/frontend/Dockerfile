FROM node:22 AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm install

COPY ./ .
RUN npm run build && ls -la dist/


FROM nginxinc/nginx-unprivileged:1.27-alpine

ENV CUSTOM_SCRIPTS_DIRECTORY=""
ENV ENABLE_GEORCHESTRA_HEADER="false"

COPY --from=builder --chown=nginx /app/dist/@datafeeder/frontend/browser /app/datafeeder
COPY nginx-default.conf.template /etc/nginx/conf.d/default.conf
COPY --chmod=755 ./custom-scripts.sh /docker-entrypoint.d/custom-scripts.sh
COPY --chmod=755 ./georchestra-header.sh /docker-entrypoint.d/georchestra-header.sh

CMD ["nginx", "-g", "daemon off;"]
