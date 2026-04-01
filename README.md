# sphinx-longmd

A Sphinx builder that compiles an entire documentation project into **one long-form Markdown file** with a machine-readable **provenance sidecar**.

It works from the assembled, resolved doctree — not from raw source files or rendered HTML. This means cross-references, domain objects, toctree ordering, and substitution expansion are all handled by Sphinx before the builder touches them.

## Installation

```bash
pip install sphinx-longmd
```

Or for development:

```bash
git clone <repo-url>
cd sphinx-longmd
pip install -e ".[test]"
```

## Quick start

Add the extension to your `conf.py`:

```python
extensions = [
    "myst_parser",      # if you use .md sources
    "sphinx_longmd",
]
```

Build:

```bash
sphinx-build -b longmd docs/source docs/_build/longmd
```

Output:

```
docs/_build/longmd/
  index.longmd.md          # one long Markdown document
  index.longmd.map.json    # provenance sidecar
  assets/                  # copied images
```

You can also invoke the builder via the packaging entry point without adding it to `extensions`:

```bash
pip install sphinx-longmd
sphinx-build -b longmd docs/source docs/_build/longmd
```

## Configuration

All options are set in `conf.py`. None are required — the defaults produce a useful build.

| Option | Type | Default | Description |
|---|---|---|---|
| `longmd_strict` | `bool` | `False` | Fail the build on unsupported nodes or unresolved references instead of degrading gracefully. |
| `longmd_raw_html` | `bool` | `True` | Pass raw HTML content through to the Markdown body. When `False`, raw HTML is recorded in the sidecar only. |

### Example `conf.py`

```python
project = "MyProject"
extensions = ["myst_parser", "sphinx_longmd"]

# Source format configuration
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# Optional: strict mode for CI
# longmd_strict = True

# Optional: suppress raw HTML in body
# longmd_raw_html = False
```

## Output artifacts

### `<root_doc>.longmd.md`

One Markdown file containing the entire project in toctree reading order.

**Dialect: LongMD/MyST v0**

- ATX headings with fixed doc-boundary offsets (root title = `#`, child doc titles = `##`, subsections follow from there).
- Standard Markdown for prose, lists, code blocks, links, images.
- HTML `<a id="..."></a>` anchors for stable link targets.
- HTML comments `<!-- longmd:start-file ... -->` / `<!-- longmd:end-file ... -->` for document boundaries.
- MyST colon-fenced directives (`:::{note}`, `:::{py:function}`, etc.) for Sphinx semantics that don't fit plain Markdown.
- `:::{sphinx-node}` fallback for unknown or third-party extension nodes.
- A synthetic table of contents at the top linking to each document.

### `<root_doc>.longmd.map.json`

Machine-readable provenance sidecar. Top-level keys:

| Key | Contents |
|---|---|
| `version` | Schema version (`"1.0"`) |
| `profile` | Output dialect (`"longmd_myst_v0"`) |
| `root_doc` | Root document name |
| `output_file` | Name of the Markdown file |
| `document_order` | Source documents in assembly order |
| `anchors` | `{canonical_key: emitted_id}` for every anchor |
| `aliases` | `{alias_id: emitted_id}` |
| `objects` | Domain object metadata (domain, type, name, anchor, source) |
| `assets` | Copied image/download records |
| `spans` | Output line ranges mapped to source locations |
| `warnings` | Warnings with code, message, severity, source location |
| `losses` | Semantic degradation records with level and details |
| `stats` | Build statistics: line count, anchor count, timing, etc. |

### `assets/`

Copies of images referenced by the Markdown body, with collision-safe filenames.

## What it handles

**Phase 1 — structural Markdown:** headings, paragraphs, emphasis, strong, inline code, bullet/enumerated lists, block quotes, fenced code blocks, links, images, document boundaries, synthetic TOC.

**Phase 2 — Sphinx semantics:** admonitions (note, warning, tip, etc.), rubrics, tables, figures with captions, footnotes/citations, field lists with API info-field normalization (Parameters, Returns, Raises), Python domain object descriptions, glossary terms, definition lists, version-modified blocks, topics, sidebars, unresolved cross-reference handling.

**Phase 3 — hardening:** custom/third-party node fallback, raw content policy, strict vs. non-strict failure modes, diagnostics and telemetry in sidecar, doc-prefix anchor collision resolution.

## Anchor collision strategy

When two source documents share the same heading ID (e.g. both have `## See Also`):

1. First document claiming the ID gets it as-is: `see-also`
2. Second document gets a doc-prefixed form: `reference-api--see-also`
3. Third document: `tutorials-index--see-also`

Prefixed IDs are tied to the document name, so they're stable across toctree reorderings. No numeric suffixes are used for cross-document collisions.

## Strict mode

Enable with `longmd_strict = True` in `conf.py` or `-D longmd_strict=1` on the command line.

In strict mode, the build **fails** (non-zero exit) when:

- An unsupported/custom node is encountered (instead of emitting a `:::{sphinx-node}` fallback)
- A non-HTML `.. raw::` directive is encountered
- Unresolved cross-references remain after Sphinx resolution

Use this in CI to catch regressions. Use non-strict mode (the default) for development and exploratory builds.

## Running tests

```bash
pip install -e ".[test]"

# All tests
pytest tests/ -v

# By phase
pytest tests/test_builder_smoke.py tests/test_anchors.py tests/test_assets.py tests/test_emitters.py tests/test_sidecar.py -v   # Phase 1
pytest tests/test_phase2.py -v   # Phase 2
pytest tests/test_phase3.py -v   # Phase 3
```

## Compatibility

| Dependency | Tested versions | Notes |
|---|---|---|
| Python | 3.11, 3.12, 3.14 | Requires 3.11+ for `dataclass(slots=True)` |
| Sphinx | 9.x | Adapts to `inline_all_toctrees` signature changes at runtime |
| MyST-Parser | 4.x, 5.x | Optional; required only if your project uses `.md` sources |
| docutils | 0.21+ | Comes with Sphinx |

The builder adapts to Sphinx API changes via runtime signature introspection (see `assemble.py`). It does not depend on deprecated `sphinx.io` or legacy `master_doc`.

## Architecture

```
Sphinx read phase (owned by Sphinx/MyST)
  ↓
assemble.py    — inline_all_toctrees → one master doctree
  ↓
anchors.py     — global pre-scan: register all anchors before emission
  ↓
emit/writer.py — priority-sorted emitter registry, line-number accounting
emit/structural.py, emit/inline.py, emit/sphinx_blocks.py, emit/objects.py
  ↓
emit/fallback.py — unknown nodes → :::{sphinx-node} or StrictModeError
  ↓
assets.py      — copy referenced images
sidecar.py     — serialize provenance JSON
diagnostics.py — timing + counters → sidecar stats
```

The builder never reads rendered HTML. It never regex-converts source files. It works from the resolved doctree.

## License

See LICENSE file.
