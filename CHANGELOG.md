# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — Unreleased

Initial release covering Phases 1–4 of the implementation plan.

### Added

- Custom Sphinx builder `longmd` emitting one long-form Markdown artifact
  from the assembled, resolved doctree.
- Output dialect **LongMD/MyST v0**: ATX headings, standard Markdown prose,
  HTML anchors/comments for boundaries, MyST colon-fenced directives for
  Sphinx semantics, `:::{sphinx-node}` fallback for unknown nodes.
- Provenance sidecar (`<root_doc>.longmd.map.json`) with anchors, aliases,
  objects, assets, spans (with real output line numbers), warnings, losses,
  and build statistics.
- Asset manager: copies referenced images into `assets/` with collision-safe
  filenames.

#### Phase 1 — structural Markdown
- Headings, paragraphs, emphasis, strong, inline code.
- Bullet and enumerated lists, block quotes.
- Fenced code blocks with language info strings.
- Internal links rewritten to same-file fragment links.
- Images with asset copy and URL rewrite.
- Document boundary markers (HTML comments).
- Synthetic table of contents.

#### Phase 2 — Sphinx semantic families
- Admonitions: note, warning, tip, important, etc. as MyST directives.
- Generic admonitions with custom titles.
- Rubrics as bold text (not headings).
- Tables as Markdown pipe tables.
- Figures with captions and anchors.
- Footnotes and citations in `[^name]` syntax.
- Field lists: generic (bold-label) and API info-field normalization
  (Parameters, Returns, Raises, Keyword Arguments, Attributes, Yields).
- Python domain object descriptions as `:::{py:function}` etc.
- Glossary terms with anchored definitions.
- Definition lists.
- Version-modified blocks (versionadded, versionchanged, deprecated).
- Topics and sidebars.
- Pending cross-reference handling with sidecar warnings.
- Sidecar object metadata from Sphinx domain registries.

#### Phase 3 — hardening
- Strict mode (`longmd_strict = True`): deterministic build failure on
  unsupported nodes, non-HTML raw content, or unresolved references.
- Raw content policy: HTML passes through (configurable), non-HTML
  recorded in sidecar only.
- Doc-prefix anchor collision resolution: stable, docname-based IDs
  instead of numeric suffixes.
- Custom/third-party node survival via `:::{sphinx-node}` fallback with
  full sidecar warning and loss records.
- Comment node suppression.
- Enhanced diagnostics: timing buckets, fallback counters, loss tracking.

#### Phase 4 — release hardening
- Production README with install, usage, config reference.
- Compatibility notes for Sphinx 9.x, MyST-Parser 4.x/5.x, Python 3.11+.
- Changelog, versioning notes.
- CI-friendly test runner script.
- Acceptance report against `validation.md`.

### Compatibility
- Python 3.11+
- Sphinx 9.x (adapts to API changes via runtime introspection)
- MyST-Parser 4.x / 5.x (optional)
- docutils 0.21+
