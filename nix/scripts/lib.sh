# Shared helpers, prepended to every script by flake.nix. writeShellApplication already sets errexit, nounset and pipefail.

log() { printf '\n==> %s\n' "$*" >&2; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

root=$(git rev-parse --show-toplevel 2>/dev/null) || die "run from inside the aeon_vertigate checkout"
cd "$root"
# shellcheck disable=SC2034
workflow=.github/workflows/Aeon.VertiGate.yml

# The workflow checks generated code with `git diff --exit-code` against a clean checkout. Locally the tree is rarely clean, so the check is against a snapshot of the generated paths taken before regenerating: call snapshot_generated before the generator and verify_generated after it, with the same paths.
generated_snapshot=$(mktemp -d)
trap 'rm -rf "$generated_snapshot"' EXIT

snapshot_generated() {
  local path
  for path in "$@"; do
    if [ -e "$path" ]; then
      cp -a --parents "$path" "$generated_snapshot"
    fi
  done
}

verify_generated() {
  local path status=0
  for path in "$@"; do
    if [ -e "$generated_snapshot/$path" ]; then
      # .gitattributes sets text=auto, so git ignores CRLF versus LF; the generators write CRLF.
      diff -ru --strip-trailing-cr -x bin -x obj -x __pycache__ "$generated_snapshot/$path" "$path" || status=1
    elif [ -e "$path" ]; then
      printf 'new file: %s\n' "$path"
      status=1
    fi
  done
  [ "$status" -eq 0 ] || die "generated code is out of date; commit the regenerated files"
}
