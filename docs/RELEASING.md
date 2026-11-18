# Releasing

Releases are published to PyPI by `.github/workflows/release.yml` when a version tag is pushed.

## One-time setup

1. Create the `semarc` project on PyPI as a **pending trusted publisher**
   (PyPI → Account settings → Publishing → Add a new pending publisher):
   - PyPI project name: `semarc`
   - Owner: `byterings`, repository: `semarc`
   - Workflow name: `release.yml`
   - Environment name: `pypi`
2. In GitHub → Settings → Environments, create an environment named `pypi`. Restricting it to
   tags `v*` and requiring a reviewer is recommended.

No API token is stored in the repository: PyPI trusts the workflow through OpenID Connect.

## Each release

1. Update `SEMARC_VERSION` in `semarc/compiler/version.py`.
2. Move the `Unreleased` entries in `CHANGELOG.md` under the new version with today's date.
3. Run the checks:

   ```bash
   python3 scripts/validate_release.py
   python3 scripts/project_tests.py examples/*.sem tests/fixtures/*.sem
   python3 scripts/e2e_runtime.py examples/*.sem tests/fixtures/*.sem
   ```

4. Commit, then tag and push:

   ```bash
   git tag v0.15.0
   git push origin v0.15.0
   ```

The workflow checks that the tag matches `SEMARC_VERSION`, runs release validation, builds the
sdist and wheel, smoke-tests the wheel (`semarc init` and `semarc build`), publishes to PyPI
and creates a GitHub release with the distributions attached.
