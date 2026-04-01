# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

`sphinx-longmd` is a Sphinx extension that compiles an entire documentation project into **one long-form Markdown file** with a machine-readable **provenance sidecar** (`.longmd.map.json`).

It works from the assembled, resolved doctree — not from raw source files or rendered HTML. The builder inlines the full toctree into one master doctree, resolves all cross-references, then emits Markdown via a priority-sorted emitter registry.

The output dialect is **LongMD/MyST v0**: standard Markdown for prose, HTML anchors for stable IDs, MyST colon-fenced directives for Sphinx semantics, and a `:::{sphinx-node}` fallback for unknown nodes.

## Development commands

### Setup

```bash
pip install -e ".[test]"
```

### Testing

```bash
# Full suite (116 tests)
pytest tests/ -v

# Quick — unit tests only, no Sphinx builds (~0.1s)
pytest tests/test_anchors.py tests/test_assets.py tests/test_emitters.py tests/test_sidecar.py -v

# By phase
pytest tests/test_builder_smoke.py tests/test_anchors.py tests/test_assets.py tests/test_emitters.py tests/test_sidecar.py -v  # Phase 1
pytest tests/test_phase2.py -v   # Phase 2
pytest tests/test_phase3.py -v   # Phase 3

# Or use the runner
./run_tests.sh all      # full suite
./run_tests.sh quick    # unit tests only
./run_tests.sh phase1   # etc.
```

### Manual build for inspection

```bash
sphinx-build -b longmd tests/fixtures/basic_mixed_source /tmp/longmd_out
cat /tmp/longmd_out/index.longmd.md
python -c "import json; print(json.dumps(json.load(open('/tmp/longmd_out/index.longmd.map.json')), indent=2))"
```

### Strict mode

```bash
sphinx-build -b longmd -D longmd_strict=1 tests/fixtures/custom_nodes /tmp/longmd_strict
# Expected: non-zero exit due to custom_card node
```

## Architecture

### Data flow

```
Sphinx read phase (Sphinx/MyST own this)
  → assemble.py: inline_all_toctrees → one master doctree
  → builder.py: _plan_anchors → global anchor registry (pre-scan)
  → emit/writer.py: recursive emission with line-number tracking
  → assets.py: copy images → assets/
  → sidecar.py: serialize provenance → .map.json
```

### Module boundaries (enforced by contracts.md §11)

```
src/sphinx_longmd/
  __init__.py          # setup(app), config registration
  builder.py           # LongMdBuilder — orchestration only, no emitter logic
  assemble.py          # doctree assembly, doc boundaries, document order
  anchors.py           # anchor planning and lookup (global pre-scan)
  context.py           # dataclasses: Emission, EmissionContext, SpanRecord, etc.
  assets.py            # asset registration + copy (no Markdown generation)
  sidecar.py           # sidecar model + JSON serialization (no doctree walking)
  diagnostics.py       # timing + counters → sidecar stats
  emit/
    writer.py          # emitter registry + central line-accounting writer
    structural.py      # sections, titles, lists, paragraphs, code blocks, boundaries
    inline.py          # emphasis, strong, literal, references, images, text
    sphinx_blocks.py   # admonitions, tables, figures, footnotes, topics, sidebars
    objects.py         # desc family, field lists, glossary, pending xrefs
    fallback.py        # unknown nodes → :::{sphinx-node}, raw content policy, strict mode
```

**Hard rules:**
- `builder.py` must not contain emitter logic (no `*Emitter` classes)
- `emit/` modules must not perform filesystem writes
- `sidecar.py` must not walk the doctree directly
- `assets.py` must not generate Markdown text
- Anchors are never invented ad-hoc during emission — always from the registry

### Emitter priority system

Emitters are registered with a numeric priority. Highest-priority match wins. Key ranges:
- 95–100: structural boundaries (start_of_file, toctree suppression)
- 85–90: sections, titles, comments, desc family, glossary
- 80–84: paragraphs, lists, code blocks, admonitions, tables, figures, field lists
- 70–78: inline formatting, references, images, footnote refs
- 40–42: raw node policy
- 1: fallback (catch-all for unknown Element nodes)

