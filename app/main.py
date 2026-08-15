from fastapi import FastAPI

app = FastAPI(title="TeamOps API", version="0.1.0")


@app.get("/healthz", tags=["health"])
async def health_check() -> dict[str, str]:
    """Liveness check used by Render and local Docker Compose."""
    return {"status": "ok"}
