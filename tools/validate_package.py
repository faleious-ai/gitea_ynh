#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.toml"
TESTS = ROOT / "tests.toml"
STABLE_VERSION = re.compile(r"^\d+\.\d+\.\d+~ynh\d+$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN = ("/latest/", "nightly", "-rc", "-beta", "-alpha")


def fail(messages: list[str]) -> int:
    for message in messages:
        print(f"ERROR: {message}", file=sys.stderr)
    return 1


def main() -> int:
    errors: list[str] = []
    manifest = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
    tomllib.loads(TESTS.read_text(encoding="utf-8"))

    version = manifest.get("version", "")
    if not STABLE_VERSION.fullmatch(version):
        errors.append(f"invalid package version: {version!r}")
    upstream_version = version.split("~", 1)[0]

    integration = manifest.get("integration", {})
    architectures = integration.get("architectures", [])
    source = manifest.get("resources", {}).get("sources", {}).get("main", {})
    if source.get("autoupdate", {}).get("strategy") != "latest_github_release":
        errors.append("main source must retain latest_github_release metadata")

    for architecture in architectures:
        entry = source.get(architecture)
        if not isinstance(entry, dict):
            errors.append(f"missing source entry for {architecture}")
            continue
        url = str(entry.get("url", ""))
        digest = str(entry.get("sha256", ""))
        if upstream_version not in url:
            errors.append(f"{architecture} URL does not contain {upstream_version}")
        if any(marker in url.lower() for marker in FORBIDDEN):
            errors.append(f"{architecture} URL is mutable or prerelease: {url}")
        if not SHA256.fullmatch(digest):
            errors.append(f"invalid SHA-256 for {architecture}")

    gitea_config = (ROOT / "conf/app.ini").read_text(encoding="utf-8")

    def ini_section(name: str) -> str:
        match = re.search(
            rf"(?ms)^\[{re.escape(name)}\][ \t]*\r?\n(.*?)(?=^\[[^\]]+\][ \t]*$|\Z)",
            gitea_config,
        )
        return match.group(1) if match else ""

    if re.search(r"(?m)^[ \t]*ALLOWED_HOST_LIST[ \t]*=", ini_section("webhook")):
        errors.append("ALLOWED_HOST_LIST must not remain in the deprecated [webhook] section")
    if not re.search(r"(?m)^[ \t]*ALLOWED_HOST_LIST[ \t]*=", ini_section("security")):
        errors.append("ALLOWED_HOST_LIST must be declared in the [security] section")

    nginx = (ROOT / "conf/nginx.conf").read_text(encoding="utf-8")
    for required, message in (
        ("location = __PATH__/.well-known/openid-configuration", "Nginx must harden OIDC discovery metadata"),
        ("location = __PATH__/.well-known/oauth-authorization-server", "Nginx must expose OAuth authorization-server metadata"),
        ("sub_filter_types application/json", "OAuth metadata filtering must apply to JSON"),
        ("sub_filter_once on", "OAuth metadata must be modified only once"),
        ("sub_filter '\"groups\"' '\"groups\", \"offline_access\"'", "OAuth metadata must advertise offline_access"),
        ('proxy_set_header Accept-Encoding ""', "OAuth metadata proxy must disable compression for deterministic filtering"),
    ):
        if required not in nginx:
            errors.append(message)

    metadata_fixture = '{"scopes_supported":["openid","profile","email","groups"],"claims_supported":["groups"]}'
    hardened_metadata = json.loads(metadata_fixture.replace('"groups"', '"groups", "offline_access"', 1))
    if hardened_metadata.get("scopes_supported") != ["openid", "profile", "email", "groups", "offline_access"]:
        errors.append("offline_access must be added to scopes_supported")
    if hardened_metadata.get("claims_supported") != ["groups"]:
        errors.append("OAuth metadata filtering must not modify claims_supported")

    for script in (ROOT / "scripts").iterdir():
        if script.is_file() and b"\r\n" in script.read_bytes():
            errors.append(f"CRLF line endings in {script.relative_to(ROOT)}")

    if errors:
        return fail(errors)

    fingerprint = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    print(f"package-valid version={version} manifest_sha256={fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
