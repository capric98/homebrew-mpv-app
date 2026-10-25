import copy
import hashlib
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import update as updater


def release(version="0.41.0"):
    assets = []
    for minimum, arch, digest in [(14, "arm", "a" * 64), (15, "intel", "b" * 64), (26, "arm", "c" * 64)]:
        name = f"mpv-v{version}-macos-{minimum}-{arch}.zip"
        assets.append({"name": name, "digest": "sha256:" + digest,
                       "browser_download_url": f"https://github.com/mpv-player/mpv/releases/download/v{version}/{name}"})
    return {"tag_name": "v" + version, "prerelease": False, "draft": False, "assets": assets}


def archive(extra=None, omit_binary=False, executable=True):
    inner = io.BytesIO()
    with tarfile.open(fileobj=inner, mode="w:gz") as tar:
        files = [("mpv.app/Contents/Info.plist", b"plist", 0o644)]
        if not omit_binary:
            files.append(("mpv.app/Contents/MacOS/mpv", b"binary", 0o755 if executable else 0o644))
        for name, data, mode in files:
            member = tarfile.TarInfo(name)
            member.size, member.mode = len(data), mode
            tar.addfile(member, io.BytesIO(data))
        if extra:
            tar.addfile(extra)
    result = io.BytesIO()
    with zipfile.ZipFile(result, mode="w") as outer:
        outer.writestr("mpv.tar.gz", inner.getvalue())
    result.seek(0)
    return result


class UpdateTests(unittest.TestCase):
    def test_selects_lowest_os_for_both_architectures(self):
        version, builds = updater.select_builds(release())
        self.assertEqual(version, "0.41.0")
        self.assertEqual([(b.arch, b.minimum) for b in builds], [("arm", 14), ("intel", 15)])

    def test_rejects_incomplete_or_untrusted_release_metadata(self):
        variants = []
        for field in ("prerelease", "draft"):
            bad = release(); bad[field] = True; variants.append(bad)
        bad = release(); bad["tag_name"] = "git-release"; variants.append(bad)
        bad = release(); bad["assets"] = bad["assets"][:1]; variants.append(bad)
        bad = release(); bad["assets"][0]["digest"] = None; variants.append(bad)
        bad = release(); bad["assets"][0]["browser_download_url"] = "https://example.invalid/mpv.zip"; variants.append(bad)
        for bad in variants:
            with self.subTest(metadata=bad), self.assertRaises(ValueError):
                updater.select_builds(bad)

    def test_rejects_unknown_os(self):
        bad = release()
        bad["assets"][0]["name"] = bad["assets"][0]["name"].replace("macos-14", "macos-99")
        bad["assets"] = bad["assets"][:2]
        with self.assertRaisesRegex(ValueError, "Unknown macOS"):
            updater.select_builds(bad)

    def test_rejects_downgrade_and_replaced_same_version(self):
        version, builds = updater.select_builds(release())
        current = updater.render(version, builds)
        old_version, old_builds = updater.select_builds(release("0.40.0"))
        with self.assertRaisesRegex(ValueError, "downgrade"):
            updater.validate_transition(current, old_version, old_builds)
        bad = copy.deepcopy(release()); bad["assets"][0]["digest"] = "sha256:" + "d" * 64
        version, replaced = updater.select_builds(bad)
        with self.assertRaisesRegex(ValueError, "different checksums"):
            updater.validate_transition(current, version, replaced)

    def test_unchanged_release_skips_download_and_write(self):
        version, builds = updater.select_builds(release())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "mpv-app.rb"
            target.write_text(updater.render(version, builds))
            original_time = target.stat().st_mtime_ns
            with patch.object(updater, "verify_download") as verify:
                self.assertFalse(updater.update(release(), target))
                verify.assert_not_called()
            self.assertEqual(target.stat().st_mtime_ns, original_time)

    def test_second_architecture_failure_leaves_original_cask(self):
        version, builds = updater.select_builds(release("0.40.0"))
        original = updater.render(version, builds)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "mpv-app.rb"; target.write_text(original)
            with patch.object(updater, "verify_download", side_effect=[None, ValueError("bad Intel download")]):
                with self.assertRaisesRegex(ValueError, "bad Intel"):
                    updater.update(release(), target)
            self.assertEqual(target.read_text(), original)

    def test_check_mode_does_not_download_or_write(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "mpv-app.rb"
            with patch.object(updater, "verify_download") as verify:
                self.assertTrue(updater.update(release(), target, check=True))
                verify.assert_not_called()
            self.assertFalse(target.exists())

    def test_verified_update_writes_new_version(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "mpv-app.rb"
            with patch.object(updater, "verify_download") as verify:
                self.assertTrue(updater.update(release(), target))
                self.assertEqual(verify.call_count, 2)
            self.assertIn('version "0.41.0"', target.read_text())
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_valid_nested_archive(self):
        updater.validate_archive(archive())

    def test_rejects_missing_or_nonexecutable_player(self):
        for options in ({"omit_binary": True}, {"executable": False}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                updater.validate_archive(archive(**options))

    def test_rejects_path_escape_and_external_symlink(self):
        unsafe = tarfile.TarInfo("../outside")
        link = tarfile.TarInfo("mpv.app/outside")
        link.type, link.linkname = tarfile.SYMTYPE, "../../outside"
        for extra in (unsafe, link):
            with self.subTest(path=extra.name), self.assertRaises(ValueError):
                updater.validate_archive(archive(extra=extra))

    def test_download_hash_mismatch_is_rejected(self):
        _, builds = updater.select_builds(release())
        with patch.object(updater, "request", return_value=io.BytesIO(b"wrong bytes")):
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                updater.verify_download(builds[0])

    def test_download_checks_hash_and_archive_together(self):
        payload = archive().getvalue()
        build = updater.Build("arm", 14, "test.zip", "https://example.invalid", hashlib.sha256(payload).hexdigest())
        with patch.object(updater, "request", return_value=io.BytesIO(payload)):
            updater.verify_download(build)


if __name__ == "__main__":
    unittest.main()
