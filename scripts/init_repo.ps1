param(
    [string]$RemoteUrl = 'git@github.com:RicardoDavitec/ClaudiaPalooza.git',
    [switch]$Push,
    [string]$SshKeyPath = 'C:\sshkeys\id_ed25519_claudia_palooza',
    [string]$SshAgentSock = 'C:\sshkeys\ssh-agent.sock'
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

function Start-SshAgentAndAddKey {
    param(
        [string]$KeyPath,
        [string]$SockPath
    )

    if (-not (Test-Path $KeyPath)) {
        Write-Host "Chave SSH não encontrada em: $KeyPath - pulando carregamento de chave."
        return
    }

    Write-Host "Tentando iniciar ssh-agent com socket em: $SockPath"
    try {
        $env:SSH_AUTH_SOCK = $null
        $agentOutput = & ssh-agent -a $SockPath -s 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host $agentOutput
        } else {
            Write-Host "Falha ao iniciar ssh-agent via processo, tentando serviço Windows..."
            Start-Service -Name ssh-agent -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    } catch {
        Write-Host "Erro ao iniciar ssh-agent via processo: $_. Tentando serviço Windows..."
        Start-Service -Name ssh-agent -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }

    Write-Host "Adicionando chave ao agente: $KeyPath"
    try {
        & ssh-add $KeyPath
    } catch {
        Write-Host "ssh-add falhou: $_"
    }
}

if ($Push) {
    Write-Host "Preparando ambiente SSH e empurrando para o remoto (origin main)..."
    Start-SshAgentAndAddKey -KeyPath $SshKeyPath -SockPath $SshAgentSock
    git push -u origin main
} else {
    Write-Host "Rodar este script com -Push para enviar ao remoto, por exemplo:`n  .\\scripts\\init_repo.ps1 -Push`
Também é possível executar manualmente:
  git remote add origin $RemoteUrl
  git push -u origin main"
}
