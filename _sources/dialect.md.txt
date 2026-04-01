# Dialect Specification

This document defines the complete output vocabulary of `sphinx-longmd`.
It is intended for developers building parsers, renderers, or tooling
that consumes `.longmd.md` files.

A LongMD file is valid Markdown extended with three additional
conventions: HTML anchors, HTML comments for document boundaries, and
MyST-style colon-fenced directive blocks. A parser that handles
standard Markdown plus these three conventions can fully consume the
output.

---

## 1. Document structure

### 1.1 Overall shape

A `.longmd.md` file has this structure:

```
<root document boundary>
<synthetic table of contents>
<root document content>
  <child document boundary>
  <child document content>
  <child document boundary end>
  ...
<root document boundary end>
```

All content from every source document in the Sphinx project appears
in this single file, in toctree reading order.

### 1.2 Document boundary markers

Every source document (including the root) is wrapped in boundary
markers using HTML comments:

```html
<a id="document-<doc-slug>"></a>
<!-- longmd:start-file docname="<docname>" source="<source-path>" -->

...content...

<!-- longmd:end-file docname="<docname>" -->
```

**Fields:**

| Field | Description | Example |
|---|---|---|
| `doc-slug` | Lowercased, hyphenated form of the docname | `api-index` |
| `docname` | Sphinx docname (path without extension) | `api/index` |
| `source` | Absolute or relative path to the source file | `/home/user/docs/api/index.rst` |

**Parsing rules:**

- Start markers always appear as a pair: an `<a id>` anchor immediately
  followed by the `<!-- longmd:start-file ... -->` comment.
