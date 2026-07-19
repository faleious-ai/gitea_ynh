# Validation status

Last architecture update: 2026-07-19.

## Current package state

- Package pin: `1.26.4~ynh1`.
- Latest stable upstream release observed: `1.27.0`.
- Stable release discovery, immutable source pinning, upstream SHA-256 verification and Sigstore verification for Gitea 1.27+ are implemented.
- Updater hardening was published at commit `9e6b721966aabf4396a5c9e4b71d9601a0f84c69`.
- The updater refuses automated downgrades, validates all supported architectures and stops for manual review if upstream republishes an asset under an already packaged version.
- Static package validation and scheduled/manual/push-triggered GitHub Actions workflows are present.
- No workflow-generated commit updating the manifest to Gitea `1.27.0~ynh1` has been observed. Do not describe the package as updated to 1.27 until that commit and its validation evidence exist.

## Required before production use

1. Confirm GitHub Actions is enabled for this fork and has permission to write repository contents.
2. Run `Update stable upstream release` manually if the push-triggered run did not execute.
3. Resolve any download, checksum or Sigstore failure without weakening verification.
4. Confirm the generated manifest contains only official versioned `dl.gitea.com` URLs and matching SHA-256 values for every declared architecture.
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

`AUTOMATION_HARDENED_EXECUTION_UNOBSERVED_LIFECYCLE_UNVERIFIED`

Read `AGENTS.md` before continuing.
