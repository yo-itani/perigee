"""Tests for application lifespan event dispatcher initialization."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from main import app


class TestLifespanEventDispatcher:
    """Verify that the lifespan sets up event_dispatcher on app.state."""

    @pytest.mark.integration
    async def test_event_dispatcher_available_on_app_state(self) -> None:
        """After lifespan startup, app.state has an InMemoryEventDispatcher."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Trigger lifespan by making any request
            response = await client.get("/health")

        assert response.status_code == 200
        assert isinstance(app.state.event_dispatcher, InMemoryEventDispatcher)
