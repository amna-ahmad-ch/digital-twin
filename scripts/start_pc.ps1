$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
docker rm -f avatar 2>$null | Out-Null
docker build -t avatar .
docker run -d --name avatar --env-file .env -p 8000:8000 avatar
Write-Host "Avatar is running at http://localhost:8000  (admin at /admin)"
