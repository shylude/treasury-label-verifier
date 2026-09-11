# CLAUDE.md — Security+ Prep Workspace

Guidance for AI assistants working inside `security-plus-prep/`. This folder is
a personal study workspace for the CompTIA Security+ (SY0-701) exam. It is
**not** part of the Treasury label-verifier application that surrounds it.

## Scope

- Only touch files under `security-plus-prep/`. Never modify the app code
  (`app/`, `tests/`, `tools/`, `Dockerfile`, etc.) when working on prep tasks.
- This is study material: Markdown notes, lab write-ups, and tracking tables.
  There is no build step, no dependencies, and no CI for this folder.

## Layout

- `README.md` — overview, exam facts, domain weight table.
- `study-plan.md` — schedule, weak-area log, exam-week checklist.
- `01-…` through `05-…` — one folder per SY0-701 domain.
- `labs/` — hands-on exercise guide and per-lab write-ups.
- `practice-exams/` — score log and missed-question review.

## Conventions

- Each domain `README.md` follows the same template: exam objectives, key
  concepts, key terms & acronyms table, notes, and a "Questions I got wrong"
  section. Preserve that structure when editing.
- Keep acronyms in the per-domain tables, expanded on first use.
- Do not invent exam facts. When adding content, flag anything not verified
  against CompTIA's official SY0-701 objectives so the user can confirm it.
- Prefer additive edits: fill in template sections rather than restructuring.

## When asked to study or quiz

- Draw questions and explanations from the domain notes already here.
- Record any weak topics in `study-plan.md`'s weak-area log and link the
  relevant practice-exam entry.
