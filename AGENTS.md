# Repository Guidelines

## Project Structure & Module Organization

Use a simple, predictable layout:

```
src/            # application/library code
tests/          # automated tests mirroring src structure
scripts/        # helper scripts (setup, dev, ci)
assets/         # static files (images, fixtures)
docs/           # architecture notes and ADRs
```

Keep modules small and focused. Place shared utilities in `src/common/`. Name entry points `main.*` (CLIs) or `app.*` (services).

## Build, Test, and Development Commands

- `make setup` — install toolchains and dependencies.
- `make dev` — run the app locally with autoreload.
- `make test` — run the test suite with coverage.
- `make lint` — run linters/formatters and fail on issues.
- `make build` — produce a release artifact.

If `make` is unavailable, provide equivalent `scripts/*.sh` wrappers (e.g., `./scripts/test.sh`).

## Coding Style & Naming Conventions

- Indentation: 4 spaces for code; 2 for YAML/JSON.
- Filenames: `snake_case` for source/tests; `kebab-case` for scripts.
- Functions/vars: `snake_case`; Classes/Types: `PascalCase`.
- Keep functions <50 lines; prefer pure helpers in `src/common/`.
- Use formatters/linters (e.g., Black/Ruff, Prettier/ESLint, gofmt) via `make lint`.

## Testing Guidelines

- Mirror `src/` in `tests/`; name files `test_<module>.*` or `<module>.test.*`.
- Aim for meaningful coverage on core logic; add regression tests for bugs.
- Use fixtures for I/O; avoid network or global state. Run locally with `make test`.

## Commit & Pull Request Guidelines

- Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`. Example: `feat(api): add pagination to /items`.
- One logical change per PR; include description, linked issue, and before/after notes or screenshots if UI.
- Ensure green `make lint` and `make test` before requesting review.

## Security & Configuration Tips

- Keep secrets in environment variables; never commit `.env`. Provide `./.env.example`.
- Add generated files and local tooling to `.gitignore`.
- Prefer dependency pinning and lockfiles; update via dedicated PRs.

