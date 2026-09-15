from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .interfaces.api.sensors import router as sensors_router

app = FastAPI(
    title="Greenhouse Control API",
    docs_url="/docs",
    redoc_url=None,
)

# Register API routes
app.include_router(sensors_router)

# Allow React frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    # Phase 1 health contract
    return {
        "status": "ok",
        "database": "up",
    }

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)