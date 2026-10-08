"""Shared test setup.

tests/test_agents and tests/test_api cover the course template (src/, LangGraph / LangChain),
not DriverGuard. They are skipped unless requirements-template.txt is installed, so
`pytest tests` works with requirements-dev.txt alone.
"""

import importlib.util
import os
from pathlib import Path

import pytest

TEMPLATE_DEPS = ("langgraph", "langchain_openai", "pytest_asyncio")
TEMPLATE_DIRS = {Path(__file__).parent / "test_agents", Path(__file__).parent / "test_api"}
HAS_TEMPLATE_DEPS = all(importlib.util.find_spec(m) for m in TEMPLATE_DEPS)


def pytest_ignore_collect(collection_path: Path, config) -> bool | None:
    if not HAS_TEMPLATE_DEPS and collection_path in TEMPLATE_DIRS:
        return True
    return None


@pytest.fixture
def need_model():
    """need_model(path): the tests on real model files. models/ is not in git, so a missing file skips
    the test; with DG_REQUIRE_MODELS=1 (the CI job that downloads them, M87) it fails instead, so these
    tests cannot go quiet where they are meant to run."""

    def need(path: Path) -> Path:
        if not path.exists():
            message = f"{path.name} is not in models/ (python tools/download_models.py)"
            if os.environ.get("DG_REQUIRE_MODELS") == "1":
                pytest.fail(message)
            pytest.skip(message)
        return path

    return need
