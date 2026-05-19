$ErrorActionPreference = "Stop"

$androidRoot = "C:\Android"
$preDownloadedZip = "C:\AndroidInstall\commandlinetools-win.zip"
$tempZip = if (Test-Path $preDownloadedZip) { $preDownloadedZip } else { Join-Path $env:TEMP ("commandlinetools-win-" + [guid]::NewGuid().ToString() + ".zip") }
$tempExtract = "C:\Users\CZ\Downloads\android-cmdline-tools-temp"
$javaHome = "C:\Program Files\Microsoft\jdk-17.0.18.8-hotspot"

New-Item -ItemType Directory -Force -Path $androidRoot | Out-Null
if (Test-Path $tempExtract) {
    Remove-Item -Recurse -Force $tempExtract
}
New-Item -ItemType Directory -Force -Path $tempExtract | Out-Null

if (-not (Test-Path $tempZip)) {
    Start-BitsTransfer -Source "https://edgedl.me.gvt1.com/android/repository/commandlinetools-win-14742923_latest.zip" -Destination $tempZip
}
Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force

New-Item -ItemType Directory -Force -Path "$androidRoot\cmdline-tools" | Out-Null
if (Test-Path "$androidRoot\cmdline-tools\latest") {
    Remove-Item -Recurse -Force "$androidRoot\cmdline-tools\latest"
}
Move-Item "$tempExtract\cmdline-tools" "$androidRoot\cmdline-tools\latest"

[Environment]::SetEnvironmentVariable("ANDROID_HOME", $androidRoot, "User")
[Environment]::SetEnvironmentVariable("ANDROID_SDK_ROOT", $androidRoot, "User")

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$entries = @()
if ($userPath) {
    $entries = $userPath -split ";" | Where-Object { $_ -ne "" }
}

foreach ($pathEntry in @("$androidRoot\cmdline-tools\latest\bin", "$androidRoot\platform-tools")) {
    if ($entries -notcontains $pathEntry) {
        $entries += $pathEntry
    }
}

[Environment]::SetEnvironmentVariable("Path", ($entries -join ";"), "User")

$env:JAVA_HOME = $javaHome
$env:Path = "$javaHome\bin;$androidRoot\cmdline-tools\latest\bin;$androidRoot\platform-tools;C:\Program Files\nodejs;C:\Program Files\Git\cmd;" + $env:Path

$acceptAll = 1..80 | ForEach-Object { "y" }
$acceptAll | & "$androidRoot\cmdline-tools\latest\bin\sdkmanager.bat" --sdk_root="$androidRoot" --licenses
& "$androidRoot\cmdline-tools\latest\bin\sdkmanager.bat" --sdk_root="$androidRoot" "platform-tools" "platforms;android-35" "build-tools;35.0.0"

if (($tempZip -ne $preDownloadedZip) -and (Test-Path $tempZip)) {
    Remove-Item -Force $tempZip
}

Write-Output "Android command-line SDK installed."
