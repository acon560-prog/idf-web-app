# ===============================
# 1. Build React frontend (CRA)
# ===============================
FROM node:18 AS frontend-builder

# Set working directory
WORKDIR /app

# Copy package.json first for caching
COPY client/package*.json ./client/

# Install dependencies
RUN cd client && npm install

# Copy full React project
COPY client ./client

# Build the production frontend bundle
RUN cd client && npm run build


# ===============================
# 2. Build Python Flask backend
# ===============================
FROM python:3.11-slim AS backend

# Set working directory
WORKDIR /app

# Install OS packages required for building Python deps
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy backend code
COPY server ./server

# Copy CRA "build" folder into Flask /server/build
COPY --from=frontend-builder /app/client/build ./server/build

# Install backend dependencies
RUN pip install --no-cache-dir -r server/requirements.txt

# Cloud Run requires this variable:
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Start Gunicorn server
CMD ["gunicorn", "--chdir", "server", "app:app", "--bind", ":8080"]
