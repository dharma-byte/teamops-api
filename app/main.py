from fastapi import FastAPI

from app.api.v1.router import router as api_v1_router

app = FastAPI(title="TeamOps API", version="0.1.0")
app.include_router(api_v1_router)


@app.get("/healthz", tags=["health"])
async def health_check() -> dict[str, str]:
    """Liveness check used by Render and local Docker Compose."""
    return {"status": "ok"}
