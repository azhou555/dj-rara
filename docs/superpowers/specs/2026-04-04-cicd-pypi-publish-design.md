# CI/CD: Automatic PyPI Publish on Git Tag

**Date:** 2026-04-04
**Status:** Approved

## Goal

Automatically publish `dj-rara` to PyPI whenever a version tag is pushed to GitHub, so that `pip install dj-rara` always reflects the latest committed changes.

## Trigger

Push of a tag matching `v*` (e.g., `v0.1.2`). Normal pushes to main do not trigger a publish.

## Workflow: `.github/workflows/publish.yml`

Two jobs:

### `build`
- Checks out the repo
- Sets up Python 3.11
- Installs `build`
- Runs `python -m build` to produce `dist/`
- Uploads `dist/` as a workflow artifact

### `publish`
- Downloads the `dist/` artifact from `build`
- Uses `pypa/gh-action-pypi-publish` with OIDC trusted publishing
- No API token stored anywhere — PyPI grants a short-lived token via OpenID Connect

**Permissions required:**
- `id-token: write` — for OIDC token exchange with PyPI
- `contents: read` — for repo checkout

## PyPI Trusted Publisher (one-time setup — already complete)

Configured on PyPI project settings → Publishing:
- Owner: `azhou555`
- Repo: `dj-rara`
- Workflow: `publish.yml`
- Environment: (none)

## Release Process

```bash
# 1. Bump version in pyproject.toml
# 2. Commit and tag
git add pyproject.toml && git commit -m "bump version to v0.1.2"
git tag v0.1.2
git push && git push --tags
```

GitHub Actions fires on the tag push, builds the package, and publishes to PyPI. No manual upload needed.

## Out of Scope

- Automated version bumping
- Test gates before publish (no test suite targeting the packaged artifact)
- GitHub Release note generation
