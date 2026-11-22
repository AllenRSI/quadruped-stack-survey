# md2html.ps1 — 把 report.md 转成与 index.html 同风格的静态页
# 只支持本项目用到的 Markdown 子集，够用且零依赖。

param(
  [Parameter(Mandatory=$true)][string]$In,
  [Parameter(Mandatory=$true)][string]$Out,
  [string]$Title = "具身四足机器狗 · 全栈算法方案调研"
)

$ErrorActionPreference = 'Stop'
$md = [System.IO.File]::ReadAllText($In, [System.Text.Encoding]::UTF8)
$lines = $md -split "`r?`n"

function Esc([string]$s) {
  $s = $s -replace '&','&amp;'
  $s = $s -replace '<','&lt;'
  $s = $s -replace '>','&gt;'
  return $s
}

function Inline([string]$s) {
  # 先抽出 code span，避免里面的内容被其它规则改写
  $codes = @()
  $s = [regex]::Replace($s, '`([^`]+)`', {
    param($m)
    $script:codes += $m.Groups[1].Value
    "%%CODE$($script:codes.Count - 1)%%"
  })

  $s = Esc $s

  # 链接 [text](url)
  $s = [regex]::Replace($s, '\[([^\]]+)\]\(([^)\s]+)\)', '<a href="$2">$1</a>')
  # 加粗 **text**
  $s = [regex]::Replace($s, '\*\*([^*]+)\*\*', '<strong>$1</strong>')
  # 斜体 *text*（避免误伤已生成的标签属性，粗体已先处理）
  $s = [regex]::Replace($s, '(?<![\*\w])\*([^*\n]+)\*(?!\*)', '<em>$1</em>')

  # 还原 code span
  for ($i = 0; $i -lt $codes.Count; $i++) {
    $s = $s.Replace("%%CODE$i%%", "<code>" + (Esc $codes[$i]) + "</code>")
  }
  return $s
}

$html = New-Object System.Text.StringBuilder
$i = 0
$inCode = $false
$codeBuf = New-Object System.Text.StringBuilder
$inList = $false
$inOl = $false

function CloseList() {
  if ($script:inList) {
    if ($script:inOl) { [void]$script:html.AppendLine('</ol>') } else { [void]$script:html.AppendLine('</ul>') }
    $script:inList = $false
  }
}

