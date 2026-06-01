FROM node:22-alpine AS client-build
WORKDIR /repo
COPY packages/koraku-client/package.json packages/koraku-client/package-lock.json ./packages/koraku-client/
RUN npm ci --prefix packages/koraku-client
COPY packages/koraku-client ./packages/koraku-client
RUN npm run build --prefix packages/koraku-client

FROM node:22-alpine AS web-build
WORKDIR /repo
COPY --from=client-build /repo/packages/koraku-client ./packages/koraku-client
COPY web/package.json web/package-lock.json ./web/
RUN npm ci --prefix web
COPY web ./web
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build --prefix web

FROM node:22-alpine AS web-run
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

COPY --from=web-build /repo/web/.next/standalone ./
COPY --from=web-build /repo/web/.next/static ./web/.next/static
COPY --from=web-build /repo/web/public ./web/public

EXPOSE 3000

CMD ["node", "server.js"]
