"""Facade re-exports for the tasks package.

services/run_service consumes the pipelines through this surface
(``from tasks import _run_agent_pipeline``) so the service layer depends on
a single stable entry module instead of each task file's internals.
"""
from tasks.agent_pipeline import _run_agent_pipeline
from tasks.complete_pipeline import _complete_pipeline
from tasks.pipeline_utils import (
    _build_session_context,
    _get_rag_context,
    _parse_json_field,
    _report_run_error,
    _run_async,
    _save_output_memories,
    _try_mock_fallback,
)
from tasks.registry import complete_agent, run_agent

__all__ = [
    "_run_agent_pipeline",
    "_complete_pipeline",
    "_build_session_context",
    "_get_rag_context",
    "_parse_json_field",
    "_report_run_error",
    "_run_async",
    "_save_output_memories",
    "_try_mock_fallback",
    "complete_agent",
    "run_agent",
]
