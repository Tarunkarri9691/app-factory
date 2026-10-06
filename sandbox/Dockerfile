# Isolated environment for running generated tests. Dependencies are baked in
# because the container runs with --network none.
FROM python:3.12-slim
RUN pip install --no-cache-dir fastapi uvicorn sqlalchemy pydantic httpx pytest jinja2 python-multipart
WORKDIR /app
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1
