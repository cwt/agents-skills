---
name: okf-best-practices
description: Google Open Knowledge Format (OKF v0.2) bundle rules, file structure guidelines, metadata fields, trust signals, interlinking standards, and consumer robustness constraints.
---

# Open Knowledge Format (OKF v0.2) Best Practices & Rules

This skill enforces strict adherence to the Google OKF v0.2 specification for structured text-based organizational knowledge.

---

## 1. Trigger Conditions

You **MUST** load and follow this skill if the active task involves:

* Creating, editing, or reading Markdown files in an OKF Bundle (typically under a `docs/` folder, rules files, or files listed in `AGENTS.md`).
* Documenting lessons learned, development rules, priorities, or architectural mandates.
* Managing provenance, freshness, or verification status of agent-generated knowledge.
* Parsing directory structures meant to represent a semantic graph of organizational knowledge.

---

## 2. Core Specification Rules

### 2.1. File Structure (YAML Frontmatter + Markdown Body)

Every concept document MUST contain exactly two parts:

1. **YAML Frontmatter Block**: Enclosed by triple hyphens (`---`) at the absolute top of the file.
2. **Markdown Body**: Standard Markdown content following the frontmatter.

#### Required Metadata Fields

The frontmatter MUST contain:

* `type` (Mandatory, String): The structural archetype (e.g., `api_spec`, `runbook`, `database_schema`, `policy`, `lessons_learned`, `project_priority`, `architecture_guideline`, `attested_computation`).

#### Standard Metadata Fields (Recommended)

* `title` (String): A human-friendly title.
* `description` (String): A brief summary for fast semantic routing.
* `resource` (String): Link or ID to the production asset.
* `tags` (Array of Strings): Flat list of categories.
* `timestamp` (ISO-8601 UTC Datetime): Exact date/time of creation or last update.

#### OKF v0.2 Trust Signals (Opt-In Metadata)

OKF v0.2 standardizes metadata for provenance, trustworthiness, and lifecycle management:

| Signal | Field | Type | Example / Values | Purpose |
| --- | --- | --- | --- | --- |
| **Lifecycle** | `status` | String | `draft`, `stable`, `deprecated` | Version and lifecycle stage of the concept. |
| **Provenance** | `sources` | Array of Strings | `[src/auth.zig, bq://analytics.events]` | Lineage tracking: origin assets or documents. |
| **Trust Tier** | `verified` | String or Array | `unverified`, `machine-confirmed`, `human-reviewed` | Verification confidence level. |
| **Freshness** | `stale_after` | ISO-8601 UTC | `2026-12-31T00:00:00Z` | Absolute date after which concept requires re-check. |
| **Attestation** | `type: attested_computation` | Archetype | *(used in `type` field)* | Verifiable execution/query output concept. |

### 2.2. Reserved Filenames

Do **NOT** use the following filenames for standard concept documents:

* `index.md`: Reserved for directory lists and subdirectory maps to support progressive disclosure.
* `log.md`: Reserved for a running, chronological log of bundle modifications.

### 2.3. GitHub Rendering (Symbolic Links)

* **Rule**: For every directory containing an `index.md` file (such as the bundle root `docs/` or subdirectories like `docs/lessons/`), you MUST create a symbolic link named `README.md` pointing to `index.md`. This allows GitHub to automatically render the index content when browsing directories.
  * *Example Command*: `ln -s index.md README.md` (always use relative paths for symlinks).

### 2.4. Markdown Layout Constraints

* **Rule**: Favor structured elements (headings `##`, bulleted lists, tables) over long unformatted prose blocks. This provides clear anchor points for parsing.

### 2.5. Concept Interlinking (The Graph Layer)

To link documents within the OKF bundle, **ALWAYS use relative paths** based on the location of the file that contains the link. **Never** use paths starting with `/`.

* **Why avoid `/`**: GitHub (and most Markdown renderers) resolve a link beginning with `/` against the **repository root**, not the bundle root. A link like `[Architecture](/architecture.md)` written in `docs/index.md` resolves to `repo/architecture.md`, which does not exist — the real file is `repo/docs/architecture.md`. It renders as a broken link.
* **Relative Links** (relative to the current file):
  * *Same directory*: `[Local Rule](./local-rule.md)` or `[Local Rule](local-rule.md)`.
  * *Subdirectory*: `[Mandates](./mandates/mandates.md)`.
  * *Parent directory*: `[Home](../index.md)`.

### 2.6. Fault-Tolerance Constraints (For AI Consumers)

* **Tolerate Extra Keys**: Do not crash on unknown YAML frontmatter keys or customized body sections.
* **Graceful Degradation**: Do not reject a bundle if optional fields, trust signals, or an `index.md` are missing.
* **Skip Orphans**: Log and skip broken links without terminating execution.

---

## 3. Production Checklist for OKF Files

* [ ] Starts with `---` as the first line of the file?
* [ ] Contains a `type` metadata field?
* [ ] Contains other key attributes (`title`, `description`, `timestamp`)?
* [ ] For production/agent docs, includes v0.2 trust signals (`status`, `sources`, `verified`, `stale_after`) where applicable?
* [ ] Closes frontmatter with `---`?
* [ ] Standard Markdown body immediately follows?
* [ ] Headers, bullet points, and tables are used instead of plain prose blocks?
* [ ] Links use relative paths (relative to the current file), never absolute `/` paths?
* [ ] Directory containing `index.md` has a `README.md` symlink pointing to it?

---

## 4. Deep-Dive Reference

For the complete specification details, BQ schema examples, and background metadata structure:

* [Google OKF v0.2 Specification & Implementation Guide](./references/okf_specification.md)
