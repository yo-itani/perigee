"""Tests for Preparation context DI providers.

These tests verify the FastAPI Depends chain resolves correctly
by mounting a small test router and exercising the dependency injection.
"""

from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from api.event_setup import create_event_dispatcher
from contexts.preparation.application.create_schedule_service import (
    CreateScheduleService,
)
from contexts.preparation.domain.schedule_repository import ScheduleRepository
from contexts.preparation.presentation.dependencies import (
    get_create_schedule_service,
    get_schedule_repository,
)


@pytest.fixture
def di_test_app() -> FastAPI:
    """Create a minimal FastAPI app with test routes that use DI providers."""
    app = FastAPI()
    app.state.event_dispatcher = create_event_dispatcher()

    @app.get("/test/schedule-repo")
    async def check_schedule_repo(
        repo: Annotated[ScheduleRepository, Depends(get_schedule_repository)],
    ) -> dict[str, str]:
        return {"type": type(repo).__name__}

    @app.get("/test/create-schedule-service")
    async def check_create_schedule_service(
        service: Annotated[CreateScheduleService, Depends(get_create_schedule_service)],
    ) -> dict[str, str]:
        return {"type": type(service).__name__}

    return app


@pytest.mark.integration
class TestPreparationDependencyChain:
    """Integration tests that verify Depends chains resolve correctly.

    These tests require a running database because get_session creates
    a real AsyncSession via the session factory.
    """

    async def test_schedule_repository_resolves_to_sqlalchemy_impl(
        self, di_test_app: FastAPI
    ) -> None:
        """The schedule repository provider yields a SqlAlchemyScheduleRepository."""
        transport = ASGITransport(app=di_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test/schedule-repo")

        assert response.status_code == 200
        assert response.json()["type"] == "SqlAlchemyScheduleRepository"

    async def test_create_schedule_service_resolves(self, di_test_app: FastAPI) -> None:
        """The create schedule service provider yields a CreateScheduleService."""
        transport = ASGITransport(app=di_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test/create-schedule-service")

        assert response.status_code == 200
        assert response.json()["type"] == "CreateScheduleService"