### Anchor collision resolution

When two docs share the same heading ID (e.g. both have `## See Also`):
1. First doc gets `see-also`
2. Second doc gets `reference-api--see-also` (doc-prefixed, stable)
3. No numeric suffixes for cross-doc collisions

### Sphinx version compatibility

`assemble.py` introspects `inline_all_toctrees` at import time to handle Sphinx 8.x vs 9.x signature changes. The `_INLINE_PARAMS` set determines which arguments to pass.

`builder.py._collect_objects` wraps all domain values in `str()` because Sphinx returns `_TranslationProxy` objects that aren't JSON-serializable.

### Strict mode

Controlled by `longmd_strict` config value. When True:
- `FallbackEmitter` raises `StrictModeError` instead of emitting `:::{sphinx-node}`
- `RawNodeEmitter` raises on non-HTML raw content
- Post-emission check fails on unresolved cross-references
- `builder.py` catches `StrictModeError` and converts to `RuntimeError` with actionable diagnostics

## Test fixtures

| Fixture | Location | Purpose |
|---|---|---|
| `basic_mixed_source` | `tests/fixtures/basic_mixed_source/` | Phase 1: `.rst` root + `.md` child + `.rst` child, cross-refs, image |
| `objects_and_glossary` | `tests/fixtures/objects_and_glossary/` | Phase 2: admonitions, py:function/class/method, glossary, tables, figures, footnotes |
| `custom_nodes` | `tests/fixtures/custom_nodes/` | Phase 3: fake extension (`_ext/fake_card.py`), raw HTML/LaTeX, unresolved refs, strict mode |

Each fixture is a self-contained Sphinx project with its own `conf.py`.

## Key design decisions

1. **AST-first, not source-regex.** We never read `.rst`/`.md` source. We work from the resolved doctree.
2. **Pre-scan anchors, don't invent them during emission.** `_plan_anchors` runs before any Markdown is generated.
3. **Doc-prefix over numeric suffix.** Collision resolution uses docname slugs for stability.
4. **Degrade, don't crash.** Unknown nodes get `:::{sphinx-node}` + sidecar warning. Strict mode is opt-in.
5. **Body for readers, sidecar for machines.** Raw LaTeX goes to sidecar. Index entries go to sidecar. The Markdown body stays readable.
6. **Line numbers are real.** `emit/writer.py` tracks a running cursor and stamps every span with actual output line ranges.

## Common tasks

### Adding a new emitter

1. Create the emitter class in the appropriate `emit/` module
2. Set `priority` (check existing ranges above)
3. Implement `matches(node)` and `emit(node, ctx, visit_children)`
4. Register it in the module's `register_*_emitters()` function
5. Add a fixture case and test assertion
6. Verify with `pytest tests/ -v`

### Debugging emission

```python
# Dump the assembled doctree for a fixture:
from sphinx.application import Sphinx
app = Sphinx('tests/fixtures/basic_mixed_source', 'tests/fixtures/basic_mixed_source',
             '/tmp/debug', '/tmp/debug/.doctrees', 'longmd')
app.build()
tree = app.env.get_doctree('index')
print(tree.pformat())  # full doctree dump
```

### Checking sidecar provenance

```bash
sphinx-build -b longmd tests/fixtures/basic_mixed_source /tmp/out
python -c "
import json
d = json.load(open('/tmp/out/index.longmd.map.json'))
for s in d['spans'][:10]:
    print(f\"L{s['out_start_line']:4d}-{s['out_end_line']:4d}  {s['node_type']:20s}  {s.get('source_docname','?')}\")
print(f'{len(d[\"spans\"])} spans, {len(d[\"warnings\"])} warnings, {len(d[\"losses\"])} losses')
"
```
