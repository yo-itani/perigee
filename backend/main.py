from fastapi import FastAPI

from api.register_routers import register_routers

app = FastAPI(title="perigee", version="0.1.0")

register_routers(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