- End markers are a single `<!-- longmd:end-file ... -->` comment.
- Boundary markers may be nested (child docs appear inside the root
  doc's boundaries).
- The `docname` attribute is the authoritative document identifier.

### 1.3 Synthetic table of contents

Immediately after the root document's start boundary, a synthetic
TOC appears:

```markdown
**Contents**

- [Index](#document-index)
- [Getting Started](#document-getting-started)
- [API Reference](#document-api-reference)
```

Each entry is a standard Markdown link targeting the `document-<slug>`
anchor of the corresponding source document.

---

## 2. Anchors

### 2.1 HTML anchor elements

All stable link targets use HTML `<a>` elements with `id` attributes:

```html
<a id="identifier"></a>
```

Anchors appear immediately before the block they target. Multiple
anchors may be stacked when a block has aliases:

```html
<a id="canonical-id"></a>
<a id="alias-id"></a>
## Section title
```

### 2.2 Anchor ID patterns

| Source construct | ID pattern | Example |
|---|---|---|
| Document boundary | `document-<doc-slug>` | `document-api-index` |
| Section heading | original section ID | `installation` |
| Section (collision) | `<doc-slug>--<section-id>` | `reference-api--see-also` |
| Explicit label | original label | `install-note` |
| Object description | signature-derived ID | `demo.frob`, `demo.Widget` |
| Glossary term | `term-<normalized>` | `term-widget` |
| Figure | auto-generated or explicit | `fig-architecture` |

### 2.3 Collision resolution

When two source documents produce the same ID:

1. First document keeps the bare ID: `see-also`
2. Subsequent documents get a doc-prefixed form: `reference-api--see-also`

The prefix uses the docname slug with `--` as separator. This is
stable across toctree reorderings.

---

## 3. Headings

ATX-style headings only. Level is determined by document nesting:

```markdown
# Root document title
## Child document title
### Child document subsection
#### Deeper subsection
```

**Heading level rules:**

- Root document title: `#`
- Child document titles (one toctree level deep): `##`
- Subsections within a child document: `###`, `####`, etc.
- Maximum depth: `######` (6 levels)

Headings are always preceded by their section's anchor(s).

---

## 4. Inline formatting

### 4.1 Emphasis

```markdown
*italic text*
```

### 4.2 Strong emphasis

```markdown
**bold text**
```

### 4.3 Inline code

```markdown
`code_here`
```

When the content contains backticks:

```markdown
`` code`with`backticks ``
```

### 4.4 Title references

Rendered as emphasis (same as 4.1):

```markdown
*Some Title*
```

---

## 5. Links

### 5.1 Internal fragment links

All in-project cross-references are same-file fragment links:

```markdown
[visible text](#anchor-id)
```

Examples:

```markdown
[Installation](#installation)
[API Reference](#document-api-reference)
[`demo.frob()`](#demo.frob)
[widget](#term-widget)
```

### 5.2 External links

Links resolved to external URLs (including intersphinx):

```markdown
[visible text](https://example.com/page)
```

### 5.3 Unresolved references

When Sphinx cannot resolve a reference, the target text appears as
inline code without a link:

```markdown
`unknown_target`
```

A warning is recorded in the sidecar.

---

## 6. Lists

### 6.1 Bullet lists

```markdown
- First item
- Second item
- Third item with
  continuation on next line
```

### 6.2 Enumerated lists

```markdown
1. First item
2. Second item
3. Third item with
   continuation on next line
```

---

## 7. Block quotes

```markdown
> Quoted text here
> spanning multiple lines
>
> With paragraph breaks inside
```

---

## 8. Code blocks

Fenced code blocks with optional language info string:

````markdown
```python
def hello():
    print("world")
```
````

When the code content itself contains triple backticks, the fence
uses additional backticks:

`````markdown
````markdown
```python
nested
```
````
`````

---

## 9. Images

### 9.1 Simple images

```markdown
![alt text](assets/filename.png)
```

Image paths point to the `assets/` directory relative to the
`.longmd.md` file. The builder copies referenced images there with
collision-safe filenames.

### 9.2 Figures with captions

```markdown
<a id="figure-id"></a>
![alt text](assets/filename.png)

*Caption text in italics*
```

The caption, if present, appears as an italic paragraph immediately
after the image. A legend, if present, follows as normal prose.

---

## 10. Tables

Markdown pipe tables:

```markdown
**Table caption**

| Column A | Column B | Column C |
| --- | --- | --- |
| cell 1 | cell 2 | cell 3 |
| cell 4 | cell 5 | cell 6 |
```

**Rules:**

- The separator row (`| --- | --- |`) always appears after the
  header row.
- If the source table has no explicit header, the first body row
  is promoted to header (Markdown requires a header row).
- Table captions appear as bold text above the table.
- Cell content is flattened to single lines.

---

## 11. Transitions

Horizontal rules:

```markdown
---
```

---

## 12. Footnotes and citations

### 12.1 Footnote references (inline)

```markdown
Some text[^1] and more[^named].
```

### 12.2 Footnote definitions

```markdown
[^1]: Auto-numbered footnote body.
[^named]: Named footnote body.
```

Citations use the same syntax with the citation label:

```markdown
[^CIT2024]: Citation body text.
```

---

## 13. Definition lists

```markdown
Term one
: Definition of term one.

Term two
: Definition of term two.
```

---

## 14. MyST colon-fenced directive blocks

These are the primary extension beyond standard Markdown. They use
MyST-Parser's colon-fence syntax: three or more colons, curly-braced
directive name, optional argument, optional field options, body, and
closing colons.

### 14.1 General syntax

```markdown
:::{directive-name} optional argument
:option-key: option value

Body content here.
:::
```

**Parsing rules:**

- Opening fence: `:::` followed by `{directive-name}`
- The directive name is inside curly braces
- An optional space-separated argument follows the closing brace
- Field-style options (`:key: value`) appear on subsequent lines
  before a blank line
- Body content follows the blank line
- Closing fence: `:::`
- Fences must be at least three colons and match in length

### 14.2 Nesting

Colon-fenced blocks can nest. Inner blocks appear within outer blocks:

```markdown
:::{py:class} demo.Widget(name)
:source-doc: objects

Description of the class.

:::{py:method} render()
:source-doc: objects

Description of the method.
:::
:::
```

---

## 15. Admonitions

Specific admonition types emitted as MyST directives:

```markdown
:::{note}
Body text.
:::

:::{warning}
Body text.
:::

:::{tip}
Body text.
:::

:::{important}
Body text.
:::
```

**All admonition directive names:**

`note`, `warning`, `tip`, `important`, `hint`, `caution`, `danger`,
`error`, `attention`, `seealso`

### 15.1 Generic admonitions

Admonitions with custom titles:

```markdown
:::{admonition} Custom Title Here
Body text.
:::
```

---

## 16. Version-modified blocks

```markdown
:::{versionadded}
Added in 2.0: Description of what was added.
:::

:::{versionchanged}
Changed in 3.1: Description of what changed.
:::

:::{deprecated}
Deprecated since 4.0: Use new_function instead.
:::
```

**Directive names:** `versionadded`, `versionchanged`, `deprecated`

---

## 17. Object descriptions

Sphinx domain objects are emitted as MyST directive blocks with
domain-qualified names.

### 17.1 General form

```markdown
<a id="signature-derived-id"></a>
:::{domain:objtype} signature text
:source-doc: docname

Description body.

**Parameters**
- `x` (`int`): first value
- `y` (`str`): display label

**Returns**
- `bool`: whether it succeeded

**Raises**
- `ValueError`: duplicate anchor
:::
```

### 17.2 Python domain examples

```markdown
:::{py:function} demo.frob(x, y=0)
:source-doc: api/index

Frob two values.

**Parameters**
- **x** (*int*) – first value
- **y** (*str*) – display label

**Returns**
whether export succeeded

**Return type**
bool

**Raises**
**ValueError** – duplicate anchor
:::
```

```markdown
:::{py:class} class demo.Widget(name)
:source-doc: api/index

A reusable widget.
:::
```

```markdown
:::{py:method} render()
:source-doc: api/index

Render the widget.
:::
```

### 17.3 Object directive names

The directive name is `{domain}:{objtype}`. Common examples:

| Directive | Source construct |
|---|---|
| `py:function` | `.. py:function::` |
| `py:class` | `.. py:class::` |
| `py:method` | `.. py:method::` |
| `py:attribute` | `.. py:attribute::` |
| `py:data` | `.. py:data::` |
| `py:exception` | `.. py:exception::` |
| `py:module` | `.. py:module::` |
| `c:function` | `.. c:function::` |
| `js:function` | `.. js:function::` |

Any Sphinx domain may appear. If the domain or objtype is unknown,
the fallback directive name is `object`.

### 17.4 Object directive options

| Option | Description |
|---|---|
| `:source-doc:` | Sphinx docname of the source document |
| `:sig:` | Additional signatures (for overloaded objects) |

### 17.5 Normalized field sections

Inside object description bodies, API info fields are rendered as
bold section headers followed by bullet lists:

```markdown
**Parameters**
- `name` (`type`): description
- `name` (`type`): description

**Keyword Arguments**
- `name` (`type`): description

**Attributes**
- `name` (`type`): description

**Returns**
- `type`: description

**Yields**
- `type`: description

**Raises**
- `ExceptionType`: description
```

Alternatively, Sphinx may pre-render these as bold-label sections
(when the Python domain transforms them before the builder sees them):

```markdown
**Parameters**
- **name** (*type*) – description

**Return type**
type

**Raises**
**ExceptionType** – description
```

Both forms are valid. Parsers should accept either.

---

## 18. Glossary terms

```markdown
<a id="term-widget"></a>
**widget**
: A reusable component.

<a id="term-anchor"></a>
**anchor**
: A stable link target in the emitted document.
```

Each term has an anchor (typically `term-<normalized-name>`), the
term itself in bold, and the definition using definition-list syntax
(`: ` prefix).

---

## 19. Generic field lists

Field lists outside object descriptions render as bold-label
paragraphs:

```markdown
**Status:** stable

**Audience:** maintainers
```

---

## 20. Rubrics

Rubrics render as bold text (they are not headings and do not create
TOC entries):

```markdown
**Examples**
```

---

## 21. Topics

```markdown
**Topic Title**

Topic body content.
```

### 21.1 Sidebars

```markdown
> **Sidebar — Title**
>
> Sidebar body content.
```

### 21.2 Local table of contents

`.. contents::` directives are suppressed (the builder provides its
own synthetic TOC).

---

## 22. Raw HTML

When `longmd_raw_html` is enabled (the default), raw HTML from the
source documents passes through verbatim:

```html
<div class="custom-banner">Hello from raw HTML</div>
```

Non-HTML raw content (e.g. LaTeX) is omitted from the body and
recorded in the sidecar only.

---

## 23. Fallback blocks

When a node has no dedicated emitter, it is wrapped in a
`sphinx-node` directive:

```markdown
:::{sphinx-node}
:node-type: full.python.path.ClassName
:source-doc: docname
:source-line: 42
:preservation: degraded

Readable fallback body text extracted from child nodes.
:::
```

### 23.1 Fallback directive options

| Option | Description |
|---|---|
| `:node-type:` | Fully qualified Python class name of the node |
| `:source-doc:` | Sphinx docname where the node originated |
| `:source-line:` | Source line number (may be empty) |
| `:preservation:` | Always `degraded` |

**Parsing guidance:** A parser encountering `:::{sphinx-node}` should
render the body content as-is (it is already readable Markdown) and
optionally surface the metadata options as debug information.

---

## 24. Provenance sidecar (`<root_doc>.longmd.map.json`)

The sidecar is a companion JSON file that carries machine-readable
provenance for every construct in the Markdown body. Its existence
is guaranteed; the Markdown file is self-contained for reading but
the sidecar enables tooling.

### 24.1 Top-level schema

```json
{
  "version": "1.0",
  "profile": "longmd_myst_v0",
  "root_doc": "index",
  "output_file": "index.longmd.md",
  "document_order": ["index", "intro", "api/index"],
  "anchors": { "canonical_key": "emitted_id" },
  "aliases": { "alias_id": "emitted_id" },
  "objects": { "domain:type:name": { ... } },
  "assets": [ { "kind": "image", "source_uri": "...", "output_path": "..." } ],
  "spans": [ { "out_start_line": 1, "out_end_line": 5, ... } ],
  "warnings": [ { "code": "...", "message": "...", "severity": "warning" } ],
  "losses": [ { "code": "...", "level": "moderate", "details": "..." } ],
  "stats": { "emitted_lines": 1618, "anchors_total": 277, ... }
}
```

### 24.2 Span records

Each span maps an output line range to its source:

```json
{
  "out_start_line": 42,
  "out_end_line": 48,
  "source_docname": "api/index",
  "source_path": "docs/source/api/index.rst",
  "source_line": 15,
  "node_type": "section",
  "anchors": []
}
```

Line numbers are 1-based. Spans are monotonically ordered by
`out_start_line`.

### 24.3 Warning records

```json
{
  "code": "unknown_node",
  "message": "No dedicated emitter for thirdparty.CardNode",
  "severity": "warning",
  "source_docname": "intro",
  "source_line": 12,
  "node_type": "thirdparty.CardNode"
}
```

**Warning codes:** `unknown_node`, `unresolved_xref`,
`raw_content_omitted`, `unresolved_reference`, `asset_missing`.

### 24.4 Loss records

```json
{
  "code": "custom_node_degraded",
  "level": "moderate",
  "node_type": "thirdparty.CardNode",
  "source_docname": "intro",
  "source_line": 12,
  "details": "emitted via sphinx-node fallback"
}
```

**Loss levels:** `minor`, `moderate`, `major`.

**Loss codes:** `custom_node_degraded`, `raw_content_sidecar_only`,
`benign_wrapper`.

---

## 25. Summary of syntactic forms

For quick reference, here is every syntactic form a parser must handle
to fully consume LongMD/MyST v0 output:

| Form | Standard? | Example |
|---|---|---|
| ATX headings | Markdown | `## Title` |
| Paragraphs | Markdown | plain text |
| Emphasis | Markdown | `*text*` |
| Strong | Markdown | `**text**` |
| Inline code | Markdown | `` `code` `` |
| Links | Markdown | `[text](#anchor)` |
| Images | Markdown | `![alt](path)` |
| Bullet lists | Markdown | `- item` |
| Enumerated lists | Markdown | `1. item` |
| Block quotes | Markdown | `> text` |
| Fenced code blocks | Markdown | ` ```lang ... ``` ` |
| Horizontal rules | Markdown | `---` |
| Pipe tables | GFM | `\| a \| b \|` |
| Footnote refs | Extended MD | `[^name]` |
| Footnote defs | Extended MD | `[^name]: body` |
| Definition lists | Extended MD | `term\n: definition` |
| HTML anchors | HTML-in-MD | `<a id="..."></a>` |
| HTML comments | HTML-in-MD | `<!-- longmd:... -->` |
| Raw HTML | HTML-in-MD | `<div>...</div>` |
| Colon-fenced directives | MyST | `:::{name} arg\n...\n:::` |

A parser targeting **minimal viable support** needs only standard
Markdown plus HTML anchor/comment pass-through. The colon-fenced
directives and extended Markdown forms (footnotes, definition lists,
tables) add semantic richness but degrade to readable text if a
parser ignores them.
