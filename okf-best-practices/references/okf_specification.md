# Open Knowledge Format (OKF) v0.3 — Specification & Implementation Guide

## 1. Overview & Purpose

The **Open Knowledge Format (OKF)** is an open, vendor-neutral specification originally introduced by Google Cloud and maintained at [open-knowledge-format/open-knowledge-format](https://github.com/open-knowledge-format/open-knowledge-format). It formalizes the "LLM Wiki pattern" into a portable standard: a directory tree of UTF-8 Markdown documents with YAML 1.2 frontmatter.

**OKF v0.3** refines v0.2 with formal conformance rules, current-event trust tier semantics, unified path/link resolution, bundle-level metadata (`okf_version`, `title`, `description`, `license`), concept retirement (`superseded_by`), explicit `x-` extension rules, and full Attested Computation contracts.

> **Canonical Repository:** Always reference `open-knowledge-format/open-knowledge-format`. Older locations (`GoogleCloudPlatform/open-knowledge-format` for v0.2 and the frozen `GoogleCloudPlatform/knowledge-catalog/okf` snapshot) are superseded.

### Goals & Non-Goals

* **Goals**: Universal producer format (humans, agents, pipelines), deterministic consumer traversal, frictionless cross-org exchange, first-class provenance/trust/freshness/lifecycle/attestation without prescribing a runtime.
* **Non-Goals**: Fixed `type` taxonomy, prescribed storage/serving runtime, replacing domain schemas (Avro, Protobuf, OpenAPI — OKF links to them), or packaging ABIs for executors/attesters.

---

## 2. Core Architecture & Bundle Layout

An **OKF Bundle** is a self-contained directory tree. It may be distributed as a Git/Mercurial repo (recommended), an archive, or a subdirectory of a larger repository (e.g., `docs/`).

```text
bundle-root/                    # Identified by root index.md with frontmatter
  index.md                      # Optional. Bundle metadata (frontmatter) + root directory map
  log.md                        # Optional. Chronological update log (NO frontmatter)
  <concept>.md                  # Concept at bundle root
  <asset>                       # Non-.md file (image, script, SQL, license)
  <subdirectory>/
    index.md                    # Optional. Directory map (NO frontmatter)
    <concept>.md                # Concept ID: <subdirectory>/<concept>
```

### Terminology & File Classification

1. **Bundle Root**: Top directory of the bundle. A bundle-root `index.md` with frontmatter marks the bundle root when nested in a larger repository.
2. **Concept**: Any `.md` file that is not reserved (`index.md`, `log.md`) and whose frontmatter contains a non-empty `type` string.
3. **Concept ID**: The relative file path within the bundle root with the `.md` suffix removed (e.g., `tables/orders`).
4. **Non-Concept Markdown**: A `.md` file without frontmatter or without a non-empty `type` (such as `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `SKILL.md`). Consumers skip it; it does **not** break conformance (validators SHOULD warn `W120`).
5. **Asset**: Any file whose name does not end in `.md` (images, `.py` attesters, `.sql` files). Assets are not concepts but MAY be targets of links or path fields.
6. **Dot-Paths & Symlinks**: Files/directories whose names begin with `.` are excluded from the bundle. Consumers read only inside the bundle root and MUST NOT follow symlinks resolving outside the bundle root.
7. **Encoding**: All text files MUST be UTF-8.

### Reserved Filenames

| Filename | Allowed Frontmatter | Purpose |
| :--- | :--- | :--- |
| `index.md` | **Root only** (optional) | Progressive disclosure directory map (`# Heading` + `* [Title](relative-url) - description`). Subdirectory `index.md` MUST have no frontmatter. |
| `log.md` | **Never** | Chronological history grouped under `## YYYY-MM-DD` headings, newest date first. |

> **Optional GitHub Rendering Convention**: For repositories browsed via GitHub web UI, you MAY add a relative symlink `ln -s index.md README.md` in directories containing `index.md` (keeping symlink targets inside the bundle root). Note that OKF v0.3 consumers treat `README.md` without `type` as a skipped non-concept file, and strict OKF validators warn (`W120`).

---

## 3. Document Structure Specification

Every concept document consists of a **YAML Frontmatter Block** followed by a **Markdown Body**.

### A. Frontmatter Syntax (§4)

* Line 1 MUST be exactly `---`; frontmatter ends at the next line that is exactly `---`.
* Frontmatter MUST parse as a **YAML 1.2 mapping** with the core schema.
* Producers MUST NOT write duplicate keys (consumers MAY reject duplicates).
* Producers SHOULD quote scalars that look like numbers or booleans (e.g., `okf_version: "0.3"`), timestamps, and actor strings.
* Producers SHOULD NOT use custom YAML tags.
* When updating an existing concept, producers SHOULD NOT re-serialize unchanged values and MUST preserve unknown keys.

### B. Frontmatter Fields (§4.1, §5, §8.1, §10)

#### Core Concept Fields

| Field | Status | Type | Description |
| :--- | :--- | :--- | :--- |
| `type` | **REQUIRED** | String | Non-empty concept archetype (e.g., `BigQuery Table`, `BigQuery Dataset`, `API Endpoint`, `Metric`, `Playbook`, `Reference`, `Attested Computation`, or project-specific types). Consumers MUST accept unknown types. |
| `title` | Optional | String | Human-friendly display title. If omitted, consumers MAY derive one from the filename. |
| `description` | Optional | String | One-sentence summary used by `index.md` generators, search snippets, and previews. |
| `resource` | Optional | Path/URI | Canonical URI or in-bundle path of the underlying production asset. Omit for abstract concepts. |
| `tags` | Optional | List of Strings | YAML list (`[sales, orders]`). **Scalar `tags` values count as one single tag** — consumers MUST NOT split on commas. |

#### Provenance Fields (`sources` & `usage_window`)

| Field | Status | Type | Description |
| :--- | :--- | :--- | :--- |
| `sources` | Optional | List of Objects | Lineage materials from which the concept derives. (Single object accepted as 1-item list.) |
| `sources[].resource` | **REQUIRED in entry** | Path/URI/Scope | Absolute URL, in-bundle path, or unfollowable scope descriptor (e.g., `all queries in BigQuery project X`). |
| `sources[].id` | Optional (Req. if cited) | String | Stable unique key within the concept, used as footnote label `[^id]` for per-claim attribution. |
| `sources[].title` | Optional | String | Human-readable label. |
| `sources[].author` | Optional | Actor | Credibility signal (authority): actor (§5) who produced the source. |
| `sources[].usage_count` | Optional | Number | Credibility signal (liveness): usage count during `usage_window`. Compare only by order of magnitude / alive vs. dead. |
| `sources[].last_modified` | Optional | RFC 3339 | Credibility signal (recency): when the source itself last changed (distinct from `generated.at`). |
| `usage_window` | Req. with `usage_count` | `{ from, to }` | Sibling of `sources` giving the RFC 3339 time range for `usage_count`. An entry MAY define its own `usage_window` override. |

#### Trust & Lifecycle Fields

| Field | Status | Type | Description |
| :--- | :--- | :--- | :--- |
| `generated` | Optional | `{ by, at }` | `by` REQUIRED (actor). `at` = RFC 3339 time of last **meaningful** edit (do not bump for whitespace, formatting, or link fixes). Replaces v0.1 `timestamp`. |
| `verified` | Optional | List of `{ by, at }` | Verification events (bare `{ by, at }` object accepted as 1-item list). Both `by` and `at` REQUIRED per event; incomplete entries are ignored. |
| `status` | Optional | String | `draft`, `stable` (default when absent), or `deprecated`. Any other value is treated as **not current** and excluded from current-knowledge views. |
| `superseded_by` | Optional (v0.3) | Path/URI | Path to replacement concept. Meaningful ONLY when `status: deprecated`. |
| `stale_after` | Optional | RFC 3339 | Instant when concept becomes stale (`now >= stale_after`). Omit if unknown; do not invent dates. Unparseable values MUST NOT be treated as fresh. |
| `timestamp` | Legacy (v0.1) | RFC 3339 | Fallback for `generated.at` in v0.1/unmigrated docs when `generated` is absent. |

#### Bundle-Root `index.md` Metadata (§8.1 — Root Index Only)

| Field | Status | Type | Description |
| :--- | :--- | :--- | :--- |
| `okf_version` | Recommended | String | Quoted version string, e.g., `"0.3"`. |
| `title` | Optional | String | Display name of the bundle. |
| `description` | Optional | String | One sentence stating scope and when agents should pick this bundle. |
| `license` | Optional | String/Path | SPDX expression (e.g., `CC-BY-4.0`) or path to a license file in the bundle. |

#### Extension Keys (§4.1)

Producers MAY add extension keys at any level (top-level or nested inside `sources[]`, `generated`, `verified[]`, `executor`, `attester`, or root `index.md`). Future OKF specs will never define keys starting with `x-`; producers SHOULD use `x-<producer>-<name>` (e.g., `x-acme-not`). Consumers MUST NOT reject unknown keys; producers modifying existing files MUST preserve them.

### C. Body Layer (§4.2)

* Dialect: **CommonMark** with **GitHub Flavored Markdown (GFM) tables** and **`[^label]` footnotes**. Producers SHOULD NOT rely on other Markdown extensions.
* Favor structured elements (`##` headings, lists, tables) over long unformatted prose blocks.
* Conventional headings (all optional):
  * `# Schema` — structured fields/columns of an asset.
  * `# Examples` — concrete usage examples (e.g., fenced SQL/code blocks).
  * `# Computation` — sanctioned computation block of an `Attested Computation`.
* **Per-Claim Attribution**: Use keyed footnotes `[^<source-id>]` resolving to `sources[].id` rather than positional indexes, numbered `[^1]`, or legacy `# Citations` lists. Consumers join on `id` and do not parse footnote text.

---

## 4. Timestamps, Actors & Trust Tier Semantics

### Timestamps (§5)

Applies to `generated.at`, `verified[].at`, `stale_after`, `sources[].last_modified`, `usage_window.from`, and `usage_window.to`:

| Form | RFC 3339 Rule | Example | Meaning |
| :--- | :--- | :--- | :--- |
| Date-time | `date-time` (with offset) | `"2026-06-30T14:00:00Z"` | Exact instant. Date-times without an offset are **invalid**. |
| Date-only | `full-date` | `"2026-06-30"` | Start of that day in UTC (`2026-06-30T00:00:00Z`). |

* Consumers MUST accept both quoted strings and YAML-native timestamps.
* Producers SHOULD quote timestamps and SHOULD use the `date-time` form for `generated.at` and `verified[].at`.

### Actor Convention (§7)

Applies to `generated.by`, `verified[].by`, and `sources[].author`:

| Form | Meaning | Trust Tier Effect (in `verified[].by`) | Example |
| :--- | :--- | :--- | :--- |
| `<producer>/<version>` | Agent or automated tool | `machine-confirmed` | `reference_agent/gemini-2.5-pro` |
| `human:<id>` | Individual person | **`human-reviewed`** (only this scheme!) | `human:ahormati` |
| `team:<id>` | Group or team | `machine-confirmed` | `team:finance-fpa` |
| `process:<id>` | Automated job/pipeline | `machine-confirmed` | `process:finance-nightly` |
| `<other>:<id>` | Custom scheme | `machine-confirmed` (treated as non-human) | `service:catalog-bot` |

Producers MUST NOT infer `human:<id>` from system usernames or git config; record a human verification only when that person confirmed the content and supplied their ID.

### Trust Tier Calculation (§5.3)

An event in `verified` is **current** iff `verified[].at >= generated.at` (as instants), or when `generated` is absent:

* **No current events** → `unverified` (older events remain in `verified` as audit history: "verified before the last change").
* **Current events from non-`human:` actors only** → `machine-confirmed`.
* **At least one current event from `human:<id>`** → `human-reviewed`.

Trust tiers are advisory signals, never access control; consumers MUST NOT reject unverified concepts.

### Concept Retirement & Moves (§5.4)

* **Retire**: Keep the file, set `status: deprecated`, and set `superseded_by` to the replacement concept path if one exists.
* **Move / Rename**: Preserve `generated` and `verified` on the moved file, and leave a short deprecated concept stub at the old path with `superseded_by` pointing to the new path so existing links and IDs keep working.

---

## 5. Links, Path Fields & the Bundle Graph (§6)

### Unified Resolution Rules

Both Markdown links in the body (`[text](target)` and reference-style links; NOT `[[wikilinks]]`) and frontmatter path fields (`resource`, `sources[].resource`, `computation`, `executor.resource`, `attester.resource`, `superseded_by`) resolve by the exact same three rules:

1. **URI scheme** (e.g., `https:`, `bq://`) → external URI (note: `sources[].resource` containing spaces is a scope descriptor, not a path).
2. **Leading `/`** (e.g., `/tables/orders.md`) → resolves from the **bundle root**.
3. **Any other value** (e.g., `./other.md`, `../tables/orders.md`) → resolves from the **directory of the file that contains it**.

* **Security boundary**: Any path resolving outside the bundle root is external; consumers MUST NOT read it from the local filesystem.
* **Identifiers**: Targets are RFC 3986 URI references. Percent-encode spaces and reserved characters (`my%20concept.md`). Paths are case-sensitive; avoid paths differing only by case.
* **Both forms valid**: Consumers MUST resolve both `/`-rooted and file-relative targets.
* **Authoring best practice**:
  * **Body Markdown links**: Write **file-relative** paths (`../tables/orders.md`, `./other.md`) so GitHub and static Markdown renderers resolve them properly when the bundle is in a subdirectory (e.g., `docs/`).
  * **Frontmatter path fields**: Write **bundle-root paths with leading `/`** (`/references/attesters/sql_equality.py`, `/metrics/gross-margin.md`) or explicit file-relative paths. *(v0.3 Breaking Change: bare path fields without leading `/` no longer resolve from the bundle root.)*
* **v0.2 Compatibility Fallback**: When reading bundles declaring `okf_version` `<= "0.2"` or no version, consumers MAY try resolving a bare path field from the bundle root if it does not resolve from its file's directory (this fallback does NOT apply to body links).

### Bundle Graph & `references/`

* Only the directory hierarchy expresses implicit parent/child structure; Markdown links represent untyped directed relationships.
* Graph edges are formed by (1) concept-to-concept body links and (2) frontmatter path fields that resolve to concepts in the bundle.
* Consumers MUST tolerate broken links (e.g., references to unwritten concepts).
* `references/` is a conventional directory for copies of external documentation, run instructions, attester scripts, and supporting concepts.

---

## 6. Attested Computations (§10)

An `Attested Computation` is a standalone concept (`type: Attested Computation`) pairing a metric/value definition with a sanctioned, verifiable computation.

### Contract Fields

| Field | Status | Type | Description |
| :--- | :--- | :--- | :--- |
| `runtime` | **REQUIRED** | String | Execution environment (e.g., `bigquery`, `postgres`, `dbt`, `python`, `Looker`); defines parameter binding semantics. |
| `parameters` | Optional | List of Objects | Typed named inputs: `{ name, type, required }` (`name` and `type` REQUIRED; `required` defaults to `false`). Common types: `string`, `integer`, `number`, `boolean`, `date`, `timestamp`. |
| `computation` | Optional | Path/URI | Path to an external file holding the computation. If set, do NOT also include an inline fenced code block under `# Computation`. |
| `executor` | Optional | `{ resource, receipt }` | `resource` = path to run instructions/code; `receipt` = list of runtime evidence fields returned (e.g., `[job_id, executed_sql, result]`). |
| `attester` | Optional | `{ resource }` | Path to deterministic code (NO LLM) that inspects a receipt and returns `{ ok: boolean, reason?: string }`. |

### Lookup & Execution Gate Rules

1. **Locating Computation (§10.3)**: If `computation` is set, read that file; otherwise read the first fenced code block in the `# Computation` section (at any ATX heading depth, ending at the next heading of same/higher level). If neither exists, the concept is not attestable.
2. **Agent Constraints**: Copy sanctioned computations verbatim from approved sources — never write or alter the query/model. At runtime, supply only declared parameter values.
3. **Attestation Gate (§10.2, §10.5)**:
   * Consumers MUST NOT label a value attested without both `runtime` and `attester`.
   * If attestation fails (`ok: false`), withhold the value entirely and display `reason`.
   * If execution/attestation passes and `now >= stale_after`, show the value with a staleness warning.
   * Report `verified` (definition review recorded in the bundle) separately from runtime attestation (per-run verification via receipt).

---

## 7. Conformance, Consumer Rules & Versioning (§11, §12)

### Bundle Conformance (§11.1)

A bundle conforms to OKF v0.3 if and only if:

1. Every frontmatter block in any `.md` file under the bundle root parses as a valid YAML mapping (no unclosed fences, no duplicate keys).
2. Every present `index.md` and `log.md` obeys §8 and §9 (no frontmatter in subdirectory `index.md` or any `log.md`; `## YYYY-MM-DD` date headings in `log.md`).

Non-concept `.md` files (no frontmatter or no `type`) do NOT make a bundle non-conformant.

### Consumer Normalization & Robustness (§11.2)

* `null`, `""`, and `[]` are equivalent to an absent key.
* For list-typed fields (`tags`, `sources`, `verified`, `parameters`), a single scalar or mapping counts as a 1-element list. A scalar `tags` value is ONE tag (MUST NOT split on commas).
* Ignore family entries missing required keys (`sources` without `resource`, `verified` without `by` and `at`, `parameters` without `name` and `type`) and SHOULD warn.
* Unknown vocabulary values (e.g., non-standard `status`) MUST be retained (MAY warn); non-standard `status` is treated as not current.
* Never reject a bundle for missing optional fields, unknown `type`, unknown keys, missing `index.md`, or broken links.
* Unknown `okf_version` values SHOULD be consumed best-effort, never refused (§12).

### Conflict Resolution Order

When two concepts disagree, resolve using the first difference in order:

1. **Current status**: `stable` or `draft` beats `deprecated` or unknown `status`.
2. **Trust tier**: `human-reviewed` > `machine-confirmed` > `unverified`.
3. **Freshness**: non-stale beats stale.
4. **Recency**: later `generated.at` wins.

---

## 8. Changes from v0.2 & Migration Guide (§12.1, §13, Appendix B)

### Breaking Changes (v0.2 → v0.3)

| Change | Impact on v0.2 Bundles | Consumer Fallback |
| :--- | :--- | :--- |
| Bare path fields without leading `/` resolve from the **containing file's directory** (§6.2). | Bare bundle-root paths in v0.2 frontmatter fail to resolve unless prefixed with `/`. | If `okf_version <= "0.2"` or absent, try bundle root for bare path fields. |
| Trust tier uses **only current verification events** where `verified[].at >= generated.at` (§5.3). | Concepts edited after human review drop from `human-reviewed` to `unverified` (or `machine-confirmed`). | None needed (downgrading trust is the safe direction). |

### Key Clarifications & Additions in v0.3

* **Additive**: `superseded_by` for deprecated concepts + move/retire pattern (§5.4); bundle metadata (`title`, `description`, `license`) in root `index.md` (§8.1); formal `x-` extension rules at all levels (§4.1).
* **Clarifications**: `.md` files without `type` are non-concepts; YAML 1.2 core schema + no duplicate keys; date-only RFC 3339 values mean UTC midnight (`T00:00:00Z`), while date-times without offsets are invalid; unknown `status` is not current; scalar `tags` is one tag; `team:` actor scheme added (`machine-confirmed`); `log.md` has no frontmatter; `Attested Computation` requires `runtime` and `attester` to attest.

### Migration Steps to v0.3

* **From v0.2**:
  1. Add `okf_version: "0.3"`, `title`, and `description` to bundle-root `index.md` frontmatter (remove frontmatter from subdirectory `index.md` and all `log.md`).
  2. Prefix bundle-root frontmatter path fields (`resource`, `sources[].resource`, `computation`, `executor.resource`, `attester.resource`, `superseded_by`) with `/`.
  3. Convert scalar comma-separated `tags` to YAML lists (`[a, b]`).
  4. Add `superseded_by` to deprecated concepts with replacements; add offsets to any offset-less date-times.
  5. Re-check `generated.at` vs `verified[].at` and flag concepts needing fresh human review.
* **From v0.1**: Replace `timestamp` with `generated: { by, at }` (keep `timestamp` only if producer is unknown), convert `# Citations` sections to `sources[]` + `[^id]` footnotes, then follow the v0.2 → v0.3 steps.

---

## 9. Worked Reference Examples (OKF v0.3)

### Bundle-Root `index.md`

```markdown
---
okf_version: "0.3"
title: Acme Retail Analytics
description: Tables, metrics, policies, and sanctioned computations for Acme Retail finance.
license: CC-BY-4.0
---

# Acme Retail Analytics

* [Tables](tables/index.md) - Core warehouse tables.
* [Metrics](metrics/index.md) - Business definitions of headline metrics.
* [Computations](computations/index.md) - Sanctioned Attested Computations.
```

### `log.md` (No Frontmatter)

```markdown
# Bundle History

## 2026-11-18
* **Update**: Migrated bundle to OKF v0.3 and added `superseded_by` to legacy margin metric.

## 2026-06-30
* **Creation**: Added [User Analytics Table](tables/user-clicks.md) and [Revenue Computation](computations/revenue.md).
```

### Concept Document (`tables/user-clicks.md`)

````markdown
---
type: BigQuery Table
title: User Analytics Table
description: One row per tracked clickstream event from the web application.
resource: https://console.cloud.google.com/bigquery?p=my-project&d=analytics&t=user_clicks
tags: [data-warehouse, marketing, tracking]
status: stable
generated: { by: "reference_agent/gemini-2.5-pro", at: "2026-07-07T15:26:00Z" }
verified:
  - { by: "human:ahormati", at: "2026-07-08T09:00:00Z" }
stale_after: "2026-12-31T00:00:00Z"
sources:
  - id: raw-events
    resource: https://console.cloud.google.com/bigquery?p=my-project&d=analytics&t=raw_events
    title: Raw Events Ingestion Table
    author: "team:data-platform"
    usage_count: 1200
    last_modified: "2026-07-06T00:00:00Z"
usage_window: { from: "2026-06-01T00:00:00Z", to: "2026-06-30T00:00:00Z" }
---

Collects deduplicated clickstream events from the web client.[^raw-events]

# Schema

| Column | Type | Description |
| --- | --- | --- |
| `event_id` | STRING | Globally unique event identifier for deduplication. |
| `user_id` | INT64 | Foreign key into [User Profiles](../auth/profiles.md). |
| `click_timestamp` | TIMESTAMP | Event timestamp in UTC. |

# Examples

```sql
SELECT user_id, COUNT(*) AS clicks
FROM `my-project.analytics.user_clicks`
GROUP BY 1;
```

[^raw-events]: Raw Events Ingestion Table
````

### Attested Computation (`computations/revenue.md`)

````markdown
---
type: Attested Computation
title: Revenue for fiscal year
description: Recognized revenue for a fiscal year, per Finance policy.
tags: [finance, revenue]
status: stable
runtime: bigquery
parameters:
  - { name: year, type: integer, required: true }
executor:
  resource: /references/skills/run-on-bq.md
  receipt: [job_id, executed_sql, result]
attester:
  resource: /references/attesters/sql_equality.py
generated: { by: "reference_agent/gemini-2.5-pro", at: "2026-06-20T14:00:00Z" }
verified: { by: "human:ahormati", at: "2026-06-25T09:00:00Z" }
stale_after: "2026-12-31T00:00:00Z"
sources:
  - id: rev-policy
    resource: /policies/revenue-recognition.md
    title: Revenue Recognition Policy
    author: "team:finance-fpa"
    last_modified: "2026-04-02T00:00:00Z"
---

# Computation

```sql
SELECT SUM(amount) AS revenue
FROM finance.recognized_revenue
WHERE fiscal_year = @year
```

Recognized revenue per the [Revenue Recognition Policy](../policies/revenue-recognition.md).[^rev-policy]

[^rev-policy]: Revenue Recognition Policy
````

### Deprecated Concept (`metrics/gross-margin-legacy.md`)

```markdown
---
type: Metric
title: Gross Margin (legacy)
description: Retired gross-margin definition using product cost only.
status: deprecated
superseded_by: /metrics/gross-margin.md
generated: { by: "human:jsmith", at: "2024-01-15T10:00:00Z" }
verified: { by: "human:jsmith", at: "2024-01-15T10:00:00Z" }
---

This metric is retired. Use [Gross Margin](gross-margin.md) for current analyses.
```
