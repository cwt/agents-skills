---
name: okf-best-practices
description: Open Knowledge Format (OKF v0.3) bundle rules, YAML frontmatter schemas, provenance, trust tiers, freshness, lifecycle (superseded_by), Attested Computations, link/path resolution, and consumer conformance constraints. Use when creating, updating, migrating, reading, or validating OKF bundles, docs/ folders, AGENTS.md-referenced knowledge files, or Markdown+frontmatter knowledge graphs.
license: MIT
metadata:
  author: Chaiwat Suttipongsakul
  version: "2.0"
---

# Open Knowledge Format (OKF v0.3) Best Practices & Rules

This skill enforces strict adherence to the **Open Knowledge Format (OKF) v0.3** specification (`open-knowledge-format/open-knowledge-format`) for structured, portable, agent- and human-readable organizational knowledge.

---

## 1. Trigger Conditions

You **MUST** load and follow this skill if the active task involves:

* Creating, editing, migrating, validating, or reading Markdown files in an OKF Bundle (commonly under `docs/`, a bundle root with `index.md`, or paths listed in `AGENTS.md`).
* Documenting datasets, tables, APIs, metrics, policies, runbooks, lessons learned, architectural mandates, or sanctioned `Attested Computation` concepts.
* Managing provenance (`sources`), trust tiers (`generated`, `verified`), freshness (`stale_after`), or lifecycle retirement (`status`, `superseded_by`).
* Parsing or traversing directory trees representing a semantic knowledge graph.

---

## 2. Core Specification Rules

### 2.1. Bundle Structure & File Classification

An **OKF Bundle** is a UTF-8 directory tree rooted at the **bundle root** (identified by a bundle-root `index.md` with frontmatter when nested in a larger repo, or the top directory of `.md` concepts).

