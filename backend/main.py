from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.exception_handlers import register_exception_handlers
from api.register_routers import register_routers
from foundation.scheduler.lifespan import create_reminder_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    scheduler = create_reminder_scheduler()
    if scheduler is not None:
        scheduler.start()
    yield
    if scheduler is not None:
        scheduler.shutdown()


app = FastAPI(title="perigee", version="0.1.0", lifespan=lifespan)

register_exception_handlers(app)
register_routers(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
