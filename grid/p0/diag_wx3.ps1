$ErrorActionPreference='Continue'
$paths = @("C:\Program Files\Google\Chrome\Application\chrome.exe",
           "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
           "C:\Program Files\Microsoft\Edge\Application\msedge.exe")
$exe = $paths | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $exe) { Write-Output "NO_BROWSER"; exit 0 }
Write-Output ("EXE=" + $exe)
$url = "https://weixin.sogou.com/weixin?type=2&query=%E8%99%9A%E6%8B%9F%E8%AF%95%E7%A9%BF%20%E8%90%BD%E5%9C%B0&s_from=input"
$out = "C:\p0\dom3.html"
$p = Start-Process $exe -Wait -PassThru -NoNewWindow -ArgumentList @(
  "--headless=new","--disable-gpu","--no-sandbox","--virtual-time-budget=10000","--timeout=15000","--dump-dom",$url
) -RedirectStandardOutput $out -RedirectStandardError "C:\p0\dom3.err"
$c = Get-Content $out -Raw -ErrorAction SilentlyContinue
if (-not $c) { $c = "" }
Write-Output ("exit=" + $p.ExitCode + " len=" + $c.Length + " txtbox=" + ([regex]::Matches($c,'txt-box').Count) + " link=" + ([regex]::Matches($c,'weixin\.sogou\.com/link').Count))
if ($c.Length -gt 0) {
  $t = [regex]::Match($c, '<title>(.*?)</title>').Groups[1].Value
  Write-Output ("title=" + $t)
  $m = [regex]::Matches($c, 'title"[^>]*>([^<]{8,80})<') | Select-Object -First 3 | ForEach-Object { $_.Groups[1].Value }
  Write-Output ("samples=" + ($m -join " | "))
}
