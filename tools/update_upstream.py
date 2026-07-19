#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
import tomllib
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.toml"
DOWNLOAD_ROOT = "https://dl.gitea.com/gitea/"
ASSET_NAMES = {
    "amd64": "gitea-{version}-linux-amd64",
    "i386": "gitea-{version}-linux-386",
    "arm64": "gitea-{version}-linux-arm64",
    "armhf": "gitea-{version}-linux-arm-6",
}
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)/?$")


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.hrefs.append(href)


def request(url: str) -> urllib.response.addinfourl:
    headers = {"Accept": "application/octet-stream", "User-Agent": "gitea-ynh-updater"}
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=180)


def request_text(url: str) -> str:
    with request(url) as response:
        return response.read().decode("utf-8")


def version_key(value: str) -> tuple[int, int, int]:
    match = SEMVER.fullmatch(value)
    if not match:
        raise RuntimeError(f"invalid semantic version: {value!r}")
    return tuple(map(int, match.groups()))


def latest_stable_version() -> str:
    parser = LinkCollector()
    parser.feed(request_text(DOWNLOAD_ROOT))
    versions: list[tuple[tuple[int, int, int], str]] = []
    for href in parser.hrefs:
        candidate = urllib.parse.urlparse(href).path.rstrip("/").rsplit("/", 1)[-1]
        match = SEMVER.fullmatch(candidate)
        if match:
            versions.append((tuple(map(int, match.groups())), candidate))
    if not versions:
        raise RuntimeError("official Gitea download index contains no stable semantic version")
    return max(versions)[1]


def download(url: str, destination: Path) -> str:
    digest = hashlib.sha256()
    with request(url) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)
    return digest.hexdigest()


def replace_field(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf'(?m)^([ \t]*{re.escape(key)}[ \t]*=[ \t]*)"[^"]*"[ \t]*$')
    updated, count = pattern.subn(rf'\1"{value}"', text, count=1)
    if count != 1:
        raise RuntimeError(f"unable to update {key}")
    return updated


def current_pins(text: str) -> tuple[str, dict[str, dict[str, str]]]:
    manifest = tomllib.loads(text)
    package_version = str(manifest.get("version", ""))
    upstream_version = package_version.split("~", 1)[0]
    version_key(upstream_version)
    source = manifest.get("resources", {}).get("sources", {}).get("main", {})
    pins: dict[str, dict[str, str]] = {}
    for architecture in ASSET_NAMES:
        entry = source.get(architecture)
        if not isinstance(entry, dict):
            raise RuntimeError(f"manifest source missing architecture {architecture}")
        pins[architecture] = {
            "url": str(entry.get("url", "")),
            "sha256": str(entry.get("sha256", "")),
        }
    return upstream_version, pins


def verify_sigstore(binary: Path, bundle: Path) -> None:
    cosign = shutil.which("cosign")
    if not cosign:
        raise RuntimeError("cosign is required for Gitea >= 1.27 release verification")
    subprocess.run(
        [
            cosign,
            "verify-blob",
            str(binary),
            "--bundle",
            str(bundle),
            "--certificate-oidc-issuer=https://token.actions.githubusercontent.com",
            "--certificate-identity-regexp=https://github.com/go-gitea/gitea/.github/workflows/release-.*",
        ],
        check=True,
    )


def main() -> int:
    version = latest_stable_version()
    version_tuple = version_key(version)
    selected = {
        architecture: (
            asset_name := template.format(version=version),
            f"{DOWNLOAD_ROOT}{version}/{asset_name}",
        )
        for architecture, template in ASSET_NAMES.items()
    }

    hashes: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="gitea-ynh-update-") as temp_dir:
        temp = Path(temp_dir)
        for architecture, (name, url) in selected.items():
            expected_line = request_text(f"{url}.sha256").strip()
            expected_match = re.fullmatch(r"([0-9a-fA-F]{64})(?:\s+\*?\S+)?", expected_line)
            if not expected_match:
                raise RuntimeError(f"invalid upstream SHA-256 file for {name}: {expected_line!r}")
            expected = expected_match.group(1).lower()
            binary = temp / name
            actual = download(url, binary)
            if actual != expected:
                raise RuntimeError(f"SHA-256 mismatch for {name}: expected {expected}, got {actual}")
            hashes[architecture] = actual

            if version_tuple >= (1, 27, 0):
                bundle = temp / f"{name}.sigstore.json"
                download(f"{url}.sigstore.json", bundle)
                verify_sigstore(binary, bundle)

    text = MANIFEST.read_text(encoding="utf-8")
    current, pins = current_pins(text)
    if version_key(current) > version_tuple:
        raise RuntimeError(f"refusing automated downgrade from {current} to {version}")

    if current == version:
        changed_assets = [
            architecture
            for architecture in ASSET_NAMES
            if pins[architecture]["sha256"] != hashes[architecture]
        ]
        if changed_assets:
            raise RuntimeError(
                "upstream republished assets for the currently packaged version; "
                f"manual review required for {', '.join(changed_assets)}"
            )

    updated = replace_field(text, "version", f"{version}~ynh1")
    for architecture, (_, url) in selected.items():
        updated = replace_field(updated, f"{architecture}.url", url)
        updated = replace_field(updated, f"{architecture}.sha256", hashes[architecture])

    if updated == text:
        print(f"already-current {version}")
        return 0

    MANIFEST.write_text(updated, encoding="utf-8")
    if current == version:
        print(f"normalized immutable pins for {version}")
    else:
        print(f"updated {current} -> {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
