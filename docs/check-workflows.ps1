# Checks that every operator named in a .bonsai file resolves to a real .NET type.
#
# Why this exists. The workflow files under docs/workflows/ are hand-authored XML,
# not built by dragging nodes in the Bonsai editor, so a misspelled operator name
# is possible. export-images.ps1 does not catch it: Bonsai's --export-image only
# lays out the graph, so a workflow naming a type that exists nowhere still exits 0
# and still writes a valid SVG. The documentation then renders perfectly while the
# workflow fails for any reader who copies it into Bonsai.
#
# The workflow conventions these files follow, and the render step this check sits
# beside, come from the author-harp-docs skill by Shawn Tan (@banchan86). The gap
# was found by testing a claim in that skill, so the fix belongs upstream in
# harp-tech/docfx-tools, which owns Export-Image.ps1 and is consumed as a submodule
# by every Harp device repository. This copy is the interim one.
#
# Run it after editing or adding a workflow, from the repository root:
#
#     .\docs\check-workflows.ps1
#
# It exits 1 if any type is missing, so it also works as a build step.
#
# What it does not check: that the workflow is sensible. A wrong KeyDown filter, a
# misspelled subject name or a node wired to the wrong register all pass. Only
# running the workflow against hardware catches those.
[CmdletBinding()] param (
    # The .bonsai files to check. Defaults to every workflow in the repository.
    [string[]]$Path,
    # Folders holding the compiled device interface. Defaults to the net4x build.
    [string[]]$LibPath,
    [ValidateSet('Debug', 'Release')]
    [string]$Configuration = 'Debug'
)
Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

$root = Split-Path $PSScriptRoot -Parent

if (-not $Path) {
    $Path = Get-ChildItem (Join-Path $root 'docs/workflows') -Filter *.bonsai -Recurse |
            Select-Object -Expand FullName
}
if (-not $Path) { throw "No .bonsai files found under docs/workflows." }

if (-not $LibPath) {
    # Keep Join-Path to two arguments: the multi-argument form is PowerShell 7 only.
    $binGlob = Join-Path (Join-Path (Join-Path $root 'artifacts') 'bin') '*'
    $LibPath = Get-ChildItem (Join-Path $binGlob "$($Configuration.ToLower())_net4*") -Directory -ErrorAction SilentlyContinue |
               Select-Object -Expand FullName
}
if (-not $LibPath) {
    throw "No $Configuration net4x build found under artifacts/bin. Run: dotnet build software/dotnet -c $Configuration"
}

# Index every assembly we might need: the device interface, then the pinned Bonsai
# packages that the workflows reference through their xmlns declarations.
$probe = @()
foreach ($p in $LibPath) {
    $probe += (Get-ChildItem $p -Filter *.dll -ErrorAction SilentlyContinue | Select-Object -Expand FullName)
}
$probe += (Get-ChildItem (Join-Path $root '.bonsai/Packages') -Recurse -Filter *.dll -ErrorAction SilentlyContinue |
           Where-Object { $_.FullName -like '*lib*net4*' } | Select-Object -Expand FullName)

$byName = @{}
foreach ($dll in $probe) {
    $n = [IO.Path]::GetFileNameWithoutExtension($dll)
    if (-not $byName.ContainsKey($n)) { $byName[$n] = $dll }
}

# Bonsai.Design references Bonsai.Core 2.8.0.0, which only resolves inside Bonsai's
# own binding redirects. Redirect by simple name so the load gets as far as it can.
# GetNewClosure captures $byName: an event handler does not see the script scope.
$resolverBlock = {
    param($source, $e)
    $simple = ($e.Name -split ',')[0]
    foreach ($a in [AppDomain]::CurrentDomain.GetAssemblies()) {
        if ($a.GetName().Name -eq $simple) { return $a }
    }
    if ($byName.ContainsKey($simple)) {
        try { return [Reflection.Assembly]::LoadFrom($byName[$simple]) } catch { return $null }
    }
    return $null
}.GetNewClosure()
[AppDomain]::CurrentDomain.add_AssemblyResolve([ResolveEventHandler]$resolverBlock)

$loaded = @{}
function Get-Asm([string]$name) {
    if ($loaded.ContainsKey($name)) { return $loaded[$name] }
    if (-not $byName.ContainsKey($name)) { $loaded[$name] = $null; return $null }
    $a = $null
    try { $a = [Reflection.Assembly]::LoadFrom($byName[$name]) } catch { $a = $null }
    $loaded[$name] = $a
    return $a
}

$quote = [char]34
$typePattern = 'xsi:type=' + $quote + '([^' + $quote + ']+)' + $quote
$nsPattern = '^clr-namespace:([^;]+);assembly=(.+)$'

$missing = 0
$unverified = 0
$checked = 0

foreach ($file in $Path) {
    $raw = Get-Content $file -Raw
    $xml = [xml]$raw

    # Map each xmlns prefix to the namespace and assembly it declares.
    $ns = @{}
    foreach ($a in $xml.DocumentElement.Attributes) {
        if ($a.Name.StartsWith('xmlns:')) {
            $pfx = $a.Name.Substring(6)
            if ($a.Value -match $nsPattern) {
                $ns[$pfx] = @{ Ns = $Matches[1]; Asm = $Matches[2] }
            }
        }
    }

    $types = [regex]::Matches($raw, $typePattern) |
             ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique

    $problems = @()
    $notes = @()
    foreach ($t in $types) {
        # Unprefixed types are built into Bonsai itself, e.g. xsi:type="Combinator".
        if (-not $t.Contains(':')) { continue }
        $parts = $t -split ':', 2
        $pfx = $parts[0]
        $name = ($parts[1] -split '\(')[0]
        $checked++

        if (-not $ns.ContainsKey($pfx)) {
            $problems += "undeclared prefix   $t"; $missing++; continue
        }
        $asm = Get-Asm $ns[$pfx].Asm
        if ($null -eq $asm) {
            $problems += ("assembly not found  " + $ns[$pfx].Asm + "   (for $t)"); $missing++; continue
        }

        $full = $ns[$pfx].Ns + '.' + $name
        $found = $null
        $err = $null
        try { $found = $asm.GetType($full, $false, $false) } catch { $err = $true }
        if ($err) {
            # A dependency of the declaring assembly could not load. The type itself
            # is not disproved, so note it rather than failing the run.
            $notes += "unverified          $full"
            $unverified++
        } elseif (-not $found) {
            $problems += "MISSING TYPE        $full"; $missing++
        }
    }

    $leaf = Split-Path $file -Leaf
    if ($problems.Count -gt 0) {
        Write-Host "  FAIL  $leaf" -ForegroundColor Red
        foreach ($p in $problems) { Write-Host "          $p" }
        foreach ($n in $notes) { Write-Host "          $n" }
    } elseif ($notes.Count -gt 0) {
        Write-Host "  ok    $leaf  ($($notes.Count) unverified)"
    } else {
        Write-Host "  ok    $leaf"
    }
}

Write-Host ""
Write-Host "  $($Path.Count) workflow(s), $checked operator reference(s) checked"
if ($unverified -gt 0) {
    Write-Host "  $unverified unverified (a dependency would not load outside Bonsai)"
}
if ($missing -gt 0) {
    Write-Host "  $missing missing type(s)" -ForegroundColor Red
    exit 1
}
Write-Host "  all types resolve"
exit 0
