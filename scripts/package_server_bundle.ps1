param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = Get-Date -Format "yyyyMMdd.HHmmss"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$distRoot = Join-Path $repoRoot "dist\server"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$packageName = "familycut-server-$Version-$stamp"
$bundleRoot = Join-Path $distRoot $packageName
$zipPath = Join-Path $distRoot ($packageName + ".zip")

if (-not (Test-Path $distRoot)) {
    New-Item -ItemType Directory -Force -Path $distRoot | Out-Null
}

if (Test-Path $bundleRoot) {
    Remove-Item -Recurse -Force $bundleRoot
}
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

New-Item -ItemType Directory -Force -Path $bundleRoot | Out-Null

Copy-Item -Recurse -Force (Join-Path $repoRoot "backend") (Join-Path $bundleRoot "backend")
Copy-Item -Recurse -Force (Join-Path $repoRoot "admin-web") (Join-Path $bundleRoot "admin-web")
Copy-Item -Recurse -Force (Join-Path $repoRoot "docs") (Join-Path $bundleRoot "docs")
Copy-Item -Force (Join-Path $repoRoot "README.md") (Join-Path $bundleRoot "README.md")
Copy-Item -Force (Join-Path $repoRoot "deploy\fnos\docker-compose.yml") (Join-Path $bundleRoot "docker-compose.yml")
Copy-Item -Force (Join-Path $repoRoot "deploy\fnos\.env") (Join-Path $bundleRoot ".env")
Copy-Item -Force (Join-Path $repoRoot "deploy\fnos\.env.example") (Join-Path $bundleRoot ".env.example")

Get-ChildItem -Path $bundleRoot -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $bundleRoot -Recurse -Directory | Where-Object {
    ($_.Name -in @("node_modules", "dist", "build", ".gradle", ".pytest_cache", ".ruff_cache", ".mypy_cache", "data")) `
        -or ($_.Name -like "*.egg-info") `
        -or ($_.FullName -like "*\deploy\*")
} | Remove-Item -Recurse -Force

$envExamplePath = Join-Path $bundleRoot ".env.example"
$envPath = Join-Path $bundleRoot ".env"

foreach ($targetPath in @($envExamplePath, $envPath)) {
    $envLines = Get-Content $targetPath
    $updatedLines = foreach ($line in $envLines) {
        if ($line -match '^APP_VERSION=') {
            "APP_VERSION=$Version"
        }
        elseif ($line -match '^BUILD_STAMP=') {
            "BUILD_STAMP=packaged"
        }
        else {
            $line
        }
    }
    Set-Content -Path $targetPath -Value $updatedLines -Encoding UTF8
}

Compress-Archive -Path $bundleRoot -DestinationPath $zipPath -Force

$keepCount = 2
$packageDirs = Get-ChildItem -Path $distRoot -Directory | Where-Object { $_.Name -like "familycut-server-*" } | Sort-Object LastWriteTime -Descending
if ($packageDirs.Count -gt $keepCount) {
    $packageDirs | Select-Object -Skip $keepCount | Remove-Item -Recurse -Force
}

$packageZips = Get-ChildItem -Path $distRoot -File -Filter "familycut-server-*.zip" | Sort-Object LastWriteTime -Descending
if ($packageZips.Count -gt $keepCount) {
    $packageZips | Select-Object -Skip $keepCount | Remove-Item -Force
}

Write-Output $bundleRoot
Write-Output $zipPath
