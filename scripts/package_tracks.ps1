param(
    [ValidateSet("runtime", "dev", "all")]
    [string]$Track = "all",
    [switch]$SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PackagesRoot = Join-Path $ProjectRoot "packages"
$Now = Get-Date -Format "yyyyMMdd_HHmmss"

function Get-AppVersion {
    $versionFile = Join-Path $ProjectRoot "version.py"
    if (-not (Test-Path $versionFile)) {
        throw "version.py not found: $versionFile"
    }
    $line = Select-String -Path $versionFile -Pattern "__version__\s*=\s*'([^']+)'" | Select-Object -First 1
    if (-not $line) {
        throw "__version__ not found in version.py"
    }
    return $line.Matches[0].Groups[1].Value
}

function Ensure-CleanDir([string]$path) {
    if (Test-Path $path) {
        Remove-Item -Path $path -Recurse -Force
    }
    New-Item -ItemType Directory -Path $path | Out-Null
}

function Build-Runtime([string]$version) {
    if (-not $SkipBuild) {
        $buildBat = Join-Path $ProjectRoot "build_exe.bat"
        if (-not (Test-Path $buildBat)) {
            throw "build_exe.bat not found: $buildBat"
        }
        Write-Host "[runtime] build_exe.bat 실행"
        cmd /c "`"$buildBat`""
        if ($LASTEXITCODE -ne 0) {
            throw "build_exe.bat failed with exit code $LASTEXITCODE"
        }
    }

    $distDir = Join-Path $ProjectRoot "dist"
    if (-not (Test-Path $distDir)) {
        throw "dist folder not found. Run build first or remove -SkipBuild."
    }

    $runtimeOut = Join-Path $PackagesRoot "runtime"
    $runtimeStage = Join-Path $runtimeOut "stage"
    Ensure-CleanDir $runtimeStage

    Copy-Item -Path (Join-Path $distDir "*") -Destination $runtimeStage -Recurse -Force
    if (Test-Path (Join-Path $ProjectRoot "README.md")) {
        Copy-Item -Path (Join-Path $ProjectRoot "README.md") -Destination $runtimeStage -Force
    }
    if (Test-Path (Join-Path $ProjectRoot "VERSION.txt")) {
        Copy-Item -Path (Join-Path $ProjectRoot "VERSION.txt") -Destination $runtimeStage -Force
    }

    $zipPath = Join-Path $runtimeOut ("SQM_v{0}_runtime_{1}.zip" -f $version, $Now)
    if (Test-Path $zipPath) {
        Remove-Item $zipPath -Force
    }
    Compress-Archive -Path (Join-Path $runtimeStage "*") -DestinationPath $zipPath
    Remove-Item -Path $runtimeStage -Recurse -Force
    Write-Host "[runtime] package created: $zipPath"
}

function Build-Dev([string]$version) {
    $devOut = Join-Path $PackagesRoot "dev"
    $devStage = Join-Path $devOut "stage"
    Ensure-CleanDir $devStage

    $excludeRegex = @(
        "\\\.git(\\|$)",
        "\\\.venv(\\|$)",
        "\\venv(\\|$)",
        "\\__pycache__(\\|$)",
        "\\\.pytest_cache(\\|$)",
        "\\build(\\|$)",
        "\\dist(\\|$)",
        "\\packages(\\|$)",
        "\\logs(\\|$)",
        "\\output(\\|$)",
        "\\terminals(\\|$)",
        "\\agent-transcripts(\\|$)"
    )

    $all = Get-ChildItem -Path $ProjectRoot -Recurse -Force
    foreach ($item in $all) {
        $full = $item.FullName
        $rel = $full.Substring($ProjectRoot.Length).TrimStart('\')
        if ([string]::IsNullOrWhiteSpace($rel)) { continue }

        $blocked = $false
        foreach ($pattern in $excludeRegex) {
            if ($full -match $pattern) {
                $blocked = $true
                break
            }
        }
        if ($blocked) { continue }

        if ($item.PSIsContainer) {
            $targetDir = Join-Path $devStage $rel
            if (-not (Test-Path $targetDir)) {
                New-Item -ItemType Directory -Path $targetDir | Out-Null
            }
        } else {
            if ($rel -match "^data\\db\\.*\.db(-wal|-shm|-journal)?$") {
                continue
            }
            $targetFile = Join-Path $devStage $rel
            $parent = Split-Path -Parent $targetFile
            if (-not (Test-Path $parent)) {
                New-Item -ItemType Directory -Path $parent | Out-Null
            }
            Copy-Item -Path $full -Destination $targetFile -Force
        }
    }

    $zipPath = Join-Path $devOut ("SQM_v{0}_dev_{1}.zip" -f $version, $Now)
    if (Test-Path $zipPath) {
        Remove-Item $zipPath -Force
    }
    Compress-Archive -Path (Join-Path $devStage "*") -DestinationPath $zipPath
    Remove-Item -Path $devStage -Recurse -Force
    Write-Host "[dev] package created: $zipPath"
}

if (-not (Test-Path $PackagesRoot)) {
    New-Item -ItemType Directory -Path $PackagesRoot | Out-Null
}

$version = Get-AppVersion
Write-Host ("[info] version={0}, track={1}" -f $version, $Track)

switch ($Track) {
    "runtime" { Build-Runtime $version }
    "dev"     { Build-Dev $version }
    "all" {
        Build-Runtime $version
        Build-Dev $version
    }
}

Write-Host "[done] 2-track packaging completed."
