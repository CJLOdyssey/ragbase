"""Unit tests for backend/repository/ (base patterns and imports)."""






class TestRepositoryImports:
    def test_import_deps(self):
        from repository.deps import get_session

        assert get_session is not None

    def test_get_session_is_asyncgen(self):
        import inspect

        from repository.deps import get_session
        assert inspect.isasyncgenfunction(get_session)

    def test_session_factory_import(self):
        from core.infra.database import get_session_factory

        assert get_session_factory is not None

    def test_repository_subclass_has_model(self):
        from core.infra.database import PromptDB
        from repository.prompts import PromptRepository

        assert PromptRepository.model is PromptDB

    def test_repository_subclass_imports(self):
        from repository.prompts import PromptRepository

        assert PromptRepository is not None
