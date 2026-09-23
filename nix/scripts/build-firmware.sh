
# Mirrors the build-firmware job. Builds a MicroPython image for one board with the application frozen in and names it like the release asset.
#
#   BOARD            board directory under firmware/boards, default NEUROPICO (hardware target 0.1)
#   MICROPYTHON_DIR  where the MicroPython tree is cloned, default artifacts/micropython
#
# The MicroPython version is read from the workflow file so the two cannot drift. The clone and its submodules are kept between runs.

board=${BOARD:-NEUROPICO}
board_dir="$root/firmware/boards/$board"
[ -d "$board_dir" ] || die "no board directory at $board_dir"

micropython_version=$(sed -n 's/^  MICROPYTHON_VERSION:[[:space:]]*//p' "$workflow")
[ -n "$micropython_version" ] || die "could not read MICROPYTHON_VERSION from $workflow"
micropython_dir=${MICROPYTHON_DIR:-$root/artifacts/micropython}

log "Checkout"
git submodule update --init --recursive

log "Configure build"
eval "$(configure-build)"
# shellcheck disable=SC2154 # set by the eval above
: "${CiBuildVersion:?}" "${CiFirmwarePreviewVersion:?}"

log "Regenerate firmware version module"
snapshot_generated firmware/vertigate/_version.py
uv run tools/firmware_version.py

log "Verify generated code is up-to-date"
verify_generated firmware/vertigate/_version.py

log "Checkout MicroPython $micropython_version"
if [ ! -d "$micropython_dir/.git" ]; then
  git clone --branch "$micropython_version" --depth 1 https://github.com/micropython/micropython.git "$micropython_dir"
else
  current=$(git -C "$micropython_dir" describe --tags --exact-match 2>/dev/null || echo unknown)
  if [ "$current" != "$micropython_version" ]; then
    die "$micropython_dir is at $current, not $micropython_version; remove it or point MICROPYTHON_DIR elsewhere"
  fi
fi

log "Set up the rp2 toolchain"
arm-none-eabi-gcc --version | head -1
picotool version

log "Fetch MicroPython submodules"
make -C "$micropython_dir/ports/rp2" BOARD_DIR="$board_dir" submodules

log "Build mpy-cross"
make -C "$micropython_dir/mpy-cross" -j"$(nproc)"

log "Build firmware"
# Start from a clean build directory as the workflow does; the CMake cache would otherwise keep a previous toolchain.
rm -rf "$micropython_dir/ports/rp2/build-$board"
make -C "$micropython_dir/ports/rp2" BOARD_DIR="$board_dir" -j"$(nproc)"

log "Name firmware image"
eval "$(sed -n 's/^\(FW_VERSION\|HW_VERSION\|HARP_VERSION\) = (\([0-9]*\), \([0-9]*\))$/\1=\2.\3/p' firmware/vertigate/_version.py)"
# shellcheck disable=SC2154 # set by the eval above
: "${FW_VERSION:?}" "${HW_VERSION:?}" "${HARP_VERSION:?}"
PREVIEW=""
if [ "$CiFirmwarePreviewVersion" != "v" ]; then PREVIEW="-preview$CiFirmwarePreviewVersion"; fi
NAME="VertiGate-fw$FW_VERSION-harp$HARP_VERSION-hw$HW_VERSION-ass0$PREVIEW.uf2"
mkdir -p artifacts/firmware
cp "$micropython_dir/ports/rp2/build-$board/firmware.uf2" "artifacts/firmware/$NAME"
ls -l artifacts/firmware
