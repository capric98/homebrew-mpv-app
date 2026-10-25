# homebrew-mpv-app

English | [简体中文](README.zh-CN.md)

A personally maintained Homebrew tap that installs **the complete macOS app built by the mpv project** into `/Applications/mpv.app`.

**This repository is not affiliated with or endorsed by the mpv or Homebrew projects.** Downloads come from stable releases in [`mpv-player/mpv`](https://github.com/mpv-player/mpv/releases/latest). The app is not repackaged and does not depend on Homebrew's `mpv` formula.

## Installation and upgrades

```bash
brew install --cask capric98/mpv-app/mpv-app
```

If you installed `/Applications/mpv.app` manually, move it elsewhere first to avoid a file conflict. After confirming the new app plays your media, you can remove the formula if you no longer need it:

```bash
brew uninstall --formula mpv
```

If Homebrew reports that other software still depends on the formula, keep it installed. This cask does not add an `mpv` command to your shell. You can run the executable inside the app directly:

```bash
/Applications/mpv.app/Contents/MacOS/mpv --version
```

To upgrade:

```bash
brew update
brew upgrade --cask capric98/mpv-app/mpv-app
```

To uninstall, run `brew uninstall --cask mpv-app`. Your configuration in `~/.config/mpv/` is preserved.

For each architecture, Apple Silicon and Intel, the updater selects the build targeting the oldest available macOS version to maximize compatibility. See the cask definition for the package version and system requirements.

## Automatic updates with GitHub Actions

`.github/workflows/update.yml` checks for the latest stable release every day at **07:23 UTC**. You can also run it manually through **Actions → Update mpv app → Run workflow** to verify the repository permissions and environment.

When an update is available, the workflow:

1. Checks the release version, download origin, assets for both architectures, and GitHub's SHA-256 digests.
2. Downloads the Apple Silicon and Intel ZIP archives, computes their SHA-256 hashes, and checks that the nested `mpv.tar.gz` contains a complete app.
3. Runs the updater tests and checks the cask's Ruby syntax before **committing and pushing directly to the default branch** as `github-actions[bot]`.

If nothing has changed, it skips the downloads and creates no commit. If any verification fails, it does not commit the cask. This automation updates the cask definition; run `brew update` and `brew upgrade` on your Mac to install the new app.

The workflow uses GitHub's built-in `GITHUB_TOKEN` with `contents: write`. **No additional secret or personal access token is required.** Repository and organization policies must allow Actions to run and write to the repository. If branch protection blocks direct pushes from the bot, change the workflow to open an update pull request and merge it according to your branch rules.

Commits pushed with `GITHUB_TOKEN` do not trigger ordinary `push` workflows, so the update workflow runs its own tests and syntax check. `validate.yml` checks your manual pushes and ordinary pull requests.

Scheduled workflows run only on the default branch and may be delayed. In public repositories, GitHub may disable scheduled workflows after 60 days without repository activity; re-enable them in Actions if needed.

## Maintenance

Under normal conditions, Actions maintains the version, download URLs, SHA-256 hashes, and minimum macOS requirements. Watch for failed workflow notifications.

Manual changes may be needed when:

- mpv changes asset names or archive layouts, or stops publishing an architecture.
- A new macOS version is not yet included in the updater's `MACOS_NAMES` mapping.
- An existing release's asset checksum changes. The updater refuses silent replacement; investigate why upstream re-uploaded the asset before proceeding.
- Branch protection blocks automated commits, or scheduled workflows have been disabled.

This tap follows stable releases, not the rolling `git-release` development builds. Versions and checksums are pinned; it does not use `version :latest` or `sha256 :no_check`.

To check or update locally:

```bash
cd ~/Git/homebrew-mpv-app
python3 -m unittest discover -s tests -v
python3 scripts/update.py --check  # 0=current; 1=update available; 2=check failed
python3 scripts/update.py         # Download, verify, and update the cask if needed
git diff -- Casks/mpv-app.rb
```

The updater requires Python 3.9 or later and uses only the standard library. No pip dependencies are needed. If you reach GitHub's unauthenticated API rate limit, supply a token through the `GITHUB_TOKEN` environment variable. Do not commit tokens to the repository. The API token is not sent with asset download requests.

The checkout action is pinned to a commit SHA. Dependabot checks for GitHub Actions updates monthly.

## Gatekeeper

A build published by the mpv project is not necessarily signed or notarized by Apple. This cask keeps the default security checks enabled and does not automatically run `xattr` or disable Gatekeeper. If macOS blocks the first launch, verify the download source and check **System Settings → Privacy & Security**. Matching a download checksum confirms that its bytes match the release asset; it is not Apple notarization.

## References

- [mpv installation](https://mpv.io/installation/)
- [Latest stable mpv release](https://github.com/mpv-player/mpv/releases/latest)
- [Homebrew Cask Cookbook](https://docs.brew.sh/Cask-Cookbook)
- [GitHub Actions schedule event](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Triggering workflows with GITHUB_TOKEN](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow#triggering-a-workflow-from-a-workflow)
