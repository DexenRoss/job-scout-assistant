from __future__ import annotations

from dataclasses import dataclass

from core.config import Settings
from sources.base import JobSource
from sources.greenhouse import GreenhouseSource


@dataclass(frozen=True)
class SourceBinding:
    name: str
    enabled: bool
    source: JobSource | None = None
    reason: str | None = None


def build_source_bindings(settings: Settings) -> list[SourceBinding]:
    return [
        _build_greenhouse_binding(settings),
        _build_computrabajo_binding(settings),
    ]


def _build_greenhouse_binding(settings: Settings) -> SourceBinding:
    if not settings.greenhouse_enabled:
        return SourceBinding(
            name="greenhouse",
            enabled=False,
            reason="GREENHOUSE_ENABLED=false",
        )

    if not settings.greenhouse_company_boards:
        return SourceBinding(
            name="greenhouse",
            enabled=False,
            reason="GREENHOUSE_COMPANY_BOARDS is empty",
        )

    return SourceBinding(
        name="greenhouse",
        enabled=True,
        source=GreenhouseSource(
            board_tokens=settings.greenhouse_company_boards,
            timeout_seconds=settings.request_timeout_seconds,
            include_content=settings.greenhouse_include_content,
        ),
    )


def _build_computrabajo_binding(settings: Settings) -> SourceBinding:
    if not settings.computrabajo_enabled:
        return SourceBinding(
            name="computrabajo",
            enabled=False,
            reason="COMPUTRABAJO_ENABLED=false",
        )

    if not settings.computrabajo_query:
        return SourceBinding(
            name="computrabajo",
            enabled=False,
            reason="COMPUTRABAJO_QUERY is empty",
        )

    try:
        from sources.computrabajo import ComputrabajoSource
    except ImportError as exc:
        return SourceBinding(
            name="computrabajo",
            enabled=False,
            reason=f"Computrabajo dependencies are unavailable: {exc}",
        )

    return SourceBinding(
        name="computrabajo",
        enabled=True,
        source=ComputrabajoSource(
            query=settings.computrabajo_query,
            location=settings.computrabajo_location,
            remote_only=settings.computrabajo_remote_only,
            timeout_seconds=settings.request_timeout_seconds,
        ),
    )
