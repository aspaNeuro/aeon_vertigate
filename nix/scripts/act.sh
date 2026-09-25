
# Runs the real workflow file under nektos/act. Arguments are passed through, so pick the event and job as usual:
#
#   act push -j build-firmware
#   act pull_request -l
#
# Uses Podman's Docker-compatible socket when no Docker daemon answers. The artifact server backs actions/upload-artifact and download-artifact, which fail without one. The publish jobs need repository secrets and are not expected to pass.

if [ -z "${DOCKER_HOST:-}" ] && ! docker info >/dev/null 2>&1 && command -v podman >/dev/null; then
  systemctl --user start podman.socket 2>/dev/null || true
  export DOCKER_HOST="unix://${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock"
fi

mkdir -p artifacts/act
exec act -W "$workflow" \
  --artifact-server-path "$root/artifacts/act" \
  -P ubuntu-latest=catthehacker/ubuntu:act-latest \
  "$@"
