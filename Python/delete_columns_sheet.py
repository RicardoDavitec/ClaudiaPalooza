#!/usr/bin/env python3
from google.oauth2 import service_account
from googleapiclient.discovery import build
import sys

SPREADSHEET_ID = '16a4_OrUalTX5pPD43DVkqiGhopP85mN4dEsh3m3wC30'
SHEET_NAME = 'Respostas ao formulário 1'
CREDENTIALS='credentials/service_account.json'

creds = service_account.Credentials.from_service_account_file(CREDENTIALS, scopes=['https://www.googleapis.com/auth/spreadsheets'])
service = build('sheets','v4',credentials=creds)

meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID, includeGridData=False).execute()
sheet_id = None
for s in meta.get('sheets',[]):
    props = s.get('properties',{})
    if props.get('title') == SHEET_NAME:
        sheet_id = props.get('sheetId')
        break
if sheet_id is None:
    print('Sheet not found')
    sys.exit(1)

# print current header
res = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"'{SHEET_NAME}'!1:1").execute()
header = res.get('values',[[]])[0]
print('Antes - cabeçalho:')
for i,h in enumerate(header, start=1):
    # column letters
    n=i
    s=''
    while n>0:
        n,rem = divmod(n-1,26)
        s = chr(65+rem)+s
    print(f"{i:02d} {s} -> {h}")

to_delete = [(13,14),(12,13),(11,12)]  # delete N, M, L in this order
# Columns to remove visually: try to delete, but if sheet contains form data Google disallows delete.
# Safer approach: hide the columns L (12), M (13), N (14) instead of deleting.
to_hide = [(11,12),(12,13),(13,14)]  # L,M,N as 0-based ranges (startIndex,endIndex)
requests = []
for start,end in to_hide:
    requests.append({
        'updateDimensionProperties': {
            'range': {
                'sheetId': sheet_id,
                'dimension': 'COLUMNS',
                'startIndex': start,
                'endIndex': end
            },
            'properties': {
                'hiddenByUser': True
            },
            'fields': 'hiddenByUser'
        }
    })

body = {'requests': requests}
resp = service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
print('\nColunas L,M,N ocultadas (hidden).')

# print updated header
res2 = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"'{SHEET_NAME}'!1:1").execute()
header2 = res2.get('values',[[]])[0]
print('\nDepois - cabeçalho:')
for i,h in enumerate(header2, start=1):
    n=i
    s=''
    while n>0:
        n,rem = divmod(n-1,26)
        s = chr(65+rem)+s
    print(f"{i:02d} {s} -> {h}")

print('\nPronto.')
