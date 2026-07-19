# Validation status

Last architecture update: 2026-07-19.

## Final package state

- Package-code HEAD: `859f7489c9cb3c266338450001ab3483e8c2e3b9`.
- Final package version: `1.27.0~ynh1`.
- The updater discovered the stable upstream release, downloaded official versioned assets, verified SHA-256 files and verified the required Sigstore bundles. A second run reported `already-current 1.27.0` and produced no manifest diff.
- The package uses `actions/checkout@v7.0.0`, `actions/setup-python@v6.3.0` and `sigstore/cosign-installer@v4.1.2` in both workflows.

## Root cause and corrections

- The original shell loop passed `scripts/login_source.sql` to `bash -n`; its SQL `NOW()` syntax produced exit code 2. The workflows now enumerate only non-SQL files, print each path, and preserve every intermediate failure.
- The updater's field-replacement regex could consume blank lines and make its output unstable. It now matches horizontal whitespace only, preserving deterministic revisable diffs.
- The multiline upgrade message was rewritten as an explicit `printf` command without changing its meaning.
- The official YunoHost package linter is executed in CI from a clean checkout and fails on real linter errors.

## Commands and evidence

Local Windows checks used the bundled Python runtime and Git Bash because `python3`, Docker and a WSL distribution were unavailable:

```text
<bundled-python> -m py_compile tools/*.py
find scripts -maxdepth 1 -type f ! -name '*.sql' -print0 | sort -z | while IFS= read -r -d '' script; do echo "Checking ${script}"; bash -n "$script"; done
<bundled-python> tools/update_upstream.py
<bundled-python> tools/update_upstream.py   # idempotence: already-current 1.27.0
```

The local checkout's CRLF conversion caused the standalone validator's line-ending warning; the exact validator and package-linter commands passed in the remote Linux workflow. The updater's four downloaded Gitea assets returned `Verified OK` from Cosign.

Validation runs for the package-code HEAD:

- Package validation: [run 29695144595](https://github.com/faleious-ai/gitea_ynh/actions/runs/29695144595).
- Update stable upstream release: [run 29695145421](https://github.com/faleious-ai/gitea_ynh/actions/runs/29695145421).

Both runs were green. The package linter reported no error or critical failure; it emitted only its upstream warning about a known small bug. No Node.js 20 warning was present in the final logs.

## Required before production use

On disposable YunoHost 12 infrastructure, still demonstrate fresh install, upgrade, login/API, repository push/clone, database/repository/SSH/LFS backup and restore, removal, URL change and reboot health.

## Current classification

`AUTOMATION_AND_PACKAGE_LINTER_VERIFIED_UPSTREAM_PIN_VALIDATED_LIFECYCLE_UNVERIFIED`

The lifecycle is intentionally not classified as verified because no YunoHost host was available in this workspace.

Read `AGENTS.md` before continuing.
