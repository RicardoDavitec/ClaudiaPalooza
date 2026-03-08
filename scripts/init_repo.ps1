param(
    [string]$RemoteUrl = 'git@github.com:RicardoDavitec/ClaudiaPalooza.git',
    [switch]$Push
)

Write-Host "== Inicializando repositório local ClaudiaPalooza =="

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git não encontrado no PATH. Instale o Git antes de prosseguir."
    exit 1
}

if (-not (Test-Path .git)) {
    git init
    git checkout -b main
    Write-Host "Repositório Git inicializado (branch: main)"
} else {
    Write-Host ".git já existe — pulando git init"
}

git add .
try {
    git commit -m "chore: repository scaffold (README, .gitignore, CI)"
} catch {
    Write-Host "Nenhum commit criado (possível que não haja mudanças a commitar)."
}

git remote remove origin -ErrorAction SilentlyContinue
git remote add origin $RemoteUrl
Write-Host "Remote origin definido para: $RemoteUrl"

if ($Push) {
    Write-Host "Empurrando para o remoto (origin main)..."
    git push -u origin main
} else {
    Write-Host "Rodar este script com -Push para enviar ao remoto, por exemplo:`n  .\\scripts\\init_repo.ps1 -Push`
Também é possível executar manualmente:
  git remote add origin $RemoteUrl
  git push -u origin main"
}
