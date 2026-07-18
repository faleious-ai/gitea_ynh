#!/usr/bin/env python3
from __future__ import annotations

import hashlib
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
