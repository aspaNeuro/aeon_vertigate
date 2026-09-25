# Local CI

This flake mirrors the build jobs of `.github/workflows/Aeon.VertiGate.yml` so they can be run on a developer machine before pushing. Each job is a script that runs the workflow's steps in the same order against the working tree. Tools that the workflow installs with apt or setup actions come from nixpkgs instead.

Run from the repository root:

```sh
nix run ./nix#lint                 # actionlint + shellcheck over the workflow file
nix run ./nix#build-firmware       # Build Firmware (hw0.1)
nix run ./nix#build-interface      # Build Interface (Linux x64 debug and release)
nix run ./nix#ci                   # all of the above
nix run ./nix#configure-build      # print the versioning variables the harp-tech/configure-build action would export
nix run ./nix#act -- push -l       # run the real workflow file under nektos/act
nix develop ./nix                  # shell with the toolchain and every script on PATH
```

Outputs go under `artifacts/`, which git ignores: the firmware image in `artifacts/firmware/`, NuGet packages in `artifacts/package/<configuration>/`, and the MicroPython checkout in `artifacts/micropython/`.

## Differences from GitHub

The generated-code check compares against the working tree as it was before regeneration rather than against `HEAD`, so an uncommitted but consistent `device.yml` change passes locally and only fails on GitHub once pushed without the regenerated files.

`configure-build` reads the latest release with `gh`, so it needs an authenticated `gh` to compute the same version as GitHub. Without one it falls back to `0.0.0` as the action does for a repository without releases. Set `CI_EVENT=release CI_VERSION=vX.Y.Z` to simulate a release build, `CI_RUN_NUMBER` to set the preview suffix, and `CI_REPO=owner/name` to query a specific repository.

The publish jobs and the Windows leg of the interface matrix are not mirrored.
