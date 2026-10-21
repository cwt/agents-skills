# Contributing

Thanks for contributing to the Agent Skills collection.

## Adding a new skill

1. Copy `templates/skill-template/` to a new directory named after your skill.
   The directory name must match the `name` field in `SKILL.md` (lowercase letters,
   numbers, and hyphens only, no consecutive hyphens).
2. Fill in the frontmatter:
   - `name` (required) — must match the directory name.
   - `description` (required, 1-1024 chars) — describe what the skill does and when
     to use it; include trigger keywords.
   - `license`, `compatibility`, `metadata` (optional).
3. Keep `SKILL.md` under 500 lines; move detailed reference material into
   `references/`, `scripts/`, or `assets/` and link to it with relative paths.
4. Run the validator locally:

   ```sh
   python3 scripts/validate_skills.py
   ```

## Style

- Prefer concise, actionable instructions over long prose.
- Use relative paths (never leading `/`) for links inside the bundle.
- Follow the [Agent Skills specification](https://agentskills.io/specification).

## Pull requests

Open a PR against `main`. CI runs `scripts/validate_skills.py` on every PR.
