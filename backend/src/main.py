# backend/src/main.py
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from src.application.readings.sampler import SimulationSampler
from src.application.readings.service import ReadingIngest
from src.infrastructure.adapters.sensors.selector import select_sensor_port
from src.infrastructure.persistence.base import Base, SessionLocal, engine
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.reading_repository import ReadingRepository

# Import Phase 2, Phase 3, and Phase 4 routers
from src.interfaces.api.sensors import router as sensors_router
from src.interfaces.api.devices import router as devices_router
from src.interfaces.api.locations import router as locations_router

logger = logging.getLogger(__name__)
SAMPLER_TICK_SECONDS = 1.0  # smallest allowed interval is 5s, so 1s ticks are plenty


def _sample_tick() -> None:
    # Own session per tick: do not reuse a request-scoped get_db session here.
    with SessionLocal() as session:
        devices, readings = DeviceRepository(session), ReadingRepository(session)
        ingest = ReadingIngest(devices, readings, select_sensor_port)
        SimulationSampler(devices, readings, ingest, select_sensor_port).run_once(
            datetime.now(timezone.utc)
        )


async def _sampler_loop(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await asyncio.to_thread(_sample_tick)
        except Exception:
            logger.exception("Sampler tick failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=SAMPLER_TICK_SECONDS)
        except asyncio.TimeoutError:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Docker-free local development uses the SQLite fallback; initialize its
    # schema automatically. PostgreSQL remains migration-managed by Alembic.
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(bind=engine)

    stop = asyncio.Event()
    task = None
    if os.getenv("SAMPLER_ENABLED", "1") != "0":  # set to 0 to disable, e.g. in tests
        task = asyncio.create_task(_sampler_loop(stop))
    yield
    stop.set()
    if task is not None:
        await task


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