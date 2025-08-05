# ChatMap Web UI Dockerfile

FROM node:22-alpine3.21 AS builder

WORKDIR /app

RUN npm install -g npm@11.5.2
RUN npm install -g --force yarn

COPY package*.json ./

RUN yarn install

COPY ./index.html  ./index.html
COPY ./src ./src
COPY ./tests ./tests
COPY ./public ./public
COPY ./vite.config.js ./vite.config.js

# Enable live mode
ENV VITE_ENABLE_LIVE=1

RUN yarn build

FROM nginx:alpine

COPY --from=builder /app/build /usr/share/nginx/html

EXPOSE 80
