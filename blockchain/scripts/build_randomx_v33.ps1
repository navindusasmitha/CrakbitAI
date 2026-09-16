param(
    [string]$Destination = "vendor/RandomX-v1.1.8"
)

$ErrorActionPreference = "Stop"
$Tag = "v1.1.8"

Write-Host "=== Crakbit v0.33 RandomX candidate builder ===" -ForegroundColor Cyan
Write-Host "Pinned upstream tag: $Tag"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git is required"
}
if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
    throw "cmake is required"
}

if (-not (Test-Path $Destination)) {
    git clone --depth 1 --branch $Tag https://github.com/tevador/RandomX.git $Destination
}
else {
    Push-Location $Destination
    try {
        git fetch --tags --depth 1 origin $Tag
        git checkout --detach $Tag
    }
    finally {
        Pop-Location
    }
}

$Build = Join-Path $Destination "build"
cmake -S $Destination -B $Build -DBUILD_SHARED_LIBS=ON
cmake --build $Build --config Release

$Candidates = @(
    (Join-Path $Build "Release/randomx.dll"),
    (Join-Path $Build "randomx.dll"),
    (Join-Path $Build "Release/librandomx.dll"),
    (Join-Path $Build "librandomx.dll")
)

$Library = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Library) {
    Write-Warning "Build finished but a shared RandomX DLL was not found in the expected paths."
    Write-Warning "Inspect $Build and set CRAKBIT_RANDOMX_LIBRARY to the actual shared library path."
    exit 2
}

$Resolved = (Resolve-Path $Library).Path
Write-Host "RandomX shared library: $Resolved" -ForegroundColor Green
Write-Host "Set for this PowerShell session with:"
Write-Host ('$env:CRAKBIT_RANDOMX_LIBRARY="{0}"' -f $Resolved) -ForegroundColor Yellow
Write-Host "Then verify with: crakchain pow-randomx-v33-selftest"
