param(
    [string]$Out = (Join-Path (Split-Path $PSScriptRoot -Parent) "kubeconfig-jenkins.yaml")
)
$ErrorActionPreference = "Stop"

if (-not (Get-Command minikube -ErrorAction SilentlyContinue)) { throw "minikube not found. Install it and reopen PowerShell." }
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) { throw "kubectl not found. Install it and reopen PowerShell." }

$status = minikube status --format "{{.Host}}" 2>$null
if ($status -ne "Running") { throw "minikube is not running. Run: minikube start --driver=docker" }

$ip = (minikube ip).Trim()
$config = kubectl config view --flatten --minify --context=minikube
if ($LASTEXITCODE -ne 0) { throw "Could not read the minikube kubeconfig." }

$config | ForEach-Object { $_ -replace 'server: https://\S+', "server: https://${ip}:8443" } |
    Set-Content -Encoding ascii -Path $Out

Write-Host "Wrote $Out (server: https://${ip}:8443)" -ForegroundColor Green
