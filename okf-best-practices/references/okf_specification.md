# Open Knowledge Format (OKF) v0.2 — Specification & Implementation Guide

## 1. Overview & Purpose

The Open Knowledge Format (OKF) is an open, vendor-neutral specification published by Google Cloud. It formalizes the "LLM Wiki pattern" into a portable standard. Its purpose is to represent organizational knowledge as a structured directory of plain text Markdown files with YAML frontmatter.

Released in July 2026, **OKF v0.2** introduces standardized **Trust Signals** (provenance, verification tiers, freshness, and lifecycle management), allowing autonomous AI agents to programmatically evaluate the authority and currency of institutional knowledge before acting on it.

This layout ensures that curated context is machine-queryable by AI agents while remaining 100% human-readable and version-controllable via Git or Mercurial.

---

## 2. Core Architecture & Bundle Rules

An **OKF Bundle** is a standard directory of files.

* **Encoding:** All files MUST be UTF-8 encoded plain text.
* **Concepts:** Each individual file within the bundle represents a single atomic "concept" (e.g., a table, API endpoint, component description, system architecture piece, runbook, policy, or attested computation).
* **Identity:** The unique identifier for any concept is its relative file path within the bundle root.

### Reserved Filenames

Only two filenames have special meaning and are reserved. They **MUST NOT** be used for normal concept documents:

1. `index.md` — Serves as a directory listing/map to allow progressive disclosure. It lets AI agents preview what data exists in a subdirectory before parsing every single file into context.
2. `log.md` — A running, chronological update log tracking modifications to the bundle.

---

## 3. File Structure Specification

Every concept Markdown file must consist of exactly two parts: a **YAML Frontmatter Block** followed by a standard **Markdown Body**.

### A. The Frontmatter Layer (Metadata)

The frontmatter must be enclosed by triple hyphens (`---`).

| Field Name | Status | Type | Description |
| --- | --- | --- | --- |
| `type` | **MANDATORY** | String | Defines the structural archetype (e.g., `api_spec`, `runbook`, `database_schema`, `policy`, `lessons_learned`, `attested_computation`). |
| `title` | Optional | String | A human-friendly title for the concept. |
| `description` | Optional | String | A high-level summary of the file's contents for fast routing. |
| `resource` | Optional | String | A reference link or ID to the production asset this file represents. |
| `status` | Optional (v0.2) | String | Lifecycle state: `draft`, `stable`, or `deprecated`. |
| `sources` | Optional (v0.2) | Array | Lineage/provenance list tracking source files, assets, or query origins. |
| `verified` | Optional (v0.2) | String or Array | Trust tier (`unverified`, `machine-confirmed`, `human-reviewed`). |
| `stale_after` | Optional (v0.2) | ISO-8601 UTC | Freshness deadline after which the concept should be re-validated. |
| `tags` | Optional | Array | A flat list of category tags for filtering and indexing. |
| `timestamp` | Optional | ISO-8601 UTC | The exact UTC datetime the document was created or last updated. |

> **Note:** Producers can add arbitrary custom keys to the frontmatter as needed. AI consumers must tolerate and gracefully ignore unknown keys without erroring out.

### B. The Content Layer (Body)

The remainder of the file is standard Markdown.

* **Structural Preference:** Producers SHOULD heavily favor structured Markdown components—such as headings (`##`), bulleted lists, and tables—over long blocks of free-form, unformatted prose. This provides clear anchor points for semantic parsing.

---

## 4. Graph Layer (Interlinking Conventions)

To transform a flat directory into a multi-dimensional semantic graph, concepts link to one another using native Markdown links.

* **Relative Links (Required):** Always use standard relative file paths based on the location of the containing file.
  * *Same directory:* `[Deployment Steps](./deploy-guide.md)` or `[Deployment Steps](deploy-guide.md)`
  * *Parent directory:* `[Back to Index](../index.md)`
* **Why Avoid Repo-Root `/` Links:** Paths starting with `/` resolve to the repository root on GitHub and static doc renderers rather than the bundle root, producing broken links when bundles live in subdirectories like `docs/`.

---

## 5. Attested Computation (`type: attested_computation`)

Introduced in OKF v0.2, the `attested_computation` archetype documents deterministically executed queries, data pipelines, or code verification runs.

* Frontmatter SHOULD include `sources` (input data/scripts) and `verified` (execution signature or runner).
* Body contains the executed code/query and the verified output snapshot.

---

## 6. System Robustness Constraints (For Consumers)

When reading or maintaining an OKF bundle, AI agents MUST follow these strict fault-tolerance constraints:

1. **Tolerate the Unknown:** An agent must never fail or crash if it encounters unknown `type` values, extra metadata keys, or customized body sections.
2. **Missing Optional Data:** An agent must not reject a bundle or file because optional fields (like `tags`, `verified`, or `status`) or an `index.md` are missing.
3. **Handle Broken Connections:** The agent must gracefully log and skip broken or orphaned cross-links without terminating operations.

---

## 7. Template Reference Example (OKF v0.2)

````markdown
---
type: database_schema
title: User Analytics Table
description: Relational table schema tracking user clickstream behavior.
resource: bq://my-project.analytics.user_clicks
status: stable
sources:
  - bq://my-project.analytics.raw_events
  - src/analytics/collector.zig
verified: human-reviewed
stale_after: 2026-12-31T00:00:00Z
tags: [data-warehouse, marketing, tracking]
timestamp: 2026-07-07T15:26:00Z
---

# User Analytics Table

## Schema Summary

This table collects real-time event logs from our web app client.

| Column | Type | Description |
| --- | --- | --- |
| `event_id` | STRING | Cryptographic unique string for deduplication. |
| `user_id` | INT64 | Matches the core identifier in the [User Profile Specs](../auth/profiles.md). |
| `click_timestamp` | TIMESTAMP | Recorded in UTC. |

## Query Example

```sql
SELECT user_id, COUNT(*) 
FROM `my-project.analytics.user_clicks` 
GROUP BY 1;
```
````
