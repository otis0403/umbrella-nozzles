$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$state = Get-Content -Raw -Encoding UTF8 .\pipeline_state.json | ConvertFrom-Json
$historyFile = Get-ChildItem -LiteralPath .\cfd -Directory | ForEach-Object { Get-Item -LiteralPath (Join-Path $_.FullName 'history.json') -ErrorAction SilentlyContinue } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$last = (Get-Content -Raw -Encoding UTF8 -LiteralPath $historyFile.FullName | ConvertFrom-Json)[-1]
$step = if ($null -ne $last.batch) { $last.batch } else { $last.outer }
[ordered]@{phase=$state.phase;case=$historyFile.Directory.Name;step=$step;elapsed_s=[math]::Round($last.elapsed_s);inlet_total_pressure_Pa=[math]::Round($last.ptin,2)} | ConvertTo-Json -Compress
