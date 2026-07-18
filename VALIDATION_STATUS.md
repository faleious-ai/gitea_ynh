# Validation status

Last architecture update: 2026-07-18.

## Current package state

- Package pin: `1.26.4~ynh1`.
- Stable release discovery, immutable source pinning, upstream SHA-256 verification and Sigstore verification for Gitea 1.27+ are implemented.
- Static package validation and scheduled/manual GitHub Actions workflows are present.
- No successful automated commit updating the manifest to Gitea 1.27 has been observed yet.

## Required before production use

1. Confirm GitHub Actions is enabled for this fork.
2. Run `Update stable upstream release` manually.
3. Resolve any download, checksum or Sigstore failure without weakening verification.
4. Confirm the generated manifest contains only official versioned URLs and matching SHA-256 values.
5. On disposable YunoHost 12 infrastructure, demonstrate:
   - fresh install;
   - upgrade from `1.26.4~ynh1`;
   - login and API response;
   - repository creation plus Git push and clone;
   - backup/restore preserving database, repositories, SSH keys, LFS and configuration;
   - removal;
   - service health after reboot.
6. Record exact commit, workflow run and evidence.

## Current classification

`AUTOMATION_PUBLISHED_LIFECYCLE_UNVERIFIED`

Read `AGENTS.md` before continuing.