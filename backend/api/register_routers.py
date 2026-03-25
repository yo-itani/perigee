from fastapi import FastAPI

from contexts.notification.presentation.router import (
    router as notification_router,
)


def register_routers(app: FastAPI) -> None:
    """Register all context routers with the FastAPI application.

    Routers will be added here as each context is implemented.
    """
    from contexts.preparation.presentation.router import (
        router as preparation_router,
    )
    from contexts.record.presentation.router import router as record_router

    app.include_router(notification_router)
    app.include_router(preparation_router, tags=["Preparation"])
    app.include_router(record_router, tags=["Record"])
