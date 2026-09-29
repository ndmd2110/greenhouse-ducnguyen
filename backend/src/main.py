# backend/src/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# Import Phase 2, Phase 3, and Phase 4 routers
from src.interfaces.api.sensors import router as sensors_router
from src.interfaces.api.devices import router as devices_router
from src.interfaces.api.locations import router as locations_router
from src.infrastructure.persistence.base import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
  # Docker-free local development uses the SQLite fallback; initialize its
  # schema automatically. PostgreSQL remains migration-managed by Alembic.
  if engine.dialect.name == "sqlite":
    Base.metadata.create_all(bind=engine)
  yield


app = FastAPI(title="IoT Device Management API", lifespan=lifespan)

# 1. Enable CORS Middleware (Fixes "Failed to fetch")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Register Routers
app.include_router(sensors_router)
app.include_router(devices_router)
app.include_router(locations_router)

# 3. Health check
@app.get("/health")
def health_check():
    return {"status": "ok", "database": "up"}

# 4. Scalar documentation
@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    return HTMLResponse("""
    <!doctype html>
    <html>
      <head>
        <title>Scalar API Reference</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>
        <script id="api-reference" data-url="/openapi.json"></script>
        <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
      </body>
    </html>
    """)