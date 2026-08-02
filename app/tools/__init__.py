"""Tool package. Importing it registers every tool into the default registry.

Each submodule uses the @tool decorator, which registers on import — so a
single `import app.tools` makes all tools available to the agent's loop.
"""
from app.tools import (  # noqa: F401
    calculator,
    clock,
    data_analysis,
    file_ops,
    graph_search,
    http_tool,
    python_exec,
    rag_search,
    sql_tool,
    subagent,
    web_search,
    wikipedia,
)
