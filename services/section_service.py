"""Section-level business logic for the engineering monitoring dashboard.

This module exposes :class:`SectionService`, the component responsible
for giving dashboard pages structured access to every engineering
section discovered in a workbook — and their nested sub-sections and
metrics — without any of them needing to know how sections were
discovered or parsed.

Every expandable panel in the dashboard (for example NPCL, DG, GG, Air
Compressor, Freon, or any other department/meter grouping the workbook
happens to contain) is powered directly by this service: a page asks for
"all sections", "a section by name", "a section's subsections", or "a
section's metrics", and receives exactly the model objects the parser
already built. No section, subsection, or metric name is ever hardcoded
here — this service only ever operates on whatever
:class:`~models.section.Section` and :class:`~models.section.SubSection`
objects the workbook happens to contain, in the order the workbook
defines them.

This service deliberately contains:

* No KPI calculations.
* No chart generation.
* No Streamlit or any other UI code.
* No re-parsing or re-discovery of workbook structure — it only reads
  the already-built :class:`~models.workbook.Workbook` object graph via
  :class:`~services.workbook_service.WorkbookService`.
"""

from __future__ import annotations

from typing import Callable, List, Optional, Protocol, runtime_checkable

from models.metric import Metric
from models.section import Section, SubSection
from models.workbook import Workbook


@runtime_checkable
class WorkbookServiceLike(Protocol):
    """Structural interface required of an injected workbook service.

    :class:`SectionService` depends on this narrow interface rather than
    the concrete ``WorkbookService`` class, keeping it decoupled from
    that service's implementation (Dependency Inversion Principle) and
    straightforward to test with fakes.
    """

    def list_sections(self, workbook: Workbook) -> List[Section]:
        """Lists every section successfully discovered in the workbook.

        Args:
            workbook: The parsed workbook to inspect.

        Returns:
            The workbook's top-level sections, in discovery order.
        """
        ...


# A predicate used to filter sections or subsections. Kept generic so the
# same filtering support works for both Section and SubSection without
# duplicating method signatures.
SectionFilter = Callable[[Section], bool]
SubSectionFilter = Callable[[SubSection], bool]


