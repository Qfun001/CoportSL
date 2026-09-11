$ErrorActionPreference = "Stop"

$desktopRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$projectRoot = (Resolve-Path (Join-Path $desktopRoot "..")).Path
$output = Join-Path $projectRoot "build\desktop\workers"
$build = Join-Path $projectRoot "build\desktop\workers-cmake"

$cmakeCommand = Get-Command cmake.exe -ErrorAction SilentlyContinue
if ($cmakeCommand) {
    $cmake = $cmakeCommand.Source
}
else {
    $cmake = Join-Path ${env:ProgramFiles} (
        "Microsoft Visual Studio\2022\Community\Common7\IDE\" +
        "CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe")
    if (-not (Test-Path -LiteralPath $cmake)) {
        throw "CMake was not found in PATH or the Visual Studio Community installation."
    }
}

New-Item -ItemType Directory -Path $output -Force | Out-Null
$targets = @(
    @{ Target = "GRRT"; Name = "GRRTWorker.exe"; App = "grrt" },
    @{ Target = "Flux"; Name = "FluxWorker.exe"; App = "flux" },
    @{ Target = "Benchmark"; Name = "BenchmarkWorker.exe"; App = "benchmark" }
)

& $cmake -S $desktopRoot -B $build -A x64
if ($LASTEXITCODE -ne 0) {
    throw "Worker CMake configuration failed."
}
foreach ($target in $targets) {
    & $cmake --build $build --config Release --target $target.Target --parallel 1
    if ($LASTEXITCODE -ne 0) {
        throw "Worker build failed: $($target.App)"
    }
    $binary = Join-Path $build "bin\Release\$($target.Target).exe"
    $actual = (& $binary --show-app).Trim()
    if ($actual -ne $target.App) {
        throw "Worker type mismatch: expected $($target.App), got $actual"
    }
    Copy-Item -LiteralPath $binary -Destination (Join-Path $output $target.Name) -Force
}

Get-ChildItem -LiteralPath $output -Filter "*Worker.exe" |
    Select-Object Name, Length, LastWriteTime
