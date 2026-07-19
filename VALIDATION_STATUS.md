# Validation status

Last architecture update: 2026-07-19.

## Final package state

- Package-code HEAD: `9a2c9fcbe1861ecf876b4cdf06b92fa7757999b0`.
- Final package version: `1.27.0~ynh2`.
- Gitea remains pinned to stable upstream `1.27.0`; all four architecture assets retain official versioned URLs, SHA-256 values and Sigstore verification.
- The updater preserves the current `~ynhN` package revision and remains idempotent when the upstream version is already current.

## Root cause and corrections

- Gitea 1.27 warned because the package template emitted `ALLOWED_HOST_LIST` under the deprecated `[webhook]` section. The key is now emitted under `[security]`, matching the upstream configuration contract.
- Install, config-panel apply and upgrade use `ynh_config_add`, which rewrites the managed `app.ini` template and removes the legacy section on existing installations. The local validator now rejects a legacy `[webhook].ALLOWED_HOST_LIST` and requires the `[security]` location.
- The updater previously reset maintenance revisions to `~ynh1`; it now preserves the existing package revision, allowing this compatibility fix to remain `~ynh2`.

## Commands and evidence

Local Windows checks used the bundled Python runtime and Git Bash because `python3`, Docker and a WSL distribution were unavailable:

```text
<bundled-python> tools/validate_package.py
<bundled-python> -m compileall -q tools
for script in scripts/*; do ...; bash -n $script; done
```

Compilation and shell parsing passed locally. The standalone validator reported only the checkout's CRLF conversion; the exact validator, linter, source-hash and Sigstore commands passed in the remote Linux workflow. The full local Gitea updater could not complete because the Windows environment blocked the Cosign/network verification; the remote updater completed successfully.

Validation runs for the package-code HEAD:

- Package validation: [run 29697551505](https://github.com/faleious-ai/gitea_ynh/actions/runs/29697551505).
- Update stable upstream release: [run 29697551535](https://github.com/faleious-ai/gitea_ynh/actions/runs/29697551535).

Both runs were green, including the official YunoHost package linter. No Node.js 20 warning was present.

## Required before production use

On disposable YunoHost 12 infrastructure, still demonstrate fresh install, upgrade from `1.27.0~ynh1`, login/API, repository push/clone, database/repository/SSH/LFS backup and restore, removal, URL change and reboot health.

## Current classification

`AUTOMATION_AND_PACKAGE_LINTER_VERIFIED_UPSTREAM_PIN_VALIDATED_LIFECYCLE_UNVERIFIED`

The lifecycle is intentionally not classified as verified because no YunoHost host was available in this workspace.

Read `AGENTS.md` before continuing.
