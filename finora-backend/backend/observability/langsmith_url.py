"""Resolve the correct LangSmith project URL at startup and cache it."""
from __future__ import annotations

import os

import structlog

log = structlog.get_logger()

_cached_url: str | None = None
_resolved = False


def get_project_url() -> str | None:
    """
    Return the full LangSmith project URL.
    Resolution order:
      1. Env vars LANGSMITH_ORG_ID + LANGSMITH_PROJECT_ID (fastest, no API call)
      2. LangSmith Client API (reads project by name, uses client._tenant_id)
      3. None if LANGCHAIN_API_KEY not set
    Result is cached — API call happens at most once per process lifetime.
    """
    global _cached_url, _resolved
    if _resolved:
        return _cached_url

    _resolved = True
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        return None

    project_name = os.getenv("LANGCHAIN_PROJECT", "finora-prod")

    # Fast path — both IDs set explicitly in env
    org_id = os.getenv("LANGSMITH_ORG_ID")
    project_id = os.getenv("LANGSMITH_PROJECT_ID")
    if org_id and project_id:
        _cached_url = f"https://smith.langchain.com/o/{org_id}/projects/p/{project_id}"
        log.info("langsmith_traced", url=_cached_url)
        return _cached_url

    # Slow path — fetch from LangSmith API (once per process)
    try:
        from langsmith import Client
        client = Client(api_key=api_key)

        project = client.read_project(project_name=project_name)
        project_id = str(project.id)

        # _tenant_id is private but stable across SDK versions
        resolved_org_id = org_id or str(getattr(client, "_tenant_id", None) or "")

        if resolved_org_id and project_id:
            _cached_url = f"https://smith.langchain.com/o/{resolved_org_id}/projects/p/{project_id}"
        elif project_id:
            # Fallback: no org id available — link to project by name (less precise)
            _cached_url = f"https://smith.langchain.com/projects/{project_name}"

        log.info("langsmith_url_resolved_from_api", url=_cached_url, project_id=project_id)
    except Exception as exc:
        log.warning("langsmith_url_resolution_failed", error=str(exc))
        _cached_url = None

    return _cached_url
