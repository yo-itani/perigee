import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.event_setup import create_event_dispatcher
from api.exception_handlers import register_exception_handlers
from api.register_routers import register_routers
from foundation.scheduler.lifespan import create_reminder_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    app.state.event_dispatcher = create_event_dispatcher()

    scheduler = create_reminder_scheduler()
    if scheduler is not None:
        scheduler.start()

    # Register auth cleanup scheduler on the same APScheduler instance
    _register_auth_cleanup(scheduler)

    yield
    if scheduler is not None:
        scheduler.shutdown()


def _register_auth_cleanup(
    reminder_scheduler: object | None,
) -> None:
    """Register the auth cleanup job on the reminder scheduler's APScheduler."""
    try:
        from foundation.auth.cleanup_scheduler import AuthCleanupScheduler

        if reminder_scheduler is not None:
            # Access the underlying APScheduler instance
            apscheduler = getattr(reminder_scheduler, "_scheduler", None)
            if apscheduler is not None:
                cleanup = AuthCleanupScheduler(apscheduler)
                cleanup.register()
                return

        # Fallback: create a standalone scheduler
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        standalone = AsyncIOScheduler()
        cleanup = AuthCleanupScheduler(standalone)
        cleanup.register()
        standalone.start()
        logger.info("Auth cleanup scheduler started (standalone)")
    except Exception:
        logger.exception("Failed to register auth cleanup scheduler")


app = FastAPI(title="perigee", version="0.1.0", lifespan=lifespan)

register_exception_handlers(app)
register_routers(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
