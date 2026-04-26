FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .

# NEXT_PUBLIC_ vars are baked into JS bundle at build time.
# Pass these via Railway/Docker build args or Vercel dashboard.
ARG NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
ARG NEXT_PUBLIC_THESYS_API_KEY=""
ARG NEXT_PUBLIC_APP_NAME=Finora
ARG NEXT_PUBLIC_APP_VERSION=1.0.0

ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL
ENV NEXT_PUBLIC_THESYS_API_KEY=$NEXT_PUBLIC_THESYS_API_KEY
ENV NEXT_PUBLIC_APP_NAME=$NEXT_PUBLIC_APP_NAME
ENV NEXT_PUBLIC_APP_VERSION=$NEXT_PUBLIC_APP_VERSION

RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
