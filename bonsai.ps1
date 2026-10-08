# Launches the Bonsai environment in .bonsai/ with the locally built Aeon.VertiGate
# assemblies added to the library search path, so the package does not need to be
# installed from the package manager to test changes to software/dotnet.
#
# The interface is built first, so a change to device.yml or to the C# sources is always
# in the environment that starts. Pass -NoBuild to skip that step.
#
# Any additional arguments are forwarded to Bonsai, for example a workflow file to open
# or --start to run it immediately:
#     ./bonsai.ps1 docs/workflows/GateControl.bonsai --start
#
# Use -WhatIf to print the command line without launching Bonsai.
#
# Runs on Windows PowerShell 5.1 as well as PowerShell 7. Keep Join-Path to two
# arguments: the multi-argument form is PowerShell 7 only, and 5.1 is the Windows default.
[CmdletBinding(SupportsShouldProcess)] param (
    [ValidateSet('Debug', 'Release')]
    [string]$Configuration = 'Debug',
    [switch]$NoBuild,
    [Parameter(ValueFromRemainingArguments)]
    [string[]]$BonsaiArgs
)
Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

$bootstrapperPath = Join-Path (Join-Path $PSScriptRoot '.bonsai') 'Bonsai.exe'
if (-not (Test-Path $bootstrapperPath)) {
    throw "Bonsai.exe not found at $bootstrapperPath. Place the Bonsai bootstrapper in .bonsai/ next to Bonsai.config."
}

if (-not $NoBuild) {
    Write-Host "Building the interface ($Configuration)..."
    & dotnet build (Join-Path $PSScriptRoot 'software/dotnet') -c $Configuration --nologo -v minimal
    if ($LASTEXITCODE -ne 0) { throw "dotnet build failed with exit code $LASTEXITCODE." }
}

# Bonsai.exe targets .NET Framework, so only the net4x build outputs can be loaded.
$artifactsGlob = Join-Path (Join-Path (Join-Path $PSScriptRoot 'artifacts') 'bin') '*'
$libPaths = Get-ChildItem (Join-Path $artifactsGlob "$($Configuration.ToLower())_net4*") -Directory | Select-Object -Expand FullName
if (-not $libPaths) {
    throw "No $Configuration net4x build output found under artifacts/bin. Run: dotnet build software/dotnet -c $Configuration"
}

$bootstrapperArgs = @()
foreach ($path in $libPaths) {
    $bootstrapperArgs += '--lib'
    $bootstrapperArgs += $path
}
$bootstrapperArgs += $BonsaiArgs

if ($PSCmdlet.ShouldProcess("$bootstrapperPath $bootstrapperArgs", 'Launch Bonsai')) {
    & $bootstrapperPath $bootstrapperArgs
}
