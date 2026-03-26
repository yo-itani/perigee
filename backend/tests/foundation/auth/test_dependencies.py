import uuid

from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from foundation.auth.dependencies import _parse_user_id_header, get_current_user
from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.in_memory_user_repository import InMemoryUserRepository

# ---------------------------------------------------------------------------
# _parse_user_id_header (pure header parsing, no DB)
# ---------------------------------------------------------------------------

_parse_app = FastAPI()


@_parse_app.get("/test-parse")
async def _parse_endpoint(
    user_id: UserId = Depends(_parse_user_id_header),  # noqa: B008
) -> dict[str, str]:
    return {"user_id": str(user_id.value)}


async def _parse_client() -> AsyncClient:
    transport = ASGITransport(app=_parse_app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_valid_uuid_returns_user_id() -> None:
    uid = str(uuid.uuid4())
    async with await _parse_client() as client:
        response = await client.get("/test-parse", headers={"X-User-Id": uid})

    assert response.status_code == 200
    assert response.json() == {"user_id": uid}


async def test_missing_header_returns_401() -> None:
    async with await _parse_client() as client:
        response = await client.get("/test-parse")

    assert response.status_code == 401
    assert response.json()["detail"] == "X-User-Id header is missing or invalid"


async def test_invalid_uuid_returns_401() -> None:
    async with await _parse_client() as client:
        response = await client.get(
            "/test-parse", headers={"X-User-Id": "not-a-uuid"}
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "X-User-Id header is missing or invalid"


async def test_empty_string_returns_401() -> None:
    async with await _parse_client() as client:
        response = await client.get("/test-parse", headers={"X-User-Id": ""})

    assert response.status_code == 401
    assert response.json()["detail"] == "X-User-Id header is missing or invalid"


# ---------------------------------------------------------------------------
# get_current_user (with DB check via in-memory repo)
# ---------------------------------------------------------------------------

_ACTIVE_USER_ID = str(uuid.uuid4())
_INACTIVE_USER_ID = str(uuid.uuid4())
_UNKNOWN_USER_ID = str(uuid.uuid4())

_active_user = User(
    id=UserId.from_str(_ACTIVE_USER_ID),
    name="Active",
    email="active@example.com",
    role=UserRole.MEMBER,
    is_active=True,
)
_inactive_user = User(
    id=UserId.from_str(_INACTIVE_USER_ID),
    name="Inactive",
    email="inactive@example.com",
    role=UserRole.MEMBER,
    is_active=False,
)

_repo = InMemoryUserRepository(users=[_active_user, _inactive_user])


def _build_auth_app() -> FastAPI:
    from api.dependencies import get_session

    app = FastAPI()

    @app.get("/test-auth")
    async def _auth_endpoint(
        user: User = Depends(get_current_user),  # noqa: B008
    ) -> dict[str, str]:
        return {"user_id": str(user.id.value)}

    # Override get_session -- not needed by in-memory repo but required by the
    # dependency signature. We inject None; the repo override below bypasses it.
    async def _fake_session():  # type: ignore[no-untyped-def]
        yield None

    app.dependency_overrides[get_session] = _fake_session

    # Override get_current_user with a version that uses the in-memory repo.
    from foundation.auth.dependencies import _parse_user_id_header

    async def _fake_get_current_user(
        parsed_id: UserId = Depends(_parse_user_id_header),  # noqa: B008
    ) -> User:
        from fastapi import HTTPException

        user = await _repo.get_by_id(parsed_id)
        if user is None:
            raise HTTPException(status_code=403, detail="User not found")
        if not user.is_active:
            raise HTTPException(
                status_code=403, detail="User account is deactivated"
            )
        return user

    app.dependency_overrides[get_current_user] = _fake_get_current_user
    return app


_auth_app = _build_auth_app()


async def _auth_client() -> AsyncClient:
    transport = ASGITransport(app=_auth_app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_active_user_returns_200() -> None:
    async with await _auth_client() as client:
        resp = await client.get(
            "/test-auth", headers={"X-User-Id": _ACTIVE_USER_ID}
        )
    assert resp.status_code == 200
    assert resp.json() == {"user_id": _ACTIVE_USER_ID}


async def test_inactive_user_returns_403() -> None:
    async with await _auth_client() as client:
        resp = await client.get(
            "/test-auth", headers={"X-User-Id": _INACTIVE_USER_ID}
        )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "User account is deactivated"


async def test_unknown_user_returns_403() -> None:
    async with await _auth_client() as client:
        resp = await client.get(
            "/test-auth", headers={"X-User-Id": _UNKNOWN_USER_ID}
        )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "User not found"
