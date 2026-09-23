
# Runs the whole build side of the workflow: lint the workflow file, then the firmware and interface jobs. The publish jobs are not mirrored.

lint
build-firmware
build-interface debug release

log "Done"
printf 'Firmware image and NuGet packages are under artifacts/. The publish jobs (GitHub Packages, NuGet.org) run only on GitHub.\n'
