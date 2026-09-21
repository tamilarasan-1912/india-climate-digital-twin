# Backend image for the India Climate Digital Twin API.
#
# The climate datasets (IMD rainfall NetCDF) and administrative geometry are NOT
# baked into the image. They are large, licensed, and refreshed independently, so
# they are mounted at runtime. See docker-compose.yml.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# netCDF4 and rasterio need native libraries; keep the layer cacheable by
# installing OS packages before copying the Python sources.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libnetcdf-dev \
        libhdf5-dev \
        libgeos-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r backend/requirements.txt

COPY backend backend
COPY scripts scripts
COPY config config

# Run as a non-root user; the mounted data directory is read-only.
RUN useradd --create-home --uid 10001 twin \
    && chown -R twin:twin /app
USER twin

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
