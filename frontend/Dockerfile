# Frontend Dockerfile for Next.js

# ---------- Base image ----------
FROM node:20-alpine AS base
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

# ---------- Dependencies layer ----------
# Copy only package files first to maximize Docker layer caching
FROM base AS deps
COPY frontend/package.json frontend/package-lock.json* frontend/pnpm-lock.yaml* frontend/yarn.lock* ./
# Default to npm; if you use yarn or pnpm, adjust the install command
RUN if [ -f package-lock.json ]; then npm ci; \
    elif [ -f yarn.lock ]; then corepack enable && yarn install --frozen-lockfile; \
    elif [ -f pnpm-lock.yaml ]; then corepack enable && pnpm install --frozen-lockfile; \
    else npm install; fi

# ---------- Development image ----------
# Used by docker-compose with `npm run dev` (hot reload)
FROM base AS dev
# Keep node_modules inside the container. docker-compose will mount project source over /app
COPY --from=deps /app/node_modules /app/node_modules
COPY frontend/ ./
EXPOSE 3000
CMD ["npm", "run", "dev"]

# ---------- Build (production) ----------
FROM base AS build
COPY --from=deps /app/node_modules /app/node_modules
COPY frontend/ ./
# If you set environment variables at build time (e.g., NEXT_PUBLIC_*), pass them via --build-arg or envs
RUN npm run build

# ---------- Runtime (production) ----------
FROM base AS runtime
ENV NODE_ENV=production
# Copy only necessary build outputs
COPY --from=build /app/.next /app/.next
COPY --from=build /app/public /app/public
COPY --from=deps /app/node_modules /app/node_modules
COPY frontend/package.json ./
EXPOSE 3000
CMD ["npm", "start"]
