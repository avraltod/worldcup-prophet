# Project rules

- This repo is PUBLIC and pre-registered: never rewrite pushed history.
- Process documents (brainstorming specs, plans, runbooks, drafts, scratch
  scripts) belong under `internal/` (gitignored) — never commit them.
  Superpowers specs go to `internal/docs/superpowers/specs/`, plans to
  `internal/docs/superpowers/plans/`.
- The public tree is a replication package: code lands in `scripts/` only if
  the live workflows, tests, or paper build need it.
