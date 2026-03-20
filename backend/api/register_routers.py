from fastapi import FastAPI


def register_routers(app: FastAPI) -> None:
    """Register all context routers with the FastAPI application.

    Routers will be added here as each context is implemented.
    """
