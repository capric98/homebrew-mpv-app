#!/usr/bin/env python3
"""Update the mpv-app Cask from mpv's latest stable release. Python 3 stdlib only."""

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile


API = "https://api.github.com/repos/mpv-player/mpv/releases/latest"
ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "Casks/mpv-app.rb"
MACOS_NAMES = {
    11: "big_sur", 12: "monterey", 13: "ventura", 14: "sonoma",
    15: "sequoia", 26: "tahoe", 27: "golden_gate",
}


@dataclass(frozen=True)
class Build:
    arch: str
    minimum: int
    name: str
    url: str
    sha256: str


def request(url):
    headers = {"User-Agent": "personal-mpv-app-tap"}
    # The updater downloads release assets without the API token.
    if url.startswith("https://api.github.com/"):
        headers["Accept"] = "application/vnd.github+json"
        if os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120)


def select_builds(release):
    tag = release["tag_name"]
    if (release.get("prerelease") or release.get("draft")
            or not re.fullmatch(r"v\d+(?:\.\d+){1,3}", tag)):
        raise ValueError("Expected a numbered stable release, not git-release/prerelease")
    selected = []
    for arch in ("arm", "intel"):
        candidates = []
        for asset in release["assets"]:
            match = re.fullmatch(
                r"mpv-" + re.escape(tag) + r"-macos-(\d+)-" + arch + r"\.zip",
                asset["name"],
            )
            if match:
                candidates.append((int(match[1]), asset))
        if not candidates:
            raise ValueError(f"No {arch} macOS build; review upstream asset naming")
        minimum, asset = min(candidates, key=lambda item: item[0])
        if minimum not in MACOS_NAMES:
            raise ValueError(f"Unknown macOS {minimum}; add the Homebrew symbol after review")
        url = f"https://github.com/mpv-player/mpv/releases/download/{tag}/{asset['name']}"
        if asset["browser_download_url"] != url:
            raise ValueError("Unexpected asset URL; expected the mpv-player/mpv release")
        digest = asset.get("digest") or ""
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise ValueError("Missing GitHub SHA-256 digest; update refused")
        selected.append(Build(arch, minimum, asset["name"], url, digest[7:]))
    return tag[1:], selected


def render(version, builds):
    lines = ['cask "mpv-app" do', f'  version "{version}"', '']
    for build in builds:
        url = build.url.replace(f"v{version}", "v#{version}")
        lines += [f'  on_{build.arch} do', f'    sha256 "{build.sha256}"',
                  f'    url "{url}"',
                  f'    depends_on macos: :{MACOS_NAMES[build.minimum]}', '  end', '']
    lines += ['  name "mpv"', '  desc "Media player distributed as a complete macOS app"',
              '  homepage "https://mpv.io/"', '', '  livecheck do',
              '    url "https://github.com/mpv-player/mpv"', '    strategy :github_latest', '  end', '',
              '  conflicts_with cask: ["mpv-macwrapper", "mpv-official", "stolendata-mpv"]', '',
              '  container nested: "mpv.tar.gz"', '  app "mpv.app"', '',
              '  caveats <<~EOS',
              '    This is a community-maintained tap using builds from mpv-player/mpv.',
              '    The mpv formula is not required. Gatekeeper checks remain enabled.',
              '  EOS', 'end', '']
    return "\n".join(lines)


def validate_transition(current, version, builds):
    """Reject downgrades and silent replacement of assets under an existing tag."""
    if not current:
        return
    match = re.search(r'^  version "([0-9.]+)"$', current, re.MULTILINE)
    if not match:
        raise ValueError("Cannot read current Cask version; review it manually")
    old = match[1]
    old_parts, new_parts = old.split("."), version.split(".")
    width = max(len(old_parts), len(new_parts))
    old_key = tuple(map(int, old_parts + ["0"] * (width - len(old_parts))))
    new_key = tuple(map(int, new_parts + ["0"] * (width - len(new_parts))))
    if new_key < old_key:
        raise ValueError(f"Refusing downgrade from {old} to {version}")
    if new_key == old_key:
        old_sums = re.findall(r'^    sha256 "([0-9a-f]{64})"$', current, re.MULTILINE)
        if old_sums != [b.sha256 for b in builds]:
            raise ValueError("Same release has different checksums; investigate asset replacement manually")


