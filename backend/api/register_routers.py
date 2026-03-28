from fastapi import FastAPI

from api.auth_router import auth_router
from api.system_router import system_router
from contexts.notification.presentation.router import (
    notifications_router,
)
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
    from shared.presentation.admin_router import admin_router
    from shared.presentation.router import router as users_router

    app.include_router(system_router)
    app.include_router(auth_router)
    app.include_router(notification_router)
    app.include_router(notifications_router)
    app.include_router(preparation_router, tags=["Preparation"])
    app.include_router(record_router, tags=["Record"])
    # Register /users/me routes before /users/{user_id} to avoid path conflicts
    app.include_router(users_router)
    app.include_router(admin_router)
