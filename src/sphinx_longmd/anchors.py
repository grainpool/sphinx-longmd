"""Anchor planning and lookup.

This module builds a global anchor registry from the assembled doctree
**before** any Markdown is emitted. Emitters never invent anchors ad hoc;
they look them up here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


def slugify_docname(docname: str) -> str:
    """Turn a Sphinx docname (``api/index``) into a slug (``api-index``)."""
    return re.sub(r"[^a-z0-9]+", "-", docname.lower()).strip("-")


def _make_safe_id(raw: str) -> str:
    """Normalise *raw* into a character-safe HTML id value."""
    s = raw.replace("::", "-").replace(":", "-").replace(".", "-")
    s = re.sub(r"[^a-zA-Z0-9_-]", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    return s.strip("-").lower()


@dataclass(slots=True)
class AnchorRecord:
    """One registered anchor target."""

    canonical_key: str
    emitted_id: str
    aliases: list[str] = field(default_factory=list)
    docname: str = ""
    source_path: str | None = None
    source_line: int | None = None
    node_type: str = ""


class AnchorRegistry:
    """Global anchor/alias registry for one build.

    Population order:
    1. register document-boundary anchors
    2. register section anchors
    3. register explicit-target anchors
    (phases 2+: objects, glossary, footnotes, etc.)
    """

    def __init__(self) -> None:
        self._by_canonical: dict[str, AnchorRecord] = {}
        self._emitted_ids: dict[str, str] = {}  # emitted_id -> canonical_key
        self._aliases: dict[str, str] = {}  # alias_id -> canonical_key

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        canonical_key: str,
        preferred_id: str,
        *,
        aliases: list[str] | None = None,
        docname: str = "",
        source_path: str | None = None,
        source_line: int | None = None,
        node_type: str = "",
    ) -> AnchorRecord:
        """Register a new anchor target.

        When the *preferred_id* is already taken, the registry tries a
        doc-prefixed form ``<slug>--<preferred_id>`` before falling back
        to numeric suffixes.  This produces stable, self-documenting IDs
        like ``reference-api--see-also`` instead of ``see-also-1``.

        Raises ``ValueError`` on canonical-key duplication.
        """
        if canonical_key in self._by_canonical:
            raise ValueError(
                f"Duplicate canonical key: {canonical_key!r} "
                f"(already registered as {self._by_canonical[canonical_key].emitted_id!r})"
            )

        emitted = self._deduplicate_with_doc_prefix(preferred_id, docname)
        alias_ids: list[str] = []
        for alias_raw in aliases or []:
            safe = _make_safe_id(alias_raw)
            if safe and safe != emitted and safe not in self._emitted_ids:
                alias_ids.append(safe)
                self._aliases[safe] = canonical_key

        record = AnchorRecord(
            canonical_key=canonical_key,
            emitted_id=emitted,
            aliases=alias_ids,
            docname=docname,
            source_path=source_path,
            source_line=source_line,
            node_type=node_type,
        )
        self._by_canonical[canonical_key] = record
        self._emitted_ids[emitted] = canonical_key
        return record

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def emitted_id_for_canonical(self, canonical_key: str) -> str | None:
        rec = self._by_canonical.get(canonical_key)
        return rec.emitted_id if rec else None

    def alias_ids_for_canonical(self, canonical_key: str) -> list[str]:
        rec = self._by_canonical.get(canonical_key)
        return list(rec.aliases) if rec else []

    def lookup_from_existing_id(
        self, docname: str, raw_id: str
    ) -> str | None:
        """Try to resolve an existing local ID to the global emitted ID.

        Checks canonical keys ``<docname>::<raw_id>`` and ``doc::<raw_id>``
        as well as direct emitted-ID and alias lookups.
        """
        # Try docname-qualified canonical key.
        ckey = f"{docname}::{raw_id}"
        rec = self._by_canonical.get(ckey)
        if rec:
            return rec.emitted_id

        # Try doc-level canonical key.
        dkey = f"doc::{raw_id}"
        rec = self._by_canonical.get(dkey)
        if rec:
            return rec.emitted_id

        # Try direct emitted-ID match.
        if raw_id in self._emitted_ids:
            return raw_id

        # Try alias lookup.
        ckey2 = self._aliases.get(raw_id)
        if ckey2:
            rec2 = self._by_canonical.get(ckey2)
            if rec2:
                return rec2.emitted_id

        return None

    # ------------------------------------------------------------------
    # Iteration / serialisation helpers
    # ------------------------------------------------------------------

    def all_records(self) -> list[AnchorRecord]:
        return list(self._by_canonical.values())

    def anchors_dict(self) -> dict[str, str]:
        """``{canonical_key: emitted_id}`` for sidecar serialisation."""
        return {r.canonical_key: r.emitted_id for r in self._by_canonical.values()}

    def aliases_dict(self) -> dict[str, str]:
        """``{alias_id: emitted_id}`` for sidecar serialisation."""
        out: dict[str, str] = {}
        for alias_id, ckey in self._aliases.items():
            rec = self._by_canonical.get(ckey)
            if rec:
                out[alias_id] = rec.emitted_id
        return out

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _deduplicate(self, preferred: str) -> str:
        safe = _make_safe_id(preferred) or "anchor"
        if safe not in self._emitted_ids:
            return safe
        for i in range(1, 10_000):
            candidate = f"{safe}-{i}"
            if candidate not in self._emitted_ids:
                return candidate
        raise ValueError(  # pragma: no cover – defensive
            f"Cannot deduplicate anchor id {preferred!r} after 10 000 attempts"
        )

    def _deduplicate_with_doc_prefix(self, preferred: str, docname: str) -> str:
        """Resolve emitted-ID collisions using doc-prefixed forms.

        Priority order:
        1. *preferred* as-is (e.g. ``see-also``)
        2. ``<doc-slug>--<preferred>`` (e.g. ``reference-api--see-also``)
        3. numeric suffixes on the doc-prefixed form (last resort)
        """
        safe = _make_safe_id(preferred) or "anchor"
        if safe not in self._emitted_ids:
            return safe

        # Try doc-prefixed form.
        if docname:
            slug = slugify_docname(docname)
            prefixed = f"{slug}--{safe}"
            if prefixed not in self._emitted_ids:
                return prefixed
            # Numeric suffixes on the prefixed form.
            for i in range(1, 10_000):
                candidate = f"{prefixed}-{i}"
                if candidate not in self._emitted_ids:
                    return candidate

        # No docname — fall back to plain numeric suffixes.
        return self._deduplicate(preferred)