class SectionService:
    """Provides structured, order-preserving access to workbook sections.

    :class:`SectionService` is the entry point dashboard pages should use
    to power any expandable section panel: it hands back the
    :class:`~models.section.Section`, :class:`~models.section.SubSection`,
    and :class:`~models.metric.Metric` objects the parser already built,
    in the exact order the workbook defined them, with optional
    predicate-based filtering for future needs (for example filtering by
    unit, by whether a section has subsections, or by any other
    attribute already present on the models).

    Attributes:
        workbook_service: The injected service used to obtain a
            workbook's discovered sections.
    """

    def __init__(self, workbook_service: WorkbookServiceLike) -> None:
        """Initializes the service with its workbook service dependency.

        Args:
            workbook_service: An object satisfying
                :class:`WorkbookServiceLike`.
        """
        self.workbook_service = workbook_service

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def list_sections(
        self,
        workbook: Workbook,
        predicate: Optional[SectionFilter] = None,
    ) -> List[Section]:
        """Lists every discovered section, in workbook order.

        Args:
            workbook: The parsed workbook to inspect.
            predicate: An optional callable used to filter sections. When
                provided, only sections for which
                ``predicate(section)`` is truthy are returned. This is
                the extension point for future filtering (for example by
                unit or by presence of subsections) without changing
                this method's signature.

        Returns:
            The matching :class:`~models.section.Section` instances, in
            the order the workbook defines them.
        """
        sections = self.workbook_service.list_sections(workbook)
        if predicate is None:
            return list(sections)
        return [section for section in sections if predicate(section)]

    def get_section(self, workbook: Workbook, name: str) -> Optional[Section]:
        """Finds a single top-level section by its normalized name.

        Args:
            workbook: The parsed workbook to inspect.
            name: The section's normalized (slugified) ``name`` to
                match. This is never a hardcoded literal supplied by
                this service; callers pass whatever name they obtained
                from a previously listed section.

        Returns:
            The matching :class:`~models.section.Section`, or ``None``
            if no section with that name exists.
        """
        for section in self.list_sections(workbook):
            if section.name == name:
                return section
        return None

    def get_section_by_display_name(
        self, workbook: Workbook, display_name: str
    ) -> Optional[Section]:
        """Finds a single top-level section by its human-readable label.

        Useful when a caller only has the label shown in the UI (for
        example a value read back from a selectbox) rather than the
        internal normalized name.

        Args:
            workbook: The parsed workbook to inspect.
            display_name: The section's ``display_name`` to match.

        Returns:
            The matching :class:`~models.section.Section`, or ``None``
            if no section with that display name exists.
        """
        for section in self.list_sections(workbook):
            if section.display_name == display_name:
                return section
        return None

    def has_sections(self, workbook: Workbook) -> bool:
        """Whether the workbook contains any discovered sections at all.

        Args:
            workbook: The parsed workbook to inspect.

        Returns:
            ``True`` if at least one section was discovered.
        """
        return len(self.list_sections(workbook)) > 0

    # ------------------------------------------------------------------
    # Subsections
    # ------------------------------------------------------------------

    def list_subsections(
        self,
        section: Section,
        predicate: Optional[SubSectionFilter] = None,
    ) -> List[SubSection]:
        """Lists every subsection belonging to a section, in order.

        A section with no subsections (because the sheet it came from had
        no grouping rows, or only one) simply yields an empty list; every
        expandable panel can therefore treat "sections with subsections"
        and "sections without subsections" uniformly by checking this
        method's result rather than branching on section shape.

        Args:
            section: The section whose subsections should be listed.
            predicate: An optional callable used to filter subsections.
                When provided, only subsections for which
                ``predicate(subsection)`` is truthy are returned.

        Returns:
            The matching :class:`~models.section.SubSection` instances,
            in the order the workbook defines them.
        """
        subsections = section.subsections
        if predicate is None:
            return list(subsections)
        return [subsection for subsection in subsections if predicate(subsection)]

    def get_subsection(self, section: Section, name: str) -> Optional[SubSection]:
        """Finds a single subsection of a section by its normalized name.

        Args:
            section: The section to search within.
            name: The subsection's normalized (slugified) ``name`` to
                match.

        Returns:
            The matching :class:`~models.section.SubSection`, or
            ``None`` if no subsection with that name exists.
        """
        for subsection in self.list_subsections(section):
            if subsection.name == name:
                return subsection
        return None

    def get_subsection_by_display_name(
        self, section: Section, display_name: str
    ) -> Optional[SubSection]:
        """Finds a single subsection of a section by its display label.

        Args:
            section: The section to search within.
            display_name: The subsection's ``display_name`` to match.

        Returns:
            The matching :class:`~models.section.SubSection`, or
            ``None`` if no subsection with that display name exists.
        """
        for subsection in self.list_subsections(section):
            if subsection.display_name == display_name:
                return subsection
        return None

    def has_subsections(self, section: Section) -> bool:
        """Whether a section has been broken down into subsections.

        Args:
            section: The section to check.

        Returns:
            ``True`` if the section has at least one subsection.
        """
        return len(section.subsections) > 0

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def list_section_metrics(
        self,
        section: Section,
        include_subsections: bool = True,
    ) -> List[Metric]:
        """Lists every metric belonging to a section, in workbook order.

        Args:
            section: The section whose metrics should be listed.
            include_subsections: When ``True`` (the default), metrics
                nested inside the section's subsections are included,
                appended in subsection order after the section's own
                directly attached metrics. When ``False``, only metrics
                attached directly to the section are returned.

        Returns:
            The matching :class:`~models.metric.Metric` instances, in
            the order the workbook defines them.
        """
        metrics = list(section.metrics)
        if include_subsections:
            for subsection in section.subsections:
                metrics.extend(self.list_subsection_metrics(subsection))
        return metrics

    def list_subsection_metrics(self, subsection: SubSection) -> List[Metric]:
        """Lists every metric belonging to a single subsection, in order.

        Args:
            subsection: The subsection whose metrics should be listed.

        Returns:
            The subsection's :class:`~models.metric.Metric` instances, in
            the order the workbook defines them.
        """
        return list(subsection.metrics)

    def get_metric(self, section: Section, name: str) -> Optional[Metric]:
        """Finds a single metric anywhere within a section by its name.

        Searches the section's directly attached metrics first, then
        each subsection's metrics in order, so this works uniformly
        whether or not the section has been broken into subsections.

        Args:
            section: The section to search within.
            name: The metric's normalized (slugified) ``name`` to match.

        Returns:
            The matching :class:`~models.metric.Metric`, or ``None`` if
            no metric with that name exists anywhere in the section.
        """
        for metric in self.list_section_metrics(section):
            if metric.name == name:
                return metric
        return None

    # ------------------------------------------------------------------
    # Cross-cutting helpers
    # ------------------------------------------------------------------

    def list_units(self, section: Section) -> List[str]:
        """Lists the distinct units used within a single section.

        Args:
            section: The section to inspect.

        Returns:
            The distinct units used anywhere in the section (including
            its subsections), in first-seen order.
        """
        seen: List[str] = []
        for unit in section.units:
            if unit and unit not in seen:
                seen.append(unit)
        return seen

    def count_metrics(self, section: Section) -> int:
        """Counts every metric belonging to a section, including nested.

        Args:
            section: The section to inspect.

        Returns:
            The total number of metrics in the section and its
            subsections combined.
        """
        return len(self.list_section_metrics(section, include_subsections=True))
