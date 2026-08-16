from __future__ import annotations


class TestModelStore:
    def test_singleton_instance(self):
        from app.services.model_store import ModelStore

        a = ModelStore()
        b = ModelStore()
        assert a is b

    def test_set_and_get_model(self):
        from app.services.model_store import ModelStore

        store = ModelStore()
        store.set_model("model_a", {"foo": "bar"})
        assert store.get_model("model_a") == {"foo": "bar"}

    def test_get_model_missing(self):
        from app.services.model_store import ModelStore

        store = ModelStore()
        assert store.get_model("nonexistent") is None

    def test_is_loaded(self):
        from app.services.model_store import ModelStore

        store = ModelStore()
        store.set_model("x", 1)
        assert store.is_loaded("x") is True
        assert store.is_loaded("y") is False

    def test_global_singleton(self):
        from app.services.model_store import model_store

        model_store.set_model("global", 42)
        assert model_store.get_model("global") == 42
