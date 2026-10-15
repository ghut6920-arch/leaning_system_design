param(
    [Parameter(Mandatory = $true)][string]$Workspace,
    [string]$ControlProjection,
    [ValidateSet('shadow', 'run')][string]$Mode = 'shadow',
    [int]$MaxSeconds = 3600,
    [switch]$StopWhenDone
)
$ErrorActionPreference = 'Stop'
$resolvedWorkspace = (Resolve-Path -LiteralPath $Workspace).Path
$runtimeScript = Join-Path $PSScriptRoot 'coordinate_runtime.py'
$pythonCommand = (Get-Command python -ErrorAction Stop).Source
$metaDirectory = Join-Path $resolvedWorkspace '.coordinator'
if (-not (Test-Path -LiteralPath (Join-Path $metaDirectory 'records.sqlite3'))) {
    throw '协调数据库尚未初始化；此入口不自动初始化或接管旧任务。'
}
$runDirectory = Join-Path $metaDirectory ('supervisor-runs/' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $runDirectory -Force | Out-Null
$readyFile = Join-Path $runDirectory 'ready.json'
$stdoutFile = Join-Path $runDirectory 'stdout.json'
$stderrFile = Join-Path $runDirectory 'stderr.txt'
$arguments = @('-B', '-X', 'utf8', $runtimeScript, '--workspace', $resolvedWorkspace)
if ($ControlProjection) { $arguments += @('--control-projection', (Resolve-Path -LiteralPath $ControlProjection).Path) }
$arguments += @($Mode, '--max-seconds', "$MaxSeconds", '--ready-file', $readyFile)
if ($StopWhenDone) { $arguments += '--stop-when-done' }
# Windows paths cannot contain quotes. Quote every argv element so spaces in
# workspace or bundled Python paths survive Start-Process's command-line join.
if ($arguments | Where-Object { $_.Contains('"') }) { throw '参数含非法引号。' }
$quotedArguments = $arguments | ForEach-Object { '"' + $_ + '"' }
$process = Start-Process -FilePath $pythonCommand -ArgumentList $quotedArguments -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile
$deadline = [datetime]::UtcNow.AddSeconds(15)
while ([datetime]::UtcNow -lt $deadline) {
    if (Test-Path -LiteralPath $readyFile) {
        $receipt = Get-Content -LiteralPath $readyFile -Raw | ConvertFrom-Json
        if ($receipt.status -eq 'ready' -and $receipt.pid -eq $process.Id) {
            [pscustomobject]@{ status = 'ready'; mode = $Mode; pid = $process.Id; instance_id = $receipt.instance_id; run_directory = $runDirectory } | ConvertTo-Json
            exit 0
        }
    }
    if ($process.HasExited) { throw "后台启动失败。诊断文件：$stderrFile；结果：$stdoutFile" }
    Start-Sleep -Milliseconds 200
}
throw "未取得监听就绪回执；请检查 $runDirectory，不能再次盲目启动。"
