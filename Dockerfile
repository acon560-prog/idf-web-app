############################
# 1) Build the React client #
############################
FROM node:20-alpine AS client-build

WORKDIR /app/client
# CRA env vars must be available at build time
ARG REACT_APP_GOOGLE_PLACES_API_KEY
ENV REACT_APP_GOOGLE_PLACES_API_KEY=${REACT_APP_GOOGLE_PLACES_API_KEY}
COPY client/package.json client/package-lock.json ./
RUN npm ci
COPY client/ ./
RUN npm run build

############################
# 2) Build the Python server#
############################
FROM python:3.12-slim AS server

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/server

# System deps (kept minimal)
RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Python deps
COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Server source
COPY server/ ./

# Copy client build output into Flask static folder
COPY --from=client-build /app/client/build ./build

# Cloud Run will set PORT
ENV PORT=8080
EXPOSE 8080

# Run via gunicorn in production
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT} -w 2 -t 120 app:app"]