while ($i -lt $lines.Count) {
  $ln = $lines[$i]
  $t  = $ln.Trim()

  # 代码块
  if ($t.StartsWith('```')) {
    if (-not $inCode) {
      $inCode = $true
      $codeBuf.Clear() | Out-Null
    } else {
      $inCode = $false
      [void]$html.AppendLine('<pre><code>' + (Esc $codeBuf.ToString().TrimEnd()) + '</code></pre>')
    }
    $i++; continue
  }
  if ($inCode) { [void]$codeBuf.AppendLine($ln); $i++; continue }

  # 空行
  if ($t -eq '') {
    CloseList
    $i++; continue
  }

  # 标题
  if ($t -match '^(#{1,4})\s+(.*)$') {
    CloseList
    $lvl = $Matches[1].Length
    $txt = Inline $Matches[2]
    if ($lvl -eq 1) {
      [void]$html.AppendLine("<h1>$txt</h1>")
    } else {
      $id = ($Matches[2] -replace '[^\w\u4e00-\u9fa5]+','-').Trim('-')
      [void]$html.AppendLine("<h$lvl id=`"$id`">$txt</h$lvl>")
    }
    $i++; continue
  }

  # 水平线
  if ($t -match '^---+$') { CloseList; [void]$html.AppendLine('<hr>'); $i++; continue }

  # 引用块
  if ($t -match '^>\s?(.*)$') {
    CloseList
    $buf = @()
    while ($i -lt $lines.Count -and $lines[$i].Trim() -match '^>\s?(.*)$') {
      $buf += (Inline ($lines[$i].Trim() -replace '^>\s?',''))
      $i++
    }
    [void]$html.AppendLine('<blockquote>' + ($buf -join '<br>') + '</blockquote>')
    continue
  }

  # 表格
  if ($t.StartsWith('|') -and ($i + 1) -lt $lines.Count -and $lines[$i+1].Trim() -match '^\|[\s\-:\|]+\|$') {
    CloseList
    $head = ($t.Trim('|') -split '\|') | ForEach-Object { Inline $_.Trim() }
    $i += 2
    $rows = @()
    while ($i -lt $lines.Count -and $lines[$i].Trim().StartsWith('|')) {
      $rows += ,(($lines[$i].Trim().Trim('|') -split '\|') | ForEach-Object { Inline $_.Trim() })
      $i++
    }
    [void]$html.AppendLine('<table class="tbl"><thead><tr>' + (($head | ForEach-Object { "<th>$_</th>" }) -join '') + '</tr></thead><tbody>')
    foreach ($r in $rows) {
      [void]$html.AppendLine('<tr>' + (($r | ForEach-Object { "<td>$_</td>" }) -join '') + '</tr>')
    }
    [void]$html.AppendLine('</tbody></table>')
    continue
  }

  # 有序列表
  if ($t -match '^\d+\.\s+(.*)$') {
    if (-not $inList -or -not $inOl) { CloseList; [void]$html.AppendLine('<ol>'); $inList = $true; $inOl = $true }
    [void]$html.AppendLine('<li>' + (Inline $Matches[1]) + '</li>')
    $i++; continue
  }

  # 无序列表
  if ($t -match '^[-*]\s+(.*)$') {
    if (-not $inList -or $inOl) { CloseList; [void]$html.AppendLine('<ul>'); $inList = $true; $inOl = $false }
    [void]$html.AppendLine('<li>' + (Inline $Matches[1]) + '</li>')
    $i++; continue
  }

  # 普通段落
  CloseList
  [void]$html.AppendLine('<p>' + (Inline $t) + '</p>')
  $i++
}

CloseList

$page = @"
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>$Title</title>
<style>
  :root{
    --ink:#0A0D12; --ink2:#11161F; --line:#242E3D; --text:#E4E8EF;
    --muted:#8A97AB; --dim:#5C6878; --amber:#E8B44A;
    --serif:"Noto Serif SC","Source Han Serif SC","Songti SC",Georgia,serif;
    --sans:"Inter","PingFang SC","Microsoft YaHei",-apple-system,sans-serif;
    --mono:"JetBrains Mono","SF Mono",Consolas,monospace;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--ink);color:var(--text);font-family:var(--sans);line-height:1.85;font-size:15.5px;
       background-image:radial-gradient(ellipse 900px 500px at 50% -10%, rgba(232,180,74,.06), transparent 70%);
       background-repeat:no-repeat;-webkit-font-smoothing:antialiased}
  .wrap{max-width:860px;margin:0 auto;padding:0 28px}
  nav{position:sticky;top:0;z-index:100;background:rgba(10,13,18,.88);backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
  nav .wrap{display:flex;align-items:center;gap:18px;height:54px;max-width:1120px}
  nav a{font-size:12.5px;color:var(--muted);text-decoration:none;white-space:nowrap}
  nav a:hover{color:var(--amber)}
  nav .brand{font-family:var(--mono);font-size:11px;letter-spacing:.14em;color:var(--dim)}
  nav .sp{flex:1}
  main{padding:64px 0 100px}
  h1{font-family:var(--serif);font-size:clamp(30px,4.4vw,46px);line-height:1.25;font-weight:600;margin-bottom:34px;letter-spacing:-.01em}
  h2{font-family:var(--serif);font-size:26px;font-weight:600;margin:56px 0 18px;padding-top:10px;border-top:1px solid var(--line);line-height:1.4}
  h3{font-size:17px;font-weight:600;margin:34px 0 12px;color:#fff;display:flex;align-items:center;gap:10px}
  h3::before{content:"";width:3px;height:15px;background:var(--amber);display:inline-block;flex:none}
  h4{font-size:15px;margin:24px 0 10px;color:#fff}
  p{margin-bottom:15px;color:#C3CBD8}
  strong{color:#fff;font-weight:600}
  em{color:var(--amber);font-style:normal}
  a{color:var(--amber);text-decoration:none}
  a:hover{text-decoration:underline}
  code{font-family:var(--mono);font-size:.88em;background:#1A2230;padding:2px 6px;border-radius:3px;color:#9FE8DF}
  pre{background:#11161F;border:1px solid var(--line);padding:18px 20px;overflow-x:auto;margin:18px 0;border-radius:3px}
  pre code{background:none;padding:0;color:#B8C2D2;font-size:12.8px;line-height:1.65}
  hr{border:none;border-top:1px solid var(--line);margin:44px 0}
  blockquote{border-left:2px solid var(--amber);padding:4px 0 4px 20px;margin:22px 0;color:#B8C2D2;font-size:14.5px}
  ul,ol{margin:0 0 16px 22px}
  li{margin-bottom:7px;color:#C3CBD8}
  .tbl{width:100%;border-collapse:collapse;font-size:13px;margin:14px 0 22px;display:block;overflow-x:auto}
  .tbl th{text-align:left;font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;color:var(--dim);
          padding:10px 12px;border-bottom:1px solid var(--line);text-transform:uppercase;white-space:nowrap}
  .tbl td{padding:11px 12px;border-bottom:1px solid rgba(36,46,61,.55);color:#C3CBD8;vertical-align:top;line-height:1.6}
  .tbl tr:hover td{background:rgba(26,34,48,.45)}
  .tbl td:first-child{color:#fff}
  footer{border-top:1px solid var(--line);padding:40px 0 70px;color:var(--dim);font-size:12.5px}
  @media(max-width:760px){ h2{font-size:22px} main{padding:40px 0 70px} }
</style>
</head>
<body>
<nav><div class="wrap">
  <a class="brand" href="./index.html">QUADRUPED STACK / 2026</a>
  <span class="sp"></span>
  <a href="./index.html">← 返回可视化页</a>
  <a href="./report.md">Markdown 原文</a>
</div></nav>
<main><div class="wrap">
$($html.ToString())
</div></main>
<footer><div class="wrap">
  调研时间 2026-11 · 数据以正文标注来源为准 · 预印本内容未经同行评审
</div></footer>
</body>
</html>
"@

[System.IO.File]::WriteAllText($Out, $page, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "wrote $Out ($($page.Length) chars)"
