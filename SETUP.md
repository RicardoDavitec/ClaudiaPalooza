ClaudiaPalooza — Instruções de setup

1) Criar e ativar ambiente virtual (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r requirements.txt
```

2) Observações importantes:
- Seu Python é 3.14.3 — compatível com dependências, ok.
- `pyzbar` requer a biblioteca nativa `zbar`. No Windows, instale via chocolately ou use wheels precompiladas.

3) Google Sheets/Google APIs:
- Para integração automatizada, crie uma Service Account no Google Cloud, baixe o JSON e compartilhe a planilha com o e‑mail da service account.
- Coloque o JSON em `credentials/service_account.json` e siga os scripts que criaremos para usar as APIs.

4) Testes iniciais:
- Para gerar QR codes de teste, execute:

```powershell
python Python\gerar_qrcodes.py
```

- Para testar validação manual:

```powershell
python Python\validar_checkin.py --modo manual
```

5) Próximos passos sugeridos:
- Configurar Google Sheets (Service Account) — recomendo que façamos juntos.
- Gerar um script `fetch_sheet_to_csv.py` que baixa respostas e cria `convidados.csv`.
6) Novas flags e automações adicionadas (resumo de desenvolvimento)

- `Python/gerar_qrcodes.py`:
	- `--incremental`: processa apenas convidados novos (pula emails já presentes em `qrcodes/registro_qrcodes.json`).
	- `--batch-size N`: processa em lotes de N convidados (útil para testes e controle de carga).
	- `--limit N`: limita o número total de convidados processados.
	- `--dry-run`: simula a execução sem gravar imagens nem exportar registros.

- `Python/persistir_qrcodes.py`:
	- `--auto-generate`: gera QRs faltantes automaticamente antes de persistir na planilha.
	- `--retries`, `--backoff-base`, `--backoff-max`: retry/backoff para chamadas à Google Sheets API com jitter.
	- `--send-method email|whatsapp|sms`: após persistir, opcionalmente envia convites usando os scripts existentes.
	- `--send-dry-run`: simula o envio (não envia realmente).
	- `--send-batch-size`: controla o tamanho dos lotes enviados.
	- Limpeza automática de CSVs temporários gerados para envio.

- `Python/authorize_convidados.py`:
	- Script usado pelo organizador para marcar convidados como autorizados diretamente na planilha.
	- Uso: `python Python/authorize_convidados.py --spreadsheet-id <ID> --emails a@x.com,b@y.com` ou `--arquivo lista.csv`.
	- Garante criação da coluna `Autorizado` e escreve `Sim` nas linhas correspondentes.

7) Sugestão de fluxo operacional (modo seguro):

- 1) Executar `fetch_sheet_to_csv.py` para sincronizar a aba do Forms.
- 2) Rodar `Python/gerar_qrcodes.py convidados_normalizado.csv --incremental --batch-size 50` (ou `--dry-run` primeiro).
- 3) Rodar `Python/persistir_qrcodes.py --spreadsheet-id <ID> --auto-generate --retries 3 --send-method email --send-dry-run --send-batch-size 50` para persistir códigos e simular envio.
- 4) Após validação, repetir com `--send-dry-run` removido para envio real.

Adicionei logs básicos em `qrcodes/persist_log.txt` e `qrcodes/relatorio_geracao.txt` (relatório do gerador). Atualize `SETUP.md` conforme necessário.
