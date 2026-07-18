#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.toml"
API = "https://api.github.com/repos/go-gitea/gitea/releases/latest"
ASSETS = {
    "amd64": re.compile(r"^gitea-(?P<version>\d+\.\d+\.\d+)-linux-amd64$"),
    "i386": re.compile(r"^gitea-(?P<version>\d+\.\d+\.\d+)-linux-386$"),
    "arm64": re.compile(r"^gitea-(?P<version>\d+\.\d+\.\d+)-linux-arm64$"),
    "armhf": re.compile(r"^gitea-(?P<version>\d+\.\d+\.\d+)-linux-arm-6$"),
}


def request_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "gitea-ynh-updater",
            **({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.getenv("GITHUB_TOKEN") else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def download(url: str, destination: Path) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "gitea-ynh-updater"})
    digest = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=180) as response, destination.open("wb") as output:
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
    release = request_json(API)
    tag = str(release.get("tag_name", ""))
    if release.get("draft") or release.get("prerelease") or not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise RuntimeError(f"latest release is not a stable semver release: {tag!r}")
    version = tag.removeprefix("v")
    assets = {asset["name"]: asset["browser_download_url"] for asset in release.get("assets", [])}

    selected: dict[str, tuple[str, str]] = {}
    for architecture, matcher in ASSETS.items():
        matches = [(name, url) for name, url in assets.items() if matcher.fullmatch(name)]
        if len(matches) != 1:
            raise RuntimeError(f"expected one {architecture} binary, found {[name for name, _ in matches]}")
        selected[architecture] = matches[0]

    with tempfile.TemporaryDirectory(prefix="gitea-ynh-update-") as temp_dir:
        temp = Path(temp_dir)
        hashes: dict[str, str] = {}
        for architecture, (name, url) in selected.items():
            binary = temp / name
            hashes[architecture] = download(url, binary)
            if tuple(map(int, version.split("."))) >= (1, 27, 0):
                bundle_name = f"{name}.sigstore.json"
                bundle_url = assets.get(bundle_name)
                if not bundle_url:
                    raise RuntimeError(f"missing Sigstore bundle {bundle_name}")
                bundle = temp / bundle_name
                download(bundle_url, bundle)
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
