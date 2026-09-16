"""arXiv Atom XML parsing."""

from dataclasses import dataclass
from xml.etree import ElementTree


ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"
ARXIV_NAMESPACE = "http://arxiv.org/schemas/atom"


class ArxivParsingError(Exception):
    """Raised when an arXiv XML response cannot be parsed."""


@dataclass(frozen=True)
class RawArxivEntry:
    """Raw structured representation of an arXiv Atom entry."""

    id_url: str
    title: str
    summary: str
    authors: list[str]
    published: str
    updated: str
    categories: list[str]
    primary_category: str | None
    abstract_url: str | None
    pdf_url: str | None


class ArxivParser:
    """Parse arXiv Atom XML responses."""

    def parse(self, raw_xml: str) -> list[RawArxivEntry]:
        """Parse an arXiv Atom XML response into raw entries."""
        try:
            root = ElementTree.fromstring(raw_xml)
        except ElementTree.ParseError as exc:
            raise ArxivParsingError(
                "Failed to parse arXiv XML response."
            ) from exc

        entries: list[RawArxivEntry] = []

        for entry in root.findall(self._atom_tag("entry")):
            entries.append(self._parse_entry(entry))

        return entries

    @staticmethod
    def _atom_tag(tag: str) -> str:
        """Build a namespaced Atom tag."""
        return f"{{{ATOM_NAMESPACE}}}{tag}"

    @staticmethod
    def _arxiv_tag(tag: str) -> str:
        """Build a namespaced arXiv tag."""
        return f"{{{ARXIV_NAMESPACE}}}{tag}"

    def _parse_entry(
        self,
        entry: ElementTree.Element,
    ) -> RawArxivEntry:
        """Parse one Atom entry."""
        id_url = self._required_text(entry, "id")
        title = self._required_text(entry, "title")
        summary = self._required_text(entry, "summary")
        published = self._required_text(entry, "published")
        updated = self._required_text(entry, "updated")

        authors = [
            name
            for author in entry.findall(self._atom_tag("author"))
            if (name := self._optional_text(author, "name")) is not None
        ]

        categories = [
            category
            for category in (
                element.attrib.get("term")
                for element in entry.findall(self._atom_tag("category"))
            )
            if category is not None
        ]

        primary_category_element = entry.find(
            self._arxiv_tag("primary_category")
        )

        primary_category = (
            primary_category_element.attrib.get("term")
            if primary_category_element is not None
            else None
        )

        abstract_url = None
        pdf_url = None

        for link in entry.findall(self._atom_tag("link")):
            href = link.attrib.get("href")

            if not href:
                continue

            rel = link.attrib.get("rel")
            title_attribute = link.attrib.get("title")

            if rel == "alternate":
                abstract_url = href

            elif title_attribute == "pdf":
                pdf_url = href

        return RawArxivEntry(
            id_url=id_url,
            title=title,
            summary=summary,
            authors=authors,
            published=published,
            updated=updated,
            categories=categories,
            primary_category=primary_category,
            abstract_url=abstract_url,
            pdf_url=pdf_url,
        )

    def _required_text(
        self,
        element: ElementTree.Element,
        tag: str,
    ) -> str:
        """Extract required child text."""
        value = self._optional_text(element, tag)

        if value is None:
            raise ArxivParsingError(
                f"Missing required arXiv field: {tag}"
            )

        return value

    def _optional_text(
        self,
        element: ElementTree.Element,
        tag: str,
    ) -> str | None:
        """Extract and normalize optional child text."""
        child = element.find(self._atom_tag(tag))

        if child is None or child.text is None:
            return None

        value = " ".join(child.text.split())

        return value or None