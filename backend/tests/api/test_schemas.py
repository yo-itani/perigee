from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from api.schemas import PaginatedResponse

# -- Test helpers --


class SampleItem(BaseModel):
    id: int
    name: str


# -- Serialization / Deserialization --


class TestPaginatedResponseSerialization:
    """Serialization and deserialization of PaginatedResponse."""

    def test_serialize_with_items(self) -> None:
        response = PaginatedResponse[SampleItem](
            items=[SampleItem(id=1, name="Alice"), SampleItem(id=2, name="Bob")],
            total_count=10,
            offset=0,
            limit=2,
        )
        data = response.model_dump()

        assert data == {
            "items": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ],
            "total_count": 10,
            "offset": 0,
            "limit": 2,
        }

    def test_serialize_empty_items(self) -> None:
        response = PaginatedResponse[SampleItem](
            items=[],
            total_count=0,
            offset=0,
            limit=20,
        )
        data = response.model_dump()

        assert data["items"] == []
        assert data["total_count"] == 0

    def test_deserialize_from_dict(self) -> None:
        raw = {
            "items": [{"id": 3, "name": "Charlie"}],
            "total_count": 1,
            "offset": 0,
            "limit": 10,
        }
        response = PaginatedResponse[SampleItem].model_validate(raw)

        assert len(response.items) == 1
        assert isinstance(response.items[0], SampleItem)
        assert response.items[0].id == 3
        assert response.items[0].name == "Charlie"
        assert response.total_count == 1

    def test_deserialize_from_json(self) -> None:
        json_str = (
            '{"items": [{"id": 4, "name": "Diana"}],'
            ' "total_count": 50, "offset": 10, "limit": 5}'
        )
        response = PaginatedResponse[SampleItem].model_validate_json(json_str)

        assert response.items[0].name == "Diana"
        assert response.offset == 10
        assert response.limit == 5

    def test_json_round_trip(self) -> None:
        original = PaginatedResponse[SampleItem](
            items=[SampleItem(id=1, name="Alice")],
            total_count=100,
            offset=20,
            limit=10,
        )
        json_str = original.model_dump_json()
        restored = PaginatedResponse[SampleItem].model_validate_json(json_str)

        assert restored == original


# -- OpenAPI schema generation --


class TestPaginatedResponseOpenAPI:
    """OpenAPI schema generation with concrete type parameters."""

    def test_openapi_schema_contains_concrete_type(self) -> None:
        """PaginatedResponse[SampleItem] generates a named schema in OpenAPI."""
        test_app = FastAPI()

        @test_app.get(
            "/items",
            response_model=PaginatedResponse[SampleItem],
        )
        async def list_items() -> PaginatedResponse[SampleItem]:
            raise NotImplementedError  # pragma: no cover

        openapi = test_app.openapi()
        schemas = openapi["components"]["schemas"]

        # FastAPI generates a schema name like PaginatedResponse_SampleItem_
        paginated_schema_names = [
            name for name in schemas if name.startswith("PaginatedResponse")
        ]
        assert len(paginated_schema_names) == 1
        schema_name = paginated_schema_names[0]

        schema = schemas[schema_name]
        # The schema must have items, total_count, offset, limit properties
        props = schema["properties"]
        assert "items" in props
        assert "total_count" in props
        assert "offset" in props
        assert "limit" in props

    def test_openapi_items_references_concrete_type(self) -> None:
        """The items array references the concrete SampleItem schema."""
        test_app = FastAPI()

        @test_app.get(
            "/items",
            response_model=PaginatedResponse[SampleItem],
        )
        async def list_items() -> PaginatedResponse[SampleItem]:
            raise NotImplementedError  # pragma: no cover

        openapi = test_app.openapi()
        schemas = openapi["components"]["schemas"]

        # SampleItem must exist as a separate schema
        assert "SampleItem" in schemas
        sample_schema = schemas["SampleItem"]
        assert "id" in sample_schema["properties"]
        assert "name" in sample_schema["properties"]

        # items array must reference SampleItem
        paginated_schema_name = next(
            name for name in schemas if name.startswith("PaginatedResponse")
        )
        items_prop = schemas[paginated_schema_name]["properties"]["items"]
        assert items_prop["type"] == "array"
        assert items_prop["items"]["$ref"] == "#/components/schemas/SampleItem"

    def test_openapi_endpoint_response_schema(self) -> None:
        """The endpoint response references the PaginatedResponse schema."""
        test_app = FastAPI()

        @test_app.get(
            "/items",
            response_model=PaginatedResponse[SampleItem],
        )
        async def list_items() -> PaginatedResponse[SampleItem]:
            raise NotImplementedError  # pragma: no cover

        openapi = test_app.openapi()
        response_content = openapi["paths"]["/items"]["get"]["responses"]["200"][
            "content"
        ]["application/json"]["schema"]

        assert "$ref" in response_content
        assert "PaginatedResponse" in response_content["$ref"]

    def test_endpoint_returns_paginated_response(self) -> None:
        """An endpoint using PaginatedResponse returns correct JSON."""
        test_app = FastAPI()

        @test_app.get(
            "/items",
            response_model=PaginatedResponse[SampleItem],
        )
        async def list_items() -> PaginatedResponse[SampleItem]:
            return PaginatedResponse[SampleItem](
                items=[SampleItem(id=1, name="Test")],
                total_count=1,
                offset=0,
                limit=10,
            )

        client = TestClient(test_app)
        resp = client.get("/items")

        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == [{"id": 1, "name": "Test"}]
        assert body["total_count"] == 1
        assert body["offset"] == 0
        assert body["limit"] == 10
