FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Lets `pytest` and `alembic` import `src.*` from /app
ENV PYTHONPATH=/app

COPY pyproject.toml .
# Runtime + dev extras (pytest, httpx) so tests can run inside the container
RUN pip install --no-cache-dir ".[dev]"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]