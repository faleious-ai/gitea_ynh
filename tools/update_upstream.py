#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
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
    pattern = re.compile(rf'(?m)^(\s*{re.escape(key)}\s*=\s*)"[^"]*"\s*$')
    updated, count = pattern.subn(rf'\1"{value}"', text, count=1)
    if count != 1:
        raise RuntimeError(f"unable to update {key}")
    return updated


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
    version_tuple = tuple(map(int, version.split(".")))
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
    current = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    if not current:
        raise RuntimeError("manifest version not found")
    current_upstream = current.group(1).split("~", 1)[0]
    if current_upstream == version:
        print(f"already-current {version}")
        return 0

    text = replace_field(text, "version", f"{version}~ynh1")
    for architecture, (_, url) in selected.items():
        text = replace_field(text, f"{architecture}.url", url)
        text = replace_field(text, f"{architecture}.sha256", hashes[architecture])
    MANIFEST.write_text(text, encoding="utf-8")
    print(f"updated {current_upstream} -> {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
