# Launches the Bonsai environment in .bonsai/ with the locally built Aeon.VertiGate
# assemblies added to the library search path, so the package does not need to be
# installed from the package manager to test changes to software/dotnet.
#
# Build the interface first, from the repository root:
#     dotnet build software/dotnet -c Debug
#
# Any additional arguments are forwarded to Bonsai, for example a workflow file to open
# or --start to run it immediately:
#     ./bonsai.ps1 docs/workflows/GateControl.bonsai --start
#
# Use -WhatIf to print the command line without launching Bonsai.
[CmdletBinding(SupportsShouldProcess)] param (
    [ValidateSet('Debug', 'Release')]
    [string]$Configuration = 'Debug',
    [Parameter(ValueFromRemainingArguments)]
    [string[]]$BonsaiArgs
)
Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

$bootstrapperPath = Join-Path $PSScriptRoot '.bonsai' 'Bonsai.exe'
if (-not (Test-Path $bootstrapperPath)) {
    throw "Bonsai.exe not found at $bootstrapperPath. Place the Bonsai bootstrapper in .bonsai/ next to Bonsai.config."
}

# Bonsai.exe targets .NET Framework, so only the net4x build outputs can be loaded.
$libPaths = Get-ChildItem (Join-Path $PSScriptRoot 'artifacts' 'bin' '*' "$($Configuration.ToLower())_net4*") -Directory | Select-Object -Expand FullName
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
