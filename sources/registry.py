from __future__ import annotations

from dataclasses import dataclass

from core.config import Settings
from sources.base import JobSource
from sources.computrabajo import ComputrabajoSource
from sources.greenhouse import GreenhouseSource
from sources.occ import OccSource


@dataclass(frozen=True)
class SourceBinding:
    name: str
    enabled: bool
    source: JobSource | None = None
    reason: str | None = None


def build_source_bindings(settings: Settings) -> list[SourceBinding]:
    return [
        _build_greenhouse_binding(settings),
        _build_indeed_binding(settings),
        _build_occ_binding(settings),
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


def _build_indeed_binding(settings: Settings) -> SourceBinding:
    if not settings.indeed_enabled:
        return SourceBinding(
            name="indeed",
            enabled=False,
            reason="INDEED_ENABLED=false",
        )

    if not settings.indeed_query:
        return SourceBinding(
            name="indeed",
            enabled=False,
            reason="INDEED_QUERY is empty",
        )

    try:
        from sources.indeed import IndeedSource
    except ImportError as exc:
        return SourceBinding(
            name="indeed",
            enabled=False,
            reason=f"Indeed dependencies are unavailable: {exc}",
        )

    return SourceBinding(
        name="indeed",
        enabled=True,
        source=IndeedSource(
            query=settings.indeed_query,
            location=settings.indeed_location,
            remote_only=settings.indeed_remote_only,
            timeout_seconds=settings.request_timeout_seconds,
        ),
    )


def _build_occ_binding(settings: Settings) -> SourceBinding:
    if not settings.occ_enabled:
        return SourceBinding(
            name="occ",
            enabled=False,
            reason="OCC_ENABLED=false",
        )

    return SourceBinding(name="occ", enabled=True, source=OccSource())


def _build_computrabajo_binding(settings: Settings) -> SourceBinding:
    if not settings.computrabajo_enabled:
        return SourceBinding(
            name="computrabajo",
            enabled=False,
            reason="COMPUTRABAJO_ENABLED=false",
        )

    return SourceBinding(
        name="computrabajo",
        enabled=True,
        source=ComputrabajoSource(),
    )
