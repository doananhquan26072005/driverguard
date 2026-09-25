"""Shared test setup.

tests/test_agents and tests/test_api cover the course template (src/, LangGraph / LangChain),
not DriverGuard. They are skipped unless requirements-template.txt is installed, so
`pytest tests` works with requirements-dev.txt alone.
"""

import importlib.util
from pathlib import Path

TEMPLATE_DEPS = ("langgraph", "langchain_openai", "pytest_asyncio")
TEMPLATE_DIRS = {Path(__file__).parent / "test_agents", Path(__file__).parent / "test_api"}
HAS_TEMPLATE_DEPS = all(importlib.util.find_spec(m) for m in TEMPLATE_DEPS)


def pytest_ignore_collect(collection_path: Path, config) -> bool | None:
    if not HAS_TEMPLATE_DEPS and collection_path in TEMPLATE_DIRS:
        return True
    return None
