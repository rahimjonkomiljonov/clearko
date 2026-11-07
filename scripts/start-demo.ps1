# Start the ClearKo demo backend on this PC and open a public tunnel to it.
#   powershell -ExecutionPolicy Bypass -File scripts\start-demo.ps1
# Needs: backend\.venv with the project installed, ClearKo\.env with LLM_API_KEY, and cloudflared
#        (winget install Cloudflare.cloudflared). Nothing here contains a secret.
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root "backend\.venv\Scripts\python.exe"
$cf = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$log = Join-Path $env:TEMP "clearko-tunnel.log"

Start-Process -FilePath $py -ArgumentList "-m","uvicorn","app.api.main:app","--port","8000" `
    -WorkingDirectory (Join-Path $root "backend") -WindowStyle Minimized
Start-Process -FilePath $cf -ArgumentList "tunnel","--url","http://localhost:8000","--no-autoupdate" `
    -RedirectStandardError $log -WindowStyle Minimized

Write-Host "Waiting for the tunnel address..."
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    $m = Select-String -Path $log -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($m) { break }
}
if ($m) {
    $url = $m.Matches[0].Value
    Write-Host "Backend tunnel: $url"
    Write-Host "The quick-tunnel address changes every time. If it differs from the one baked into the Vercel"
    Write-Host "site (NEXT_PUBLIC_API_URL), set the new value in Vercel and redeploy, or ask Claude to do it."
} else {
    Write-Host "No tunnel address found yet: see $log"
}
