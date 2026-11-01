# Prepara a pasta do AnyHelp como repositório Git e envia para o GitHub.
#
#   cd C:\Users\thais\Desktop\projects\AnyHelp
#   powershell -ExecutionPolicy Bypass -File scripts\preparar-repositorio.ps1 -Repo https://github.com/SUA-ORG/anyhelp.git
#
# O que faz:
#   1. move _github\  ->  .github\   (workflows do GitHub Actions)
#   2. git init, commit inicial e push para o repositório informado
param(
  [Parameter(Mandatory = $true)][string]$Repo
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (Test-Path "_github") {
  New-Item -ItemType Directory -Force -Path ".github\workflows" | Out-Null
  Get-ChildItem "_github\workflows\*.yml" | ForEach-Object {
    Move-Item -Force $_.FullName ".github\workflows\$($_.Name)"
  }
  Remove-Item -Recurse -Force "_github"
  Write-Host "Workflows movidos para .github\workflows" -ForegroundColor Cyan
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "Git não encontrado. Instale em https://git-scm.com/download/win e rode de novo."
}

if (-not (Test-Path ".git")) { git init | Out-Null }
git add .
git commit -m "AnyHelp: projeto inicial" | Out-Null
git branch -M main
if (git remote | Select-String -Quiet "^origin$") { git remote set-url origin $Repo } else { git remote add origin $Repo }
git push -u origin main

Write-Host ""
Write-Host "Pronto. Agora cadastre ANYHELP_SERVER e ANYHELP_KEY em:" -ForegroundColor Cyan
Write-Host "  $($Repo -replace '\.git$','')/settings/variables/actions"
