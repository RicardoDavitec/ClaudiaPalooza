#!/usr/bin/env python3
"""
Upload CSV para uma aba do Google Sheet (substitui todo o conteúdo da aba).

Uso:
  python upload_csv_to_sheet.py --spreadsheet-id ID --arquivo convidados_teste.csv
"""
import argparse
import csv
import os
import sys
from pathlib import Path

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except Exception:
    print('Erro: instale google-auth e google-api-python-client')
    raise


def read_csv_rows(path):
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        r = csv.reader(f)
        for row in r:
            rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--spreadsheet-id', required=True)
    parser.add_argument('--arquivo', required=True)
    parser.add_argument('--credentials', default='credentials/service_account.json')
    parser.add_argument('--sheet', default=None)
    args = parser.parse_args()

    if not os.path.exists(args.arquivo):
        print('Arquivo CSV não encontrado:', args.arquivo)
        sys.exit(1)

    creds = service_account.Credentials.from_service_account_file(args.credentials, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    # ler CSV
    values = read_csv_rows(args.arquivo)

    # se sheet não fornecido, usar primeira aba
    sheet_name = args.sheet
    if not sheet_name:
        meta = service.spreadsheets().get(spreadsheetId=args.spreadsheet_id).execute()
        sheets = meta.get('sheets', [])
        if not sheets:
            print('Planilha sem abas')
            sys.exit(1)
        sheet_name = sheets[0]['properties']['title']

    range_name = f"'{sheet_name}'!A1"
    body = {'values': values}
    service.spreadsheets().values().clear(spreadsheetId=args.spreadsheet_id, range=f"'{sheet_name}'").execute()
    service.spreadsheets().values().update(spreadsheetId=args.spreadsheet_id, range=range_name, valueInputOption='RAW', body=body).execute()
    print(f'✅ CSV {args.arquivo} enviado para planilha {args.spreadsheet_id} aba {sheet_name} ({len(values)-1} registros)')


if __name__ == '__main__':
    main()
