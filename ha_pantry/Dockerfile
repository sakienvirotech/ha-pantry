FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/home-assistant/base-python:3.14-alpine3.24
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /src/dist ./static
# s6 clears the environment for CMD by default.
ENV S6_KEEP_ENV=1
# Ingress is the only client, so never take the client address from headers.
CMD ["python3", "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8099", "--no-proxy-headers"]
