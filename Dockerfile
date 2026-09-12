# multi-stage build: React UI, then the FastAPI app serving it from the same origin
# (see README "single-port demo"). Build: docker compose up --build

FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim-bookworm AS runtime
WORKDIR /app
# libgl1/libglib2.0-0: runtime libs opencv/easyocr's torch backend link against
# https:// (not the default http://) works around networks that block/403 the plain-HTTP mirror
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt backend/requirements.txt
# CPU-only torch wheels first: easyocr depends on torch/torchvision, and without this
# pip resolves the default (CUDA-bundled) wheels - several GB of GPU libraries this
# container never uses. Installing the CPU build first satisfies that dependency so pip
# skips it below.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchvision \
    && pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY --from=frontend /app/frontend/dist frontend/dist
EXPOSE 8000
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
