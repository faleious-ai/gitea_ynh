# Validation status

Last update: 2026-07-27.

## Released package state

- Package-code commit:
  `dbf500011fe742265dfef3aac663a4f9ee709655`.
- Package version: `1.27.0~ynh3`.
- Stable upstream: `1.27.0`, with official versioned assets, committed
  SHA-256 values and Sigstore verification for all four architectures.
- Package validation:
  [run 30141243368](https://github.com/faleious-ai/gitea_ynh/actions/runs/30141243368).
- Stable upstream reconciliation:
  [run 30141243392](https://github.com/faleious-ai/gitea_ynh/actions/runs/30141243392).

Both exact-commit workflows succeeded, including the official YunoHost package
linter. The published Git blob for `scripts/upgrade` contains 0 CRLF sequences;
all 126 line endings are LF.

## OAuth discovery correction

Gitea 1.27 provides OpenID Connect discovery and refresh tokens, but does not
advertise `offline_access`. Revision `~ynh3`:

- exposes both `/.well-known/openid-configuration` and the RFC 8414
  `/.well-known/oauth-authorization-server` alias outside YunoHost SSO;
- preserves the canonical Gitea issuer, authorization and token endpoints;
- advertises `offline_access` without changing the claims list;
- preserves PKCE S256 and the authorization-code and refresh-token grants.

The local validator requires these locations and rejects CRLF in lifecycle
scripts.

## Real recovery on YunoHost 12

An attempted local-source upgrade on 2026-07-25 used a Windows checkout with
CRLF. The remote upgrade operation failed before package logic ran:

```text
./upgrade: line 2: $'\r': command not found
./upgrade: line 95: syntax error near unexpected token `|'
```

The subsequent restore reached Gitea startup but failed because the restored
`app.ini` database password did not match the existing MariaDB principal. A
cleanup operation then removed the partially restored app.

Recovery on 2026-07-27 used the original `gitea-pre-upgrade2` archive, whose
SHA-256 was:

```text
30bd2f03497ec50e03bcea25629d319887ede4b59c15a52ffb7e77fad371b0a8
```

Before any database change, an additional safety set was created at:

```text
/home/yunohost.backup/safety/gitea-recovery-20260727T151507Z
```

It contains and verifies:

- a byte-identical copy of the original backup and its info JSON;
- a separate ACL/xattr/numeric-owner archive of the orphan data directory;
- the pre-recovery empty database schema;
- the pre-recovery Nginx vhost;
- `SHA256SUMS` for every file.

The archived database credential was read without printing it and applied to
the existing empty MariaDB principal. Native restore of `1.27.0~ynh2` then
succeeded with:

- 4 users;
- 13 repository database records;
- 14 Git repository directories in the persistent data directory;
- active Gitea and valid Nginx configuration.

The native pre-upgrade backup
`gitea-restored-ynh2-pre-ynh3-20260727T151507Z` was created before upgrading
from an exact LF archive of package commit `dbf5000`. Upgrade to
`1.27.0~ynh3` completed successfully.

## Post-recovery contract

The recovered runtime passed:

- Gitea API HTTP 200 and unauthenticated `/api/v1/user` HTTP 401;
- both OAuth discovery documents HTTP 200;
- issuer `https://git.asimovart.com.br`;
- authorization endpoint `/login/oauth/authorize`;
- token endpoint `/login/oauth/access_token`;
- PKCE S256, refresh-token grant and `offline_access`;
- authorization request HTTP 303 without any YunoHost SSO redirect;
- four preserved registered OAuth applications;
- Gitea, Gitea Runner and Gitea MCP active with `Result=success`;
- MCP protected-resource metadata HTTP 200;
- missing and invalid MCP credentials HTTP 401 with the required
  `WWW-Authenticate` challenge;
- authenticated MCP initialize HTTP 200, initialized notification HTTP 202 and
  53 tools;
- generated credential absent from Gitea, MCP and Nginx logs;
- revoked credential rejected with HTTP 401 and zero recovery tokens remaining;
- Asimov GIT connector identity read as `leivisondias`.

The final native backup is:

```text
gitea-post-recovery-ynh3-20260727T151750Z
SHA-256: 089624495e22e9835e35763f1422485049bea45fc7aa0ba29718ff47ea7364c7
```

Its `backup.csv` explicitly includes `/home/yunohost.app/gitea`, so the final
archive contains the persistent repository data as well as the database and
application files.

The unrelated Nextcloud vhost still emits its pre-existing duplicate `wasm`
MIME warning; Nginx syntax validation succeeds.

## Remaining lifecycle scope

The real recovery, backup, restore, upgrade, OAuth, API and dependent MCP
contracts are verified. A disposable fresh install, URL change, removal and
host reboot of `1.27.0~ynh3` were not repeated during this production recovery.

## Current classification

`RECOVERED_AND_OAUTH_LIFECYCLE_VERIFIED`
