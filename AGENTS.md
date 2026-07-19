# AGENTS.md

## Mission

Maintain the YunoHost package for the official Gitea server. The package tracks the newest stable upstream release that passes reproducibility and package checks. “Latest” is resolved by automation; install and upgrade always use versioned URLs and SHA-256 values committed in `manifest.toml`.

## Read before changing

1. `manifest.toml`, `tests.toml`, `scripts/` and `conf/`.
2. Gitea release notes: https://blog.gitea.com/tags/release/
3. Gitea administration documentation: https://docs.gitea.com/
4. Upstream source: https://github.com/go-gitea/gitea
5. YunoHost packaging documentation: https://doc.yunohost.org/packaging_apps
6. Sibling packages:
   - https://github.com/faleious-ai/gitea-runner_ynh
   - https://github.com/faleious-ai/gitea-mcp_ynh

## Update policy

- Accept stable releases only. Reject draft, prerelease, RC, beta, alpha and nightly builds.
- Never use a mutable `latest` download during install or upgrade.
- Keep an immutable URL and SHA-256 per supported architecture.
- Starting with Gitea 1.27, verify the upstream Sigstore bundle before publishing new hashes.
- Patch and minor updates may be automated after validation. Major updates require review of breaking changes and database migrations.
- Keep the Gitea/Runner compatibility note current.

## Required validation

```bash
python3 tools/validate_package.py
python3 -m py_compile tools/*.py
find scripts -maxdepth 1 -type f ! -name '*.sql' -print0 |
  sort -z |
  while IFS= read -r -d '' script; do
    echo "Checking ${script}"
    bash -n "$script"
  done
```

The GitHub workflows also run the current official `YunoHost/package_linter`
procedure: clone the linter, create a virtual environment, install its
`requirements.txt` and invoke `package_linter.py` against this package.

A release is validated only after fresh install, upgrade from the previous packaged release, backup/restore, removal, HTTP/API checks and service health pass. Do not claim CI success without the exact workflow run and commit SHA.

## Automation

- `tools/update_upstream.py` discovers the newest stable release, validates release metadata and assets, computes SHA-256 and updates `manifest.toml`.
- `.github/workflows/upstream-update.yml` runs the updater on schedule and by manual dispatch.
- `.github/workflows/package-ci.yml` validates pushes and pull requests.
- Generated README files must not be edited manually.

## Safety rules

- Preserve database contents, repositories, LFS, SSH keys, hooks, packages and `app.ini` across upgrade and restore.
- Never place credentials or tokens in Git, tests, logs or workflow output.
- Preserve YunoHost permissions, LDAP integration, multi-instance behavior and proxy routes unless a documented migration requires a change.
- Do not silently remove an architecture.
- When a release fails validation, keep the prior validated version and record the failure with evidence.
