# ClaudiaPalooza

Repositório para gerenciamento de convites, geração de QR codes e controle de check-in do evento "ClaudiaPalooza".

Resumo rápido
- Scripts principais em `Python/`
- Arquivos de configuração: `requirements.txt`, `credentials/service_account.json` (não comitar)
- Pasta `qrcodes/` contém saídas (registradas em `.gitignore`)

Guia rápido

1. Criar e ativar ambiente virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Preparar credenciais
- Colocar o arquivo do service account em `credentials/service_account.json` (essa pasta está em `.gitignore`).

3. Fluxo habitual
- Baixar respostas do Form: `Python/fetch_sheet_to_csv.py --spreadsheet-id <ID> --sheet "Respostas ao formulário 1"`
- Normalizar CSV: `Python/normalize_convidados.py --input convidados.csv --output convidados_normalizado.csv`
- Gerar QRs (dry-run): `python Python/gerar_qrcodes.py convidados_normalizado.csv ./qrcodes --dry-run`
- Persistir códigos (dry-run): `python Python/persistir_qrcodes.py --spreadsheet-id <ID> --sheet Processamento --registro qrcodes/registro_qrcodes.json --dry-run`

Boas práticas e segurança
- NÃO comitar `credentials/` nem o service account.
- Use a aba `Processamento` para colunas de controle (`Autorizado`, `Codigo_*`, colunas de envio).
- Sempre rodar `--dry-run` antes de persistir/escrever em produção.
- Backup: exporte a aba de respostas antes de ações de escrita.

Estrutura do repositório

- `Python/` — scripts principais
- `credentials/` — credenciais (ignoradas)
- `qrcodes/` — saída (ignorada)
- `convidados_*.csv` — CSVs de trabalho

Como contribuir
- Veja `CONTRIBUTING.md` para orientações.
# ClaudiaPalooza
