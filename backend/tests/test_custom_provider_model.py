import uuid


class TestCustomProviderModel:
    def test_to_dict_returns_expected_keys(self):
        from app.models.custom_provider import CustomProvider

        cp = CustomProvider(
            user_id=uuid.uuid4(),
            name="Test Provider",
            base_url="http://localhost:8080/v1",
            api_key_encrypted="encrypted:key",
            models=["model-a", "model-b"],
            is_local=True,
            description="A test provider",
        )
        d = cp.to_dict()
        assert d["name"] == "Test Provider"
        assert d["base_url"] == "http://localhost:8080/v1"
        assert d["models"] == ["model-a", "model-b"]
        assert d["is_local"] is True
        assert d["description"] == "A test provider"
        assert d["is_active"] is True
        assert isinstance(d["id"], str)
        assert isinstance(d["user_id"], str)

    def test_to_dict_default_values(self):
        from app.models.custom_provider import CustomProvider

        cp = CustomProvider(
            user_id=uuid.uuid4(),
            name="Minimal",
            base_url="http://localhost:8080/v1",
        )
        d = cp.to_dict()
        assert d["models"] == []
        assert d["is_local"] is False
        assert d["description"] is None
        assert d["is_active"] is True
        assert d["api_key_encrypted"] is None

    def test_default_is_active_true(self):
        from app.models.custom_provider import CustomProvider

        cp = CustomProvider(
            user_id=uuid.uuid4(),
            name="Test",
            base_url="http://localhost:8080/v1",
        )
        assert cp.is_active is True

    def test_default_models_empty_list(self):
        from app.models.custom_provider import CustomProvider

        cp = CustomProvider(
            user_id=uuid.uuid4(),
            name="Test",
            base_url="http://localhost:8080/v1",
        )
        assert cp.models == []

    def test_auto_generates_uuid(self):
        from app.models.custom_provider import CustomProvider

        cp = CustomProvider(
            user_id=uuid.uuid4(),
            name="Test",
            base_url="http://localhost:8080/v1",
        )
        assert cp.id is not None
        assert isinstance(cp.id, uuid.UUID)

    def test_timestamps_set_on_create(self):
        from datetime import datetime

        from app.models.custom_provider import CustomProvider

        cp = CustomProvider(
            user_id=uuid.uuid4(),
            name="Test",
            base_url="http://localhost:8080/v1",
        )
        assert cp.created_at is not None
        assert cp.updated_at is not None
        assert isinstance(cp.created_at, datetime)

    def test_table_name(self):
        from app.models.custom_provider import CustomProvider

        assert CustomProvider.__tablename__ == "custom_providers"

    def test_to_dict_with_none_timestamps(self):
        from app.models.custom_provider import CustomProvider

        cp = CustomProvider(
            user_id=uuid.uuid4(),
            name="Test",
            base_url="http://localhost:8080/v1",
        )
        cp.created_at = None
        cp.updated_at = None
        d = cp.to_dict()
        assert d["created_at"] is None
        assert d["updated_at"] is None
