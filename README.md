# Agent Skills Repository

A curated collection of specialized skills for AI coding agents (e.g., Google Antigravity / AGY, Claude, Cursor, OpenAI Codex, Gemini CLI, and LLM assistants).

Each skill follows the open [Agent Skills standard](https://agentskills.io/specification): a `SKILL.md` file with YAML frontmatter plus optional `scripts/`, `references/`, and `assets/` directories. Skills provide clear guidelines, triggers, rules, and code patterns designed to keep AI assistants aligned with best practices, specific framework versions, and project conventions.

---

## 🛠 Available Skills

| Skill | Description | Key Topics |
| :--- | :--- | :--- |
| [**`okf-best-practices`**](./okf-best-practices/SKILL.md) | Open Knowledge Format (OKF v0.3) bundle rules and document structures. | YAML frontmatter schemas, provenance, trust tiers, freshness, lifecycle (`superseded_by`), Attested Computations, path/link resolution, consumer conformance. |
| [**`zig-0160-development`**](./zig-0160-development/SKILL.md) | Comprehensive development guide for **Zig 0.16.0** (verified to also build on **0.17.0**). | Zig 0.16.0 `main(init)` entry points, `std.Io` / `std.process`, unmanaged containers, memory management, `build.zig`, C interop, code review & bug hunting. |

---

## 📂 Repository Structure

```text
agents-skills/
├── okf-best-practices/
│   ├── SKILL.md                  # Main skill definition & prompt instructions for OKF v0.3
│   └── references/
│       └── okf_specification.md  # Official OKF v0.3 specification reference
├── zig-0160-development/
│   ├── SKILL.md                  # Concise core rules (under 500 lines); details in references/
│   └── references/
│       ├── language-basics.md    # Values, pointers, control flow, structs, errors, comptime, tests
│       ├── containers-and-io.md  # ArrayList, hash maps, I/O, files, net, concurrency
│       ├── build-and-templates.md # Program templates, build.zig, zon, deps, cross-compile
│       ├── migration-errors-builtins.md # Migration table, compiler errors, builtins, checklist
│       ├── dual-016-017.md       # Dual-build guide (0.16.0 + 0.17.0)
│       └── review-catalog.md     # Bug-hunting catalog for Zig code review
├── scripts/
│   └── validate_skills.py        # Validates SKILL.md frontmatter against the spec
├── templates/
│   └── skill-template/           # Starter template for new skills
├── .github/workflows/
│   └── validate.yml              # CI validation
├── CONTRIBUTING.md
├── LICENSE                       # MIT License
└── README.md                     # Repository documentation
```

---

## ✅ Validation

All skills are validated against the Agent Skills specification by CI:

```bash
python3 scripts/validate_skills.py
```

The validator checks required frontmatter (`name`, `description`), name/directory match, name format, description length, SKILL.md length (recommended < 500 lines), and relative links.

---

## 🚀 How to Use

### 1. Clone the Repository

Clone this repository into your preferred location (Mercurial or Git via hg-git):

```bash
hg clone https://github.com/cwt/agents-skills.git
# or
git clone https://github.com/cwt/agents-skills.git
```

### 2. Symlink Desired Skills

Navigate to your agent's `skills/` directory (global or workspace-level) and create symbolic links (`ln -s`) pointing to the desired skills:

#### Global Setup (e.g. Antigravity / AGY)

```bash
# Navigate to the global skills directory
mkdir -p ~/.gemini/config/skills && cd ~/.gemini/config/skills

# Symlink desired skills from the cloned repo
ln -s /path/to/agents-skills/okf-best-practices .
ln -s /path/to/agents-skills/zig-0160-development .
```

#### Workspace Setup

```bash
# Navigate to the project's agent skills directory
mkdir -p .agents/skills && cd .agents/skills

# Symlink desired skills from the cloned repo
ln -s /path/to/agents-skills/okf-best-practices .
ln -s /path/to/agents-skills/zig-0160-development .
```

---

## 📝 Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for how to add or update a skill, including the skill template and validation steps.

---

## 📄 License

This repository is licensed under the [MIT License](./LICENSE). Copyright (c) 2026 Chaiwat Suttipongsakul.
