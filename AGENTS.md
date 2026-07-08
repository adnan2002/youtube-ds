# Repository Guidelines

## Project Structure & Module Organization
This repository is currently empty except for Git metadata. When code is added, keep the top level shallow and predictable:
- `src/` for application code
- `tests/` for automated tests
- `docs/` for design notes or usage docs
- `assets/` for static files, if needed

If you introduce a framework, mirror its standard structure and update this file.

## Build, Test, and Development Commands
No build or test commands exist yet. Add the project’s canonical commands here when tooling is introduced, for example:
- `npm test` or `pytest` for test runs
- `npm run build` or `make build` for release builds
- `npm run dev` or `make dev` for local development

Prefer a small set of documented commands in `README.md` and keep them stable.

## Coding Style & Naming Conventions
No language-specific style guide is defined yet. Until then:
- Use the formatter and linter standard for the chosen stack.
- Prefer clear, descriptive names for files, functions, and modules.
- Use consistent casing that matches the language convention, such as `snake_case` for Python and `camelCase` for JavaScript functions.

If you add tooling such as Prettier, ESLint, Black, or Ruff, commit the config files with the code.

## Testing Guidelines
No test framework is configured yet. When tests are added:
- Place unit tests under `tests/` or a framework-specific test directory.
- Name tests after the behavior they verify, such as `test_login.py` or `auth.spec.ts`.
- Keep tests deterministic and focused on one behavior per case.

## Commit & Pull Request Guidelines
There is no existing commit history to infer a convention from. Use short, imperative commit messages, for example: `Add upload validation`.

Pull requests should include:
- A clear summary of the change
- Any setup or migration notes
- Screenshots or logs when behavior changes are visible
- Links to related issues, if applicable

## Agent-Specific Instructions
Before editing files, check whether `AGENTS.md` already exists and do not overwrite it. Keep changes minimal and aligned with the current repository state.
