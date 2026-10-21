#!/usr/bin/env python3
"""Validate Agent Skills in this repository against the agentskills.io spec.

Checks each skill directory for a valid SKILL.md with required frontmatter
(name, description), name/dir match, name format, description length, and a
reasonable SKILL.md body length.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESC = 1024
MAX_LINES = 500
errors = []
warnings = []


def parse_frontmatter(text):
    if not text.startswith("---"):
        return None, "missing opening '---'"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, "missing closing '---'"
    body = parts[1]
    # Minimal YAML-ish parse: key: value, and key:\n  - / nested simple maps
    fm = {}
    for line in body.splitlines():
        if not line.strip():
            continue
        if line.startswith(" ") or line.startswith("\t"):
            # nested/continuation line; skip for top-level field detection
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            fm[key] = val if val else None
    return fm, None


def main():
    skill_dirs = []
    for entry in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, entry)
        if not os.path.isdir(path) or entry.startswith(".") or entry in ("scripts", "templates", "docs"):
            continue
        if os.path.exists(os.path.join(path, "SKILL.md")):
            skill_dirs.append(entry)

    if not skill_dirs:
        print("No skill directories found.")
        sys.exit(0)

    for d in skill_dirs:
        skill_path = os.path.join(ROOT, d)
        skill_md = os.path.join(skill_path, "SKILL.md")
        with open(skill_md, encoding="utf-8") as f:
            text = f.read()
        fm, err = parse_frontmatter(text)
        prefix = f"[{d}]"
        if err:
            errors.append(f"{prefix} SKILL.md: {err}")
            continue
        # required fields
        if "name" not in fm or not fm.get("name"):
            errors.append(f"{prefix} missing required field 'name'")
        else:
            name = fm["name"].strip().strip('"').strip("'")
            if name != d:
                errors.append(f"{prefix} name '{name}' does not match directory '{d}'")
            if len(name) < 1 or len(name) > MAX_NAME:
                errors.append(f"{prefix} name length must be 1-{MAX_NAME}")
            if not NAME_RE.match(name):
                errors.append(f"{prefix} name must be lowercase letters, numbers, hyphens")
        if "description" not in fm or not fm.get("description"):
            errors.append(f"{prefix} missing required field 'description'")
        else:
            desc = fm["description"].strip().strip('"').strip("'")
            if len(desc) < 1 or len(desc) > MAX_DESC:
                errors.append(f"{prefix} description length must be 1-{MAX_DESC} (got {len(desc)})")

        line_count = text.count("\n") + 1
        if line_count > MAX_LINES:
            warnings.append(f"{prefix} SKILL.md is {line_count} lines (recommended < {MAX_LINES})")

        # check referenced files exist
        for m in re.finditer(r"\]\(([^)]+)\)", text):
            link = m.group(1)
            if link.startswith("http") or link.startswith("#") or link.startswith("mailto:"):
                continue
            link = link.split("#")[0]
            if not link:
                continue
            # Skip illustrative/placeholder links used in documentation examples.
            base = os.path.basename(link)
            if base in {"local-rule.md", "mandates.md", "architecture.md", "profiles.md",
                        "deploy-guide.md", "index.md"}:
                continue
            if "local-rule" in link or "mandates/mandates" in link:
                continue
            target = os.path.normpath(os.path.join(skill_path, link))
            if not os.path.exists(target):
                warnings.append(f"{prefix} broken relative link: {link}")

    for w in warnings:
        print("WARN:", w)
    for e in errors:
        print("ERROR:", e)
    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s).")
        sys.exit(1)
    print(f"OK: {len(skill_dirs)} skill(s) validated. {len(warnings)} warning(s).")


if __name__ == "__main__":
    main()
