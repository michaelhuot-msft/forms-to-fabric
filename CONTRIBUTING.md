# Contributing to Forms to Fabric

Thank you for your interest in contributing! This guide explains how to get involved.

## How to Contribute

1. **Fork** the repository.
2. **Create a branch** from `main` for your change (`git checkout -b feat/my-feature`).
3. **Make your changes** and commit them following the commit message format below.
4. **Open a Pull Request** against `main` with a clear description of what you changed and why.

## Code Style

- **Language:** Python 3.11+
- **Type hints:** Use type annotations on all function signatures.
- **Docstrings:** Include a docstring for every public module, class, and function.
- **Formatting:** Follow [PEP 8](https://peps.python.org/pep-0008/) conventions.

## Getting Started

After cloning, install the pre-commit hooks:

```bash
sh scripts/install-hooks.sh
```

This validates Bicep templates automatically before each commit.

## Running Tests

```bash
python -m pytest tests/ -v
```

All tests must pass before a PR will be reviewed.

## CI Checks

All PRs must pass these automated checks:

1. **Python tests** — `python -m pytest tests/ -v`
2. **Ruff linter** — `ruff check src/functions/ tests/`
3. **Ruff formatter** — `ruff format --check src/functions/ tests/`
4. **Bicep validation** — `az bicep build --file infra/main.bicep`
5. **JSON schema validation** — `config/form-registry.json` validated against `config/form-registry.schema.json`
6. **Credential scanning** — Gitleaks checks for leaked secrets in all commits

> **Note:** PowerShell scripts in `scripts/` should be tested manually before PR — there are no automated PS tests in CI.

## Commit Message Format

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

<optional body>
```

**Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`

Examples:

```
feat(ingest): add support for multi-select questions
fix(deid): handle missing field gracefully
docs(admin): clarify key rotation steps
```
