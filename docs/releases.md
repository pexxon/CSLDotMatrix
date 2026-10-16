# GitHub builds and releases

`.github/workflows/build.yml` runs on branch pushes, pull requests, version-tag
pushes, and manual **Actions → Test, package, and release → Run workflow** runs.

## What the pipeline does

1. Runs hardware-free unit tests on Python 3.9 and 3.14, plus CLI and shell checks.
2. Builds in a fresh `archlinux:base-devel` container. It installs dependencies,
   creates an unprivileged build user, generates the source archive and matching
   Arch metadata, runs `makepkg` (including tests), validates desktop entries,
   runs `namcap`, and smoke-tests the packaged CLI without opening HID.
3. Saves the package, exact source asset, generated `PKGBUILD` and `.SRCINFO`,
   `SHA256SUMS`, and `namcap.log` as a workflow artifact for 30 days. Open a
   successful run's **Artifacts** section to download its ZIP and extract the
   `.pkg.tar.zst` file.
4. On a pushed `vMAJOR.MINOR.PATCH` tag, publishes a GitHub release with those
   files attached, generated change notes, and installation instructions. Branch,
   pull-request, and manual runs only save artifacts.

Only the release job has repository write permission. It uses GitHub's built-in
`GITHUB_TOKEN`, so no personal token or AUR credentials are needed. The workflow
does not submit packages to AUR. Repository/organization policy must allow
GitHub Actions and the release job's `contents: write` permission.

Windows reference binaries and raw USB captures are excluded from release
sources. Only the explicit build outputs are uploaded. `namcap` errors fail the
build; warnings remain in the attached report for review. These checks do not
test real cooler output, desktop login behavior, or manual-install migration.

## Publish a release

1. Update `pyproject.toml`, `csl_dotmatrix/__init__.py`, and
   `packaging/aur/PKGBUILD` to the same version; update the README/installer text
   as appropriate. The helper rejects mismatched package/project versions and
   tags. Reset `pkgrel` for a new upstream version.
2. Commit and push all application, packaging, and workflow changes. Review the
   successful branch build and its `namcap.log`, and finish the required desktop
   and hardware checks.
3. Create and push the matching tag, for example:

   ```sh
   git tag -a v0.6.0 -m 'CSL DotMatrix v0.6.0'
   git push origin v0.6.0
   ```

4. Wait for the tag's workflow run to pass. Downloads then appear on the
   repository's **Releases** page. Nothing must be uploaded manually.

Pushing the tag is the publication action. Tags must refer to the commit with
the finished sources and workflow. Do not reuse tags or replace assets from an
existing release; publish a new version. If a run fails before creating a
release, fix the cause and rerun the failed jobs when the tagged code is still
correct. If code must change, use a new version/tag.

The generated release `PKGBUILD` and `.SRCINFO` contain the checksum of the
**exact attached source archive**. Those are the files to use for a later AUR
submission. The checked-in checksum is a local snapshot and is refreshed when
preparing a release; the pipeline never commits generated files back to Git.

## Build the same assets locally on Arch

Install `base-devel`, `python-build`, `python-installer`, `python-setuptools`,
`python-hidapi`, `pyside6`, `namcap`, and `desktop-file-utils`, then run as your
regular user:

```sh
bash tools/ci_build_arch.sh
```

Outputs appear in `dist/`. For source/metadata preparation alone:

```sh
python3 tools/prepare_package.py --tag v0.6.0 --output dist
```

Release tooling requires Python 3.11+ and `makepkg`. Downloaded packages are
unsigned local packages, checked with the published SHA-256 manifest; CI does
not set up a signed pacman repository. On a fully updated Arch-based desktop,
install with:

```sh
sudo pacman -S --needed python-hidapi pyside6
sudo pacman -U ./csldotmatrix-0.6.0-1-any.pkg.tar.zst
csl-dotmatrix-session
```

References: [GitHub workflow artifacts](https://github.com/actions/upload-artifact),
[GitHub CLI release creation](https://cli.github.com/manual/gh_release_create).
