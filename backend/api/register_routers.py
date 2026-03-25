from fastapi import FastAPI

from contexts.notification.presentation.router import (
    router as notification_router,
)


def register_routers(app: FastAPI) -> None:
    """Register all context routers with the FastAPI application.

    Routers will be added here as each context is implemented.
    """
    app.include_router(notification_router)
