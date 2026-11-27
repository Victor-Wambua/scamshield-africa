# Not built on the development machine (no Docker available). Staging use only.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv/app
RUN pip install uv
COPY pyproject.toml uv.lock* ./
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv pip install --system ".[postgres]"
RUN useradd -r -u 10001 scamshield && mkdir -p /srv/data && chown scamshield /srv/data
USER scamshield
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request as u;u.urlopen('http://127.0.0.1:8000/healthz')"
CMD ["sh", "-c", "python -m scamshield migrate && uvicorn --factory scamshield.main:app_factory --host 0.0.0.0 --port 8000 --proxy-headers"]