* **Concept**: A `.md` file that is **not** a reserved filename and has YAML frontmatter with a non-empty `type` string. Its **Concept ID** is its relative path from the bundle root without `.md` (e.g., `metrics/gross-margin`).
* **Non-Concept Markdown**: Any `.md` file without frontmatter or without a non-empty `type` (e.g., `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `SKILL.md`). Consumers skip it; it does **not** break conformance, though OKF validators SHOULD warn (`W120`).
* **Asset**: Any non-`.md` file (images, SQL files, Python attesters, license files). Assets can be linked or targeted by path fields, and are not concepts.
* **Boundaries**: Files and directories starting with `.` are NOT part of the bundle. Consumers MUST read only inside the bundle root and MUST NOT follow symbolic links that escape it.

### 2.2. Reserved Filenames & GitHub Rendering

Do **NOT** use these filenames for concept documents at any directory level (consumers MUST NOT treat them as concepts):

* `index.md`: Directory map for progressive disclosure (`# Section` + `* [Local Rule](./local-rule.md) - description` matching each concept's `description`).
  * **Bundle-root `index.md`**: MAY (and SHOULD) include frontmatter with bundle metadata (`okf_version: "0.3"`, `title`, `description`, `license`, plus extension keys). Bundle metadata applies to the bundle, not to individual concepts. Regenerating `index.md` MUST preserve existing root frontmatter.
  * **Subdirectory `index.md`**: MUST have **no frontmatter**.
* `log.md`: Chronological bundle modification history.
  * MUST have **no frontmatter** at any level.
  * Date headings MUST use ISO 8601 `## YYYY-MM-DD`, newest date first.
* **GitHub Directory Rendering (Optional Repo Convention)**: If automatic directory rendering on GitHub is desired, you MAY create a relative symlink `ln -s index.md README.md` (staying strictly inside the bundle root). Note that OKF v0.3 itself does not require `README.md` symlinks, and strict OKF validators warn (`W120`) on non-concept `.md` files.

### 2.3. Frontmatter Syntax & Metadata Schema

Every concept MUST start on line 1 with `---`, close frontmatter with `---`, and be followed by a Markdown body.

* **Syntax (§4)**: Frontmatter MUST parse as a **YAML 1.2 mapping** (core schema). Producers MUST NOT write duplicate keys, SHOULD NOT use custom YAML tags, SHOULD quote values that look like numbers or booleans (e.g., `okf_version: "0.3"`), and SHOULD NOT re-serialize unchanged values when editing.
* **Extensions (§4.1)**: Custom keys are permitted at **any level** (including inside `sources[]`, `generated`, `verified[]`, `executor`, `attester`, and root `index.md`). Future OKF specs will never define `x-` keys — name custom keys `x-<producer>-<name>` (e.g., `x-acme-owner`). Producers updating a file MUST preserve unknown keys.

#### Core Fields

| Field | Status | Type | Rules & Purpose |
| --- | --- | --- | --- |
| `type` | **REQUIRED** | String | Non-empty concept kind (e.g., `BigQuery Table`, `Metric`, `Playbook`, `Reference`, `Attested Computation`, or domain types like `runbook`, `policy`). No central registry. |
| `title` | Optional | String | Human-friendly display name (consumers may derive from filename if absent). |
| `description` | Optional | String | One-sentence summary for `index.md`, search snippets, and previews. |
| `resource` | Optional | Path/URI | Canonical URI or bundle path of the underlying asset; omit for abstract concepts. |
| `tags` | Optional | List of Strings | YAML list (`[a, b]`). **Never** write comma-separated scalars (`tags: a, b`), which v0.3 reads as one single tag. |

#### Provenance, Trust & Lifecycle Fields

| Family | Field | Type / Shape | Rules & Purpose |
| --- | --- | --- | --- |
| **Provenance** | `sources` | List of Objects | Each entry REQUIRES `resource` (URL, bundle path, or scope descriptor). Optional: `id` (required if cited via `[^id]`), `title`, `author` (actor), `usage_count`, `last_modified`. |
| **Provenance** | `usage_window` | `{ from, to }` | Sibling of `sources` (required when `usage_count` is set); individual entries MAY override with their own `usage_window`. |
| **Generation** | `generated` | `{ by, at }` | `by` REQUIRED (actor). `at` (optional, SHOULD be `date-time`) = last **meaningful** change (skip for whitespace/format/link fixes). Replaces legacy v0.1 `timestamp`. |
| **Verification** | `verified` | List (or 1 Object) | Events `{ by, at }` (both REQUIRED per event). Older events stay as history; only **current** events determine trust tier. |
| **Lifecycle** | `status` | String | `draft`, `stable` (default when absent), or `deprecated`. Any other value is treated as **not current**. |
| **Retirement** | `superseded_by` | Path/URI | Replacement concept path; meaningful ONLY with `status: deprecated`. Leave a deprecated stub at old path on renames/moves. |
| **Freshness** | `stale_after` | RFC 3339 | Concept is stale when `now >= stale_after`. Omit if unknown; do not invent dates. Malformed values are never fresh. |

#### Trust Tier Calculation (§5.3 — v0.3 Rule)

An event in `verified` is **current** ONLY when `verified[].at >= generated.at` (compared as instants), or when `generated` is absent:

1. **No current event** → `unverified`
2. **Current events from non-`human:` actors only** (`process:`, `team:`, `<producer>/<version>`, other schemes) → `machine-confirmed`
3. **At least one current event from `human:<id>`** → `human-reviewed`

Trust tiers are advisory, not access control. Modifying a concept's meaning advances `generated.at`, automatically invalidating older human reviews until re-verified.

### 2.4. Actors & Timestamps

* **Actors (§7)** (`generated.by`, `verified[].by`, `sources[].author`):
  * Agents/tools: `<producer>/<version>` (e.g., `reference_agent/gemini-2.5-pro`).
  * Other actors: `<scheme>:<id>` using `human:<id>`, `team:<id>`, or `process:<id>` (only `human:` yields `human-reviewed`).
  * **Never fabricate `human:<id>`** from git config or OS logins, and never add `verified` entries to content you generated unless that human confirmed it and gave their ID.
* **Timestamps (§5)**: All timestamp keys (`generated.at`, `verified[].at`, `stale_after`, `sources[].last_modified`, `usage_window.from`, `usage_window.to`) MUST use RFC 3339:
  * `date-time` with offset (e.g., `"2026-06-30T14:00:00Z"` or `"+07:00"`). Date-times without offset are INVALID.
  * `full-date` (e.g., `"2026-06-30"`), interpreted as `00:00:00Z` UTC.
  * Producers SHOULD quote timestamps and use full `date-time` for `generated.at` and `verified[].at`.

### 2.5. Attested Computations (§10)

Use a standalone concept with `type: Attested Computation` for sanctioned, verifiable calculations:

* **Required**: `runtime` (e.g., `bigquery`, `postgres`, `dbt`, `python`, `Looker`).
* **Optional**: `parameters` (list of `{ name, type, required }` with `name` & `type` required), `computation` (path to external file; omit if using inline block), `executor` (`{ resource, receipt }`), `attester` (`{ resource }` — deterministic non-LLM code returning `{ ok, reason? }`).
* **Computation lookup**: Uses `computation` path field if set; otherwise the first fenced code block under a `# Computation` heading (any ATX level).
* **Strict Rules**: NEVER author or alter a sanctioned computation — copy verbatim from an approved source. When executing, supply only parameter values. Consumers MUST NOT display a value as attested without both `runtime` and `attester`, or if execution/attestation failed or didn't run. Report both `verified` (definition review) and attestation (runtime receipt).

### 2.6. Body Layout, Interlinking & Path Resolution

* **Markdown Dialect (§4.2)**: CommonMark + GFM tables + keyed `[^label]` footnotes. Favor headings (`# Schema`, `# Examples`, `# Computation`), lists, and tables over long prose blocks.
* **Per-Claim Attribution**: Cite claims with keyed footnotes ``[^<source-id>]`` matching `sources[].id` (not numbered `[^1]` or legacy `# Citations` lists).
* **Unified Path & Link Resolution (§6 — v0.3 Breaking Change)**:
  1. Values with a URI scheme (e.g., `https:`, `bq://`) → external URL/URI.
  2. Values starting with `/` → resolve from the **bundle root**.
  3. Any other value → resolve from the **directory of the file that contains it** (v0.3 breaking change for bare frontmatter path fields!).
  4. Paths escaping the bundle root are external and MUST NOT be read from the local filesystem.
  5. Percent-encode spaces/reserved chars (`%20`); paths are case-sensitive.
* **Authoring Guidance**:
  * **Body Markdown links**: Use relative paths from the current file so GitHub and static renderers resolve them properly inside subdirectories: `[Local Rule](./local-rule.md)`, `[Mandates](./mandates/mandates.md)`, `[Home](../index.md)`. Never use `[Architecture](/architecture.md)` in bodies if the bundle lives under a subdirectory like `docs/`. Only standard Markdown/reference links count (`[[wikilinks]]` are not OKF links).
  * **Frontmatter path fields** (`resource`, `sources[].resource`, `computation`, `executor.resource`, `attester.resource`, `superseded_by`): Prefer leading `/` from the bundle root (e.g., `` `/references/attesters/sql_equality.py` ``, `` `/metrics/gross-margin.md` ``), or explicit file-relative paths — never bare bundle-root paths without `/`.
  * **v0.2 Compatibility**: When reading bundles declaring `okf_version` `<= "0.2"` or no version, consumers MAY try bundle-root fallback for bare frontmatter path fields (not body links) and v0.1 `timestamp` / `# Citations` fallbacks.
* **Graph Edges (§6.4) & `references/`**: Both concept-to-concept links and path fields resolving to concepts form directed graph edges (only the directory tree defines parent/child). `references/` is conventional for external material copies, run instructions, and code.

### 2.7. Consumer Conformance & Fault-Tolerance (§11)

* **Conformance (§11.1)**: A bundle is conformant when every frontmatter block in `.md` files under the root parses as a YAML mapping and present `index.md` / `log.md` files match §8 and §9.
* **Value Normalization (§11.2)**: Treat `null`, `""`, and `[]` as absent; treat a single item in list fields (`tags`, `sources`, `verified`, `parameters`) as a 1-item list; never split scalar `tags` on commas; ignore family entries missing required keys (`sources` without `resource`, `verified` without `by`/`at`, `parameters` without `name`/`type`).
* **Graceful Tolerance**: Never reject or crash on missing optional fields, missing `index.md`, unknown `type`, unknown extension keys, or broken links (unwritten concepts).
* **Conflict Resolution**: Prefer concepts in order: (1) current status (`stable`/`draft`) > non-current; (2) `human-reviewed` > `machine-confirmed` > `unverified`; (3) not stale > stale; (4) later `generated.at`.

---

## 3. Production & Validation Checklist

* [ ] Bundle-root `index.md` declares `okf_version: "0.3"`, `title`, `description` (and `license` if known); subdirectory `index.md` and all `log.md` files have **no frontmatter**.
* [ ] Every concept starts on line 1 with `---`, closes with `---`, has no duplicate keys, quotes ambiguous scalars/timestamps/actors, and declares a non-empty `type`.
* [ ] `tags` is a YAML list (`[a, b]`), not a comma-separated scalar string.
* [ ] `sources` entries are objects with `resource` (and `id` for `[^id]` footnotes); `usage_count` has a `usage_window`.
* [ ] `generated: { by, at }` records only meaningful edits (`at` as RFC 3339 `date-time` with offset); `verified` is never fabricated.
* [ ] `status: deprecated` includes `superseded_by` (starting with `/` or file-relative) when a replacement exists; `stale_after` is omitted unless a review date is known.
* [ ] Frontmatter path fields use leading `/` from bundle root (or true file-relative paths); Markdown body links use file-relative paths.
* [ ] Custom extension keys use `x-<producer>-<name>` and existing unknown keys are preserved.
* [ ] Optional: `README.md` symlink points to `index.md` if GitHub directory rendering is desired (expect validator `W120`).

---

## 4. Deep-Dive Reference

* [Open Knowledge Format (OKF v0.3) Specification & Implementation Guide](./references/okf_specification.md)
* Upstream specification & reference tools: [open-knowledge-format/open-knowledge-format](https://github.com/open-knowledge-format/open-knowledge-format)
