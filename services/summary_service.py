"""Summary card generation for the engineering monitoring dashboard homepage.

This module exposes :class:`SummaryService`, the component responsible
for building the data behind the dashboard's homepage summary cards
(configured by default as NPCL, CLC, Blast, Dunkin, Freon, and Air
Compressor).

Only the *identity* of which sections should appear as summary cards,
and in what order, is configured here — as a plain list of section
identifiers supplied at construction time. Every number shown on a card
(total, average, last registered value, maximum, minimum, trend,
percentage change) is produced by
:class:`~services.kpi_service.KPIService`'s existing, fully dynamic
section-aggregation logic; this service performs no calculations of its
own and never hardcodes how a KPI is derived.

This service deliberately contains:

* No chart generation.
* No Streamlit or any other UI code.
* No duplicated KPI math — every figure comes from
  :meth:`~services.kpi_service.KPIService.calculate_section_summary`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Protocol, Sequence, runtime_checkable

from models.section import Section
from models.workbook import Workbook
from services.filter_service import FilterCriteria, FilterService
from services.kpi_service import SectionKPISummary


# The dashboard's fixed homepage layout: which sections should be shown
# as summary cards, by default, and in what order. This is configuration
# only — it names sections the same way a UI label would, but every
# value ultimately shown on a card is computed dynamically by
# KPIService. A workbook missing one of these sections simply produces
# fewer cards; nothing here assumes all six are present.
DEFAULT_SUMMARY_CARD_SECTIONS: Sequence[str] = (
    "npcl",
    "clc",
    "blast",
    "dunkin",
    "freon",
    "air_compressor",
)


@dataclass(frozen=True)
class SummaryCard:
    """A single homepage summary card, ready for the UI layer.

    Attributes:
        section_key: The configured identifier used to request this
            card (as supplied to :class:`SummaryService`), preserved so
            the UI layer can map a card back to its configuration entry
            (for icons, ordering, etc.) without re-deriving it.
        section_name: The matched section's normalized (slugified) name,
            as discovered in the workbook.
        display_name: The matched section's human-readable label.
        summary: The section's aggregated :class:`SectionKPISummary`.
    """

    section_key: str
    section_name: str
    display_name: str
    summary: SectionKPISummary


@runtime_checkable
class WorkbookServiceLike(Protocol):
    """Structural interface required of an injected workbook service."""

    def get_workbook(
        self,
        source_path: str,
        workbook_name: Optional[str] = None,
        strict: bool = False,
    ) -> Workbook:
        """Retrieves the fully parsed Workbook model for a source path."""
        ...


@runtime_checkable
class SectionServiceLike(Protocol):
    """Structural interface required of an injected section service."""

    def list_sections(self, workbook: Workbook) -> List[Section]:
        """Lists every section successfully discovered in the workbook."""
        ...

    def get_section(self, workbook: Workbook, name: str) -> Optional[Section]:
        """Finds a single top-level section by its normalized name."""
        ...

    def get_section_by_display_name(
        self, workbook: Workbook, display_name: str
    ) -> Optional[Section]:
        """Finds a single top-level section by its human-readable label."""
        ...


@runtime_checkable
class FilterServiceLike(Protocol):
    """Structural interface required of an injected filter service."""

    def filter_section(
        self, section: Section, criteria: FilterCriteria
    ) -> Optional[Section]:
        """Returns a new Section restricted to matching subsections/metrics."""
        ...


@runtime_checkable
class KPIServiceLike(Protocol):
    """Structural interface required of an injected KPI service."""

    def calculate_section_summary(
        self,
        section: Section,
        include_subsections: bool = True,
        data_point_filter=None,
    ) -> SectionKPISummary:
        """Computes a single aggregated KPI summary across a section."""
        ...


class SummaryService:
    """Builds the dashboard homepage's section summary cards.

    :class:`SummaryService` looks up each configured section (by
    normalized name, falling back to display name), applies whatever
    filters are currently active, and asks
    :class:`~services.kpi_service.KPIService` for that section's
    aggregated KPIs. Sections configured for the homepage but absent
    from a particular workbook are skipped silently, since not every
    workbook will contain every one of the fixed six sections.

    Attributes:
        workbook_service: The injected service used to obtain a parsed
            workbook (only needed by the source-path convenience entry
            point; callers may also pass an already-loaded workbook
            directly to :meth:`build_summary_cards`).
        section_service: The injected service used to locate sections by
            name.
        filter_service: The injected service used to apply active
            filters to a section before aggregation.
        kpi_service: The injected service used to compute a section's
            aggregated KPIs.
        section_keys: The ordered list of section identifiers that
            should appear as homepage summary cards. Defaults to
            :data:`DEFAULT_SUMMARY_CARD_SECTIONS`.
    """

    def __init__(
        self,
        workbook_service: WorkbookServiceLike,
        section_service: SectionServiceLike,
        filter_service: FilterServiceLike,
        kpi_service: KPIServiceLike,
        section_keys: Optional[Sequence[str]] = None,
    ) -> None:
        """Initializes the service with its collaborators and configuration.

        Args:
            workbook_service: An object satisfying
                :class:`WorkbookServiceLike`.
            section_service: An object satisfying
                :class:`SectionServiceLike`.
            filter_service: An object satisfying
                :class:`FilterServiceLike`.
            kpi_service: An object satisfying :class:`KPIServiceLike`.
            section_keys: The ordered section identifiers to render as
                summary cards. Defaults to
                :data:`DEFAULT_SUMMARY_CARD_SECTIONS` (NPCL, CLC, Blast,
                Dunkin, Freon, Air Compressor) when omitted, so the fixed
                homepage layout can still be overridden or extended by
                callers without touching this module.
        """
        self.workbook_service = workbook_service
        self.section_service = section_service
        self.filter_service = filter_service
        self.kpi_service = kpi_service
        self.section_keys = list(section_keys or DEFAULT_SUMMARY_CARD_SECTIONS)

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def build_summary_cards(
        self,
        workbook: Workbook,
        criteria: Optional[FilterCriteria] = None,
        include_subsections: bool = True,
    ) -> List[SummaryCard]:
        """Builds summary cards for every configured section that's present.

        Args:
            workbook: The parsed workbook to build cards from.
            criteria: The currently active filter criteria (date range,
                month, multiple months, or any future filter). When
                omitted, no filtering is applied and every historical
                value contributes to each card's KPIs.
            include_subsections: Whether each card's aggregation should
                include metrics nested in the section's subsections.
                Defaults to ``True``, matching the section-level
                aggregation semantics used elsewhere in the dashboard.

        Returns:
            One :class:`SummaryCard` per configured section that exists
            in ``workbook``, in the configured order. Configured
            sections absent from the workbook are omitted; no error is
            raised.
        """
        cards: List[SummaryCard] = []
        for section_key in self.section_keys:
            card = self.build_summary_card(
                workbook, section_key, criteria, include_subsections
            )
            if card is not None:
                cards.append(card)
        return cards

    def build_summary_card(
        self,
        workbook: Workbook,
        section_key: str,
        criteria: Optional[FilterCriteria] = None,
        include_subsections: bool = True,
    ) -> Optional[SummaryCard]:
        """Builds a single summary card for one configured section.

        Args:
            workbook: The parsed workbook to build the card from.
            section_key: The section identifier to look up, matched
                against both normalized section names and display names
                so configuration can use whichever is more convenient.
            criteria: The currently active filter criteria, if any.
            include_subsections: Whether the aggregation should include
                metrics nested in the section's subsections.

        Returns:
            The built :class:`SummaryCard`, or ``None`` if no section
            matching ``section_key`` exists in ``workbook``.
        """
        section = self._resolve_section(workbook, section_key)
        if section is None:
            return None

        filtered_section = self._apply_filters(section, criteria)
        if filtered_section is None:
            return None

        summary = self.kpi_service.calculate_section_summary(
            filtered_section, include_subsections=include_subsections
        )

        return SummaryCard(
            section_key=section_key,
            section_name=filtered_section.name,
            display_name=filtered_section.display_name,
            summary=summary,
        )

    def build_summary_cards_from_source(
        self,
        source_path: str,
        workbook_name: Optional[str] = None,
        criteria: Optional[FilterCriteria] = None,
        include_subsections: bool = True,
    ) -> List[SummaryCard]:
        """Convenience entry point that loads a workbook, then builds cards.

        Args:
            source_path: Path or identifier of the workbook to load.
            workbook_name: Optional human-friendly name for the
                workbook.
            criteria: The currently active filter criteria, if any.
            include_subsections: Whether each card's aggregation should
                include metrics nested in the section's subsections.

        Returns:
            The homepage's :class:`SummaryCard` list, as in
            :meth:`build_summary_cards`.
        """
        workbook = self.workbook_service.get_workbook(
            source_path=source_path, workbook_name=workbook_name
        )
        return self.build_summary_cards(workbook, criteria, include_subsections)

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------

    def _resolve_section(
        self, workbook: Workbook, section_key: str
    ) -> Optional[Section]:
        """Locates a configured section by normalized name or display name.

        Trying the normalized name first, then falling back to the
        display name, lets ``section_keys`` be configured with whichever
        form is most convenient (a slug like ``"air_compressor"`` or a
        label like ``"Air Compressor"``) without this service needing to
        know which one a given workbook actually produced.

        Args:
            workbook: The parsed workbook to search.
            section_key: The configured section identifier to resolve.

        Returns:
            The matching :class:`Section`, or ``None`` if not found by
            either name.
        """
        section = self.section_service.get_section(workbook, section_key)
        if section is not None:
            return section
        return self.section_service.get_section_by_display_name(
            workbook, section_key
        )

    def _apply_filters(
        self, section: Section, criteria: Optional[FilterCriteria]
    ) -> Optional[Section]:
        """Applies the active filter criteria to a section, if any is set.

        Args:
            section: The section to filter.
            criteria: The currently active filter criteria, or ``None``
                to skip filtering entirely.

        Returns:
            The filtered :class:`Section`, the original ``section`` when
            ``criteria`` is ``None``, or ``None`` if filtering excludes
            the section entirely (for example a name-based exclusion
            that doesn't apply here, or no data remaining in range).
        """
        if criteria is None:
            return section
        return self.filter_service.filter_section(section, criteria)
