import uuid

from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from foundation.auth.dependencies import get_current_user_id
from shared.domain.value_objects import UserId

_app = FastAPI()


@_app.get("/test-auth")
async def _test_endpoint(
    user_id: UserId = Depends(get_current_user_id),  # noqa: B008
) -> dict[str, str]:
    return {"user_id": str(user_id.value)}


async def _client() -> AsyncClient:
    transport = ASGITransport(app=_app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_valid_uuid_returns_user_id() -> None:
    uid = str(uuid.uuid4())
    async with await _client() as client:
        response = await client.get("/test-auth", headers={"X-User-Id": uid})

    assert response.status_code == 200
    assert response.json() == {"user_id": uid}


async def test_missing_header_returns_401() -> None:
    async with await _client() as client:
        response = await client.get("/test-auth")

    assert response.status_code == 401
    assert response.json()["detail"] == "X-User-Id header is missing or invalid"


async def test_invalid_uuid_returns_401() -> None:
    async with await _client() as client:
        response = await client.get("/test-auth", headers={"X-User-Id": "not-a-uuid"})

    assert response.status_code == 401
    assert response.json()["detail"] == "X-User-Id header is missing or invalid"


async def test_empty_string_returns_401() -> None:
    async with await _client() as client:
        response = await client.get("/test-auth", headers={"X-User-Id": ""})

    assert response.status_code == 401
    assert response.json()["detail"] == "X-User-Id header is missing or invalid"