def validate_archive(archive):
    """Inspect ZIP/TAR without extracting or executing the downloaded app."""
    archive.seek(0)
    with zipfile.ZipFile(archive) as outer:
        if outer.namelist() != ["mpv.tar.gz"]:
            raise ValueError("ZIP layout changed; expected only mpv.tar.gz")
        if outer.getinfo("mpv.tar.gz").file_size > 1024**3:
            raise ValueError("Unexpectedly large inner archive")
        with tempfile.TemporaryFile() as inner:
            with outer.open("mpv.tar.gz") as source:
                shutil.copyfileobj(source, inner, length=1024 * 1024)
            inner.seek(0)
            required = {"mpv.app/Contents/Info.plist", "mpv.app/Contents/MacOS/mpv"}
            with tarfile.open(fileobj=inner, mode="r|gz") as bundle:
                for member in bundle:
                    path = PurePosixPath(member.name)
                    if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != "mpv.app":
                        raise ValueError("Unexpected path outside mpv.app in TAR")
                    if member.isdev() or member.isfifo():
                        raise ValueError("Unexpected special file in App bundle")
                    if member.issym() or member.islnk():
                        base = posixpath.dirname(member.name) if member.issym() else ""
                        resolved = posixpath.normpath(posixpath.join(base, member.linkname))
                        if not resolved.startswith("mpv.app/"):
                            raise ValueError("App bundle link escapes the bundle")
                    if member.name in required and member.isfile() and member.size > 0:
                        if member.name.endswith("/MacOS/mpv") and not member.mode & 0o111:
                            raise ValueError("mpv binary is not executable")
                        required.remove(member.name)
            if required:
                raise ValueError("TAR does not contain a complete mpv.app: " + ", ".join(sorted(required)))


def verify_download(build):
    print(f"Downloading and verifying {build.name} …", flush=True)
    with tempfile.TemporaryFile() as archive:
        hasher = hashlib.sha256()
        with request(build.url) as response:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)
                archive.write(chunk)
        if hasher.hexdigest() != build.sha256:
            raise ValueError(f"SHA-256 mismatch: {build.name}")
        validate_archive(archive)


def update(release, target=TARGET, check=False):
    version, builds = select_builds(release)
    current = target.read_text() if target.exists() else ""
    validate_transition(current, version, builds)
    content = render(version, builds)
    if current == content:
        print(f"Cask is current: {version}; no downloads or changes")
        return False
    if check:
        print(f"Cask update available: {version}")
        return True
    # Both architectures must verify before any tracked file is changed.
    for build in builds:
        verify_download(build)
    with tempfile.NamedTemporaryFile(mode="w", dir=target.parent, suffix=".tmp", delete=False) as temporary:
        temporary.write(content)
        temporary_name = Path(temporary.name)
    try:
        temporary_name.chmod(0o644)
        temporary_name.replace(target)
    finally:
        temporary_name.unlink(missing_ok=True)
    print(f"Updated {target.name} to {version}")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, help="Use saved GitHub release JSON")
    parser.add_argument("--check", action="store_true", help="Metadata check only: exit 1 if update is available")
    args = parser.parse_args()
    try:
        if args.metadata:
            release = json.loads(args.metadata.read_text())
        else:
            with request(API) as response:
                release = json.load(response)
        changed = update(release, check=args.check)
        return 1 if args.check and changed else 0
    except (OSError, ValueError, KeyError, tarfile.TarError, zipfile.BadZipFile) as error:
        print(f"Update failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
