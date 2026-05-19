ARG NODE_IMAGE=node:20-alpine
ARG NGINX_IMAGE=nginx:1.27-alpine
ARG APP_VERSION=dev
ARG BUILD_STAMP=local

FROM ${NODE_IMAGE} AS build
WORKDIR /app/admin-web

COPY admin-web/package.json admin-web/package-lock.json admin-web/tsconfig.json admin-web/vite.config.ts admin-web/index.html ./
COPY admin-web/src ./src

ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV APP_VERSION=${APP_VERSION}
ENV BUILD_STAMP=${BUILD_STAMP}

RUN npm ci && npm run build

FROM ${NODE_IMAGE} AS mobile-build
WORKDIR /app/mobile-web

COPY mobile-web/package.json mobile-web/package-lock.json mobile-web/tsconfig.json mobile-web/tsconfig.node.json mobile-web/index.html mobile-web/.gitignore ./
COPY mobile-web/vite.config.ts ./vite.config.ts
COPY mobile-web/public ./public
COPY mobile-web/src ./src

ARG VITE_API_BASE_URL=/api/v1
ARG VITE_APP_BASE=/m/
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_APP_BASE=${VITE_APP_BASE}
ENV APP_VERSION=${APP_VERSION}
ENV BUILD_STAMP=${BUILD_STAMP}

RUN npm ci && npm run build

FROM ${NGINX_IMAGE}
ARG APP_VERSION=dev
ARG BUILD_STAMP=local
LABEL org.opencontainers.image.title="familycut-admin-web"
LABEL org.opencontainers.image.version="${APP_VERSION}"
LABEL org.opencontainers.image.revision="${BUILD_STAMP}"
ENV APP_VERSION=${APP_VERSION}
ENV BUILD_STAMP=${BUILD_STAMP}
COPY admin-web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/admin-web/dist /usr/share/nginx/html
COPY --from=mobile-build /app/mobile-web/dist /usr/share/nginx/html/m
RUN chmod -R a+rX /usr/share/nginx/html
