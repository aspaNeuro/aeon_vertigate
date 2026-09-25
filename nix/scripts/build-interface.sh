
# Mirrors the Linux x64 legs of the build-interface job: regenerate the C# and Python interfaces from device.yml, check they were committed, then restore, build and pack the NuGet package. Configurations are taken from the arguments, default `debug release`. Packages land in artifacts/package/<configuration>/.

configurations=("$@")
if [ ${#configurations[@]} -eq 0 ]; then
  configurations=(debug release)
fi

export DOTNET_NOLOGO=true
export DOTNET_CLI_TELEMETRY_OPTOUT=true
export DOTNET_GENERATE_ASPNET_CERTIFICATE=false
export ContinuousIntegrationBuild=true

log "Set up .NET tools"
dotnet tool restore

log "Configure build"
eval "$(configure-build)"
# shellcheck disable=SC2154 # set by the eval above
: "${CiBuildVersion:?}" "${CiIsForRelease:?}"

generated=(software/dotnet/Aeon.VertiGate src/aeon/vertigate)

log "Regenerate interfaces"
snapshot_generated "${generated[@]}"
dotnet harp.toolkit generate interface csharp device.yml --namespace Aeon.VertiGate --output software/dotnet/Aeon.VertiGate
dotnet harp.toolkit generate interface python device.yml --output src/aeon/vertigate

log "Verify generated code is up-to-date"
verify_generated "${generated[@]}"

log "Restore"
dotnet restore software/dotnet

for configuration in "${configurations[@]}"; do
  log "Build ($configuration)"
  dotnet build software/dotnet --no-restore --configuration "$configuration"

  log "Pack ($configuration)"
  dotnet pack software/dotnet --no-restore --no-build --configuration "$configuration"
done

log "Collect NuGet packages"
ls -l artifacts/package/*/
