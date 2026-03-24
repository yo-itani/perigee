import uuid

from contexts.record.domain.value_objects import (
    ActionItemId,
    CommentId,
    RecordId,
    RecordStatus,
    RetrospectiveId,
)


class TestRecordId:
    def test_generate_creates_unique_ids(self) -> None:
        id1 = RecordId.generate()
        id2 = RecordId.generate()
        assert id1 != id2

    def test_from_str_roundtrip(self) -> None:
        raw = "550e8400-e29b-41d4-a716-446655440000"
        record_id = RecordId.from_str(raw)
        assert str(record_id.value) == raw

    def test_equality_same_uuid(self) -> None:
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        assert RecordId(value=raw) == RecordId(value=raw)

    def test_frozen(self) -> None:
        record_id = RecordId.generate()
        try:
            record_id.value = uuid.uuid4()  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")  # noqa: TRY301
        except AttributeError:
            pass

    def test_usable_as_dict_key(self) -> None:
        record_id = RecordId.generate()
        d = {record_id: "record"}
        assert d[record_id] == "record"


class TestActionItemId:
    def test_generate_creates_unique_ids(self) -> None:
        id1 = ActionItemId.generate()
        id2 = ActionItemId.generate()
        assert id1 != id2

    def test_from_str_roundtrip(self) -> None:
        raw = "660e8400-e29b-41d4-a716-446655440000"
        action_item_id = ActionItemId.from_str(raw)
        assert str(action_item_id.value) == raw

    def test_equality_same_uuid(self) -> None:
        raw = uuid.UUID("660e8400-e29b-41d4-a716-446655440000")
        assert ActionItemId(value=raw) == ActionItemId(value=raw)

    def test_frozen(self) -> None:
        action_item_id = ActionItemId.generate()
        try:
            action_item_id.value = uuid.uuid4()  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")  # noqa: TRY301
        except AttributeError:
            pass


class TestCommentId:
    def test_generate_creates_unique_ids(self) -> None:
        id1 = CommentId.generate()
        id2 = CommentId.generate()
        assert id1 != id2

    def test_from_str_roundtrip(self) -> None:
        raw = "770e8400-e29b-41d4-a716-446655440000"
        comment_id = CommentId.from_str(raw)
        assert str(comment_id.value) == raw

    def test_equality_same_uuid(self) -> None:
        raw = uuid.UUID("770e8400-e29b-41d4-a716-446655440000")
        assert CommentId(value=raw) == CommentId(value=raw)

    def test_frozen(self) -> None:
        comment_id = CommentId.generate()
        try:
            comment_id.value = uuid.uuid4()  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")  # noqa: TRY301
        except AttributeError:
            pass


class TestRetrospectiveId:
    def test_generate_creates_unique_ids(self) -> None:
        id1 = RetrospectiveId.generate()
        id2 = RetrospectiveId.generate()
        assert id1 != id2

    def test_from_str_roundtrip(self) -> None:
        raw = "880e8400-e29b-41d4-a716-446655440000"
        retrospective_id = RetrospectiveId.from_str(raw)
        assert str(retrospective_id.value) == raw

    def test_equality_same_uuid(self) -> None:
        raw = uuid.UUID("880e8400-e29b-41d4-a716-446655440000")
        assert RetrospectiveId(value=raw) == RetrospectiveId(value=raw)

    def test_frozen(self) -> None:
        retrospective_id = RetrospectiveId.generate()
        try:
            retrospective_id.value = uuid.uuid4()  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")  # noqa: TRY301
        except AttributeError:
            pass


class TestRecordStatus:
    def test_draft_value(self) -> None:
        assert RecordStatus.DRAFT.value == "draft"

    def test_published_value(self) -> None:
        assert RecordStatus.PUBLISHED.value == "published"

    def test_enum_members(self) -> None:
        assert set(RecordStatus) == {RecordStatus.DRAFT, RecordStatus.PUBLISHED}
