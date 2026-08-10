# Agent Skills Repository

A curated collection of specialized skills for AI coding agents (e.g., Google Antigravity / AGY, Claude, Cursor, and LLM assistants).

Each skill provides clear guidelines, triggers, rules, and code patterns designed to keep AI assistants aligned with best practices, specific framework versions, and project conventions.

---

## 🛠 Available Skills

| Skill | Description | Key Topics |
| :--- | :--- | :--- |
| [**`okf-best-practices`**](./okf-best-practices/SKILL.md) | Google Open Knowledge Format (OKF v0.1) bundle rules and document structures. | YAML frontmatter schemas, interlinking standards, document types, consumer robustness constraints. |
| [**`zig-0160-development`**](./zig-0160-development/SKILL.md) | Comprehensive development guide for **Zig 0.16.0**. | Zig 0.16.0 `main(init)` entry points, `std.Io` / `std.process`, unmanaged containers, memory management, `build.zig`, C interop. |

---

## 📂 Repository Structure

```text
agents-skills/
├── okf-best-practices/
│   ├── SKILL.md                  # Main skill definition & prompt instructions for OKF v0.1
│   └── references/
│       └── okf_specification.md  # Official OKF v0.1 specification reference
├── zig-0160-development/
│   └── SKILL.md                  # Detailed rules, examples, and patterns for Zig 0.16.0
├── LICENSE                       # MIT License
└── README.md                     # Repository documentation
```

---

## 🚀 How to Use

### 1. Clone the Repository

Clone this repository into your preferred location:

```bash
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

## 📄 License

This repository is licensed under the [MIT License](./LICENSE). Copyright (c) 2026 Chaiwat Suttipongsakul.
