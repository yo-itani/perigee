from foundation.domain.exceptions import OptimisticLockError


class TestOptimisticLockError:
    def test_message_contains_entity_info(self) -> None:
        err = OptimisticLockError("Record", "abc-123")
        assert "Record" in str(err)
        assert "abc-123" in str(err)

    def test_attributes(self) -> None:
        err = OptimisticLockError("Record", "abc-123")
        assert err.entity_type == "Record"
        assert err.entity_id == "abc-123"

    def test_is_exception(self) -> None:
        err = OptimisticLockError("Record", "abc-123")
        assert isinstance(err, Exception)
