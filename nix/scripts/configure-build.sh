
# Local stand-in for the harp-tech/configure-build@v2 action. Prints shell exports for the three variables the action puts in the environment, so build scripts run `eval "$(configure-build)"`:
#
#   CiBuildVersion            semver used as the package version
#   CiIsForRelease            true on a release event
#   CiFirmwarePreviewVersion  "v" on a release, otherwise the run number that suffixes the firmware file name
#
# The event is described through the environment:
#
#   CI_EVENT           push (default), pull_request or release
#   CI_VERSION         the release tag when CI_EVENT=release, for example v0.1.0
#   CI_RUN_NUMBER      stands in for the GitHub Actions run number, default 0
#   CI_REPO            owner/name queried for the latest release, default is gh's default repository for this checkout
#   CI_DEFAULT_BRANCH  default main
#
# Versioning follows the action: a release build uses the tag and requires its major.minor to match firmwareVersion in device.yml. Any other build starts from the latest GitHub release (patch + 1, or the same version with its pre-release part dropped; 0.0.0 with no releases), appends a pre-release suffix of ci<run> prefixed with the branch name off the default branch, and then lets a higher device.yml firmwareVersion supersede major.minor. A firmwareVersion lower than the release line is an error.

event=${CI_EVENT:-push}
run_number=${CI_RUN_NUMBER:-0}

firmware_version=$(sed -n 's/^firmwareVersion:[[:space:]]*"\{0,1\}\([0-9][0-9]*\.[0-9][0-9]*\)"\{0,1\}.*/\1/p' device.yml)
[ -n "$firmware_version" ] || die "could not read firmwareVersion from device.yml"
firmware_major=${firmware_version%%.*}
firmware_minor=${firmware_version#*.}

# Sets major, minor, patch and prerelease from vX.Y.Z[-pre]. Build metadata is not accepted.
parse_semver() {
  local version=${1#v}
  local pattern='^([0-9]+)\.([0-9]+)\.([0-9]+)(-([0-9A-Za-z.-]+))?$'
  [[ $version =~ $pattern ]] || return 1
  major=${BASH_REMATCH[1]}
  minor=${BASH_REMATCH[2]}
  patch=${BASH_REMATCH[3]}
  prerelease=${BASH_REMATCH[5]}
}

if [ "$event" = release ]; then
  [ -n "${CI_VERSION:-}" ] || die "CI_EVENT=release needs CI_VERSION set to the release tag"
  parse_semver "$CI_VERSION" || die "release tag '$CI_VERSION' is not a valid semver version"
  if [ "$major" -ne "$firmware_major" ] || [ "$minor" -ne "$firmware_minor" ]; then
    die "firmware version '$firmware_version' does not match specified version '${CI_VERSION#v}'"
  fi
  is_for_release=true
  preview_version=v
else
  case "$event" in
    push | pull_request | workflow_dispatch) ;;
    *) warn "event '$event' was not considered when designing the versioning logic" ;;
  esac

  log "Determining version from the latest release"
  repo_args=()
  if [ -n "${CI_REPO:-}" ]; then
    repo_args=(--repo "$CI_REPO")
  fi
  latest_tag=$(gh release view "${repo_args[@]}" --json tagName --jq .tagName 2>/dev/null || true)

  if [ -z "$latest_tag" ]; then
    printf 'no release found (or gh is not authenticated), falling back on 0.0.0\n' >&2
    major=0 minor=0 patch=0 prerelease=
  elif ! parse_semver "$latest_tag"; then
    warn "most recent release '$latest_tag' is not a valid semver version, using 0.0.0 instead"
    major=0 minor=0 patch=0 prerelease=
  else
    printf 'most recent release: %s\n' "$latest_tag" >&2
    if [ -n "$prerelease" ]; then
      prerelease=
    else
      patch=$((patch + 1))
    fi
  fi

  suffix="ci$run_number"
  branch=$(git rev-parse --abbrev-ref HEAD)
  if [ "$branch" != "${CI_DEFAULT_BRANCH:-main}" ]; then
    suffix="$(printf '%s' "$branch" | sed 's/[^0-9A-Za-z-]/-/g')-$suffix"
  fi
  prerelease=$suffix

  if [ "$firmware_major" -lt "$major" ] || { [ "$firmware_major" -eq "$major" ] && [ "$firmware_minor" -lt "$minor" ]; }; then
    die "firmware version '$firmware_version' is lower than CI build version '$major.$minor.$patch-$prerelease'"
  elif [ "$firmware_major" -ne "$major" ] || [ "$firmware_minor" -ne "$minor" ]; then
    major=$firmware_major
    minor=$firmware_minor
    patch=0
  fi

  is_for_release=false
  preview_version=$run_number
fi

version="$major.$minor.$patch${prerelease:+-$prerelease}"
printf 'Configuring build environment to build%s version %s\n' "$([ "$is_for_release" = true ] && printf ' and release')" "$version" >&2

printf 'export CiBuildVersion=%q\n' "$version"
printf 'export CiIsForRelease=%q\n' "$is_for_release"
printf 'export CiFirmwarePreviewVersion=%q\n' "$preview_version"
