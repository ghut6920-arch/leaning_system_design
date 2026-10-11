# AI authored preparation packaging only; revision 1. Does not write learner progress.
$ErrorActionPreference = 'Stop'
$learningRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$prepRoot = Join-Path $learningRoot 'artifacts/lesson-preparation/2026-10-11-transformer-kv-cache-r1'
$questionRoot = Join-Path $learningRoot 'questions/preparation-tests/transformer-kv-cache-20261011'
$utf8 = New-Object System.Text.UTF8Encoding($false)
$baseline = @(Get-Content -LiteralPath (Join-Path $prepRoot 'protected-baseline.json') -Encoding UTF8 -Raw | ConvertFrom-Json)
$protectedRoots = @('state','sessions','goals','assessment','plan')
$currentFiles = @($protectedRoots | ForEach-Object { Get-ChildItem -LiteralPath (Join-Path $learningRoot $_) -File -Recurse })
$changed = @($baseline | Where-Object { !(Test-Path -LiteralPath $_.path) -or ((Get-FileHash -LiteralPath $_.path -Algorithm SHA256).Hash.ToLower() -ne $_.sha256) } | Select-Object -ExpandProperty path)
$setDelta = @(Compare-Object -ReferenceObject @($baseline.path) -DifferenceObject @($currentFiles.FullName))
if ($changed.Count -or $setDelta.Count) { throw 'Protected progress content or file set changed; inspect before delivery.' }
$framework = Get-Content -LiteralPath (Join-Path $learningRoot 'framework-manifest.json') -Encoding UTF8 -Raw | ConvertFrom-Json
$frameworkMismatch = @($framework.entries | Where-Object { $p=Join-Path $learningRoot $_.path; !(Test-Path -LiteralPath $p) -or ((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower() -ne $_.sha256) })
if ($frameworkMismatch.Count) { throw 'Framework fingerprints changed; inspect before delivery.' }
$sections = @(
    (Join-Path $prepRoot '00-scope-and-framework.md'),
    (Join-Path $prepRoot '03-cognitive-design.md'),
    (Join-Path $questionRoot 'visible/04-materials.md'),
    (Join-Path $questionRoot 'visible/05-continuous-work.md'),
    (Join-Path $questionRoot 'teacher-reference/06-reference.md'),
    (Join-Path $questionRoot 'backup/08-support.md'),
    (Join-Path $prepRoot '07-reverse-review.md'),
    (Join-Path $prepRoot '09-delivery-verification.md'),
    (Join-Path $prepRoot '01-disciplinary-analysis.md'),
    (Join-Path $prepRoot '02-source-register.md')
)
$parts = New-Object System.Collections.Generic.List[string]
$parts.Add("# Transformer Attention：KV Cache 与长上下文推理完整备课`n`n2026-10-11 / revision 1；供审查，未开展正式教学。`n`n主线：Attention运算 → 逐层因果不变量 → 前缀有效性与推理时序 → 资源成本 → 方案选择 → 长上下文质量与条件更新。`n`n本文件由规范原件汇编。完整教师参考随稿供审查，不要求本轮作答；学科研究与完整来源台账附于文末，原件清单与代码见同目录README。`n")
foreach ($section in $sections) {
    $body=[System.IO.File]::ReadAllText($section)
    $parts.Add("`n---`n`n" + $body)
}
$master = Join-Path $prepRoot '完整备课.md'
[System.IO.File]::WriteAllText($master, ($parts -join "`n"), $utf8)
if ([System.IO.File]::ReadAllText($master) -ne ($parts -join "`n")) { throw 'Master read-back mismatch.' }
$allFiles = @(@($prepRoot,$questionRoot,$PSScriptRoot) | ForEach-Object { Get-ChildItem -LiteralPath $_ -File -Recurse } | Where-Object { $_.Name -notin @('delivery-checks.json','delivery-manifest.json') -and $_.FullName -notmatch '[\\/]__pycache__[\\/]' })
$broken = New-Object System.Collections.Generic.List[string]
foreach ($md in @($allFiles | Where-Object Extension -eq '.md')) {
    $body = [System.IO.File]::ReadAllText($md.FullName)
    foreach ($match in [regex]::Matches($body, '!?(?:\[[^\]]*\])\(([^)]+)\)')) {
        $target = $match.Groups[1].Value.Trim('<','>')
        if ($target -match '^https?://' -or $target -match '^#') { continue }
        $target = ($target -split '#',2)[0]
        if (!$target) { continue }
        $resolved = if ([System.IO.Path]::IsPathRooted($target)) { $target } else { Join-Path $md.DirectoryName $target }
        if (!(Test-Path -LiteralPath $resolved)) { $broken.Add($md.Name + ': ' + $target) }
    }
}
$numerical = Get-Content -LiteralPath (Join-Path $prepRoot 'teacher-run/checks.json') -Encoding UTF8 -Raw | ConvertFrom-Json
$render = Get-Content -LiteralPath (Join-Path $prepRoot 'figures/render-info.json') -Encoding UTF8 -Raw | ConvertFrom-Json
$checks = [ordered]@{
    revision=1; purpose='preparation_review_only'; protected_files=$baseline.Count;
    protected_content_changes=$changed; protected_file_set_changes=$setDelta;
    framework_entries_checked=$framework.entries.Count; framework_mismatches=$frameworkMismatch;
    local_markdown_links_broken=@($broken); teacher_numeric_tolerance=$numerical.tolerance;
    learner_events_created=$false; learner_execution=$false; master_read_back=$true;
    raster_record_read=$true; raster_visual_review='performed by root via view_image; see 09';
    limitations=@('No formal teaching or learner evidence','No production GPU/HF performance or long-context quality test')
}
[System.IO.File]::WriteAllText((Join-Path $prepRoot 'delivery-checks.json'), ($checks | ConvertTo-Json -Depth 12), $utf8)
$manifest = [ordered]@{ revision=1; generated_for='preparation_review'; files=@($allFiles | Sort-Object FullName | ForEach-Object { [ordered]@{path=$_.FullName;bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower()} }); integrity_report=(Join-Path $prepRoot 'delivery-checks.json') }
[System.IO.File]::WriteAllText((Join-Path $prepRoot 'delivery-manifest.json'), ($manifest | ConvertTo-Json -Depth 8), $utf8)
$savedChecks = Get-Content -LiteralPath (Join-Path $prepRoot 'delivery-checks.json') -Encoding UTF8 -Raw | ConvertFrom-Json
if ($savedChecks.local_markdown_links_broken.Count) { throw ('Local links require repair: ' + ($savedChecks.local_markdown_links_broken -join ', ')) }
[pscustomobject]@{master=$master;files=$allFiles.Count;protected_files=$baseline.Count;framework_entries=$framework.entries.Count;broken_local_links=$broken.Count;master_bytes=(Get-Item -LiteralPath $master).Length} | ConvertTo-Json
