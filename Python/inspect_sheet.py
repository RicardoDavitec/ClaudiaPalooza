#!/usr/bin/env python3
from google.oauth2 import service_account
from googleapiclient.discovery import build
from pathlib import Path
import sys

creds_path = Path('credentials/service_account.json')
if not creds_path.exists():
    print('Credenciais não encontradas')
    sys.exit(1)

creds = service_account.Credentials.from_service_account_file(str(creds_path), scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
service = build('sheets', 'v4', credentials=creds)
spreadsheet_id = '16a4_OrUalTX5pPD43DVkqiGhopP85mN4dEsh3m3wC30'
sheet = "Respostas ao formulário 1"
res = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=f"'{sheet}'").execute()
vals = res.get('values', [])
if not vals:
    print('nenhum dado')
    sys.exit(0)

print('CABEÇALHO:')
print(vals[0])
print('\nPRIMEIRAS 5 LINHAS:')
for r in vals[1:6]:
    print(r)
