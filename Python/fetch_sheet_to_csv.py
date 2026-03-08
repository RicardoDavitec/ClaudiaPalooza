#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baixa respostas do Google Sheets usando Service Account e salva como CSV.

Uso:
    python fetch_sheet_to_csv.py --spreadsheet-id SPREADSHEET_ID \
        --credentials credentials/service_account.json --output convidados.csv

Observações:
- Compartilhe a planilha com o e-mail da service account (ex.: your-service@...gserviceaccount.com).
- Instale dependências (veja `requirements.txt`):
    pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
"""

import argparse
import csv
import os
import sys

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except Exception as e:
    print("❌ Erro ao importar bibliotecas do Google. Instale: google-auth-oauthlib google-api-python-client")
    raise

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


def fetch_sheet_to_csv(spreadsheet_id: str, credentials_path: str, sheet_name: str | None, output: str):
    if not os.path.exists(credentials_path):
        print(f"❌ Arquivo de credenciais não encontrado: {credentials_path}")
        print("Coloque o JSON da Service Account em credentials/service_account.json e compartilhe a planilha com o e-mail da service account.")
        sys.exit(1)

    creds = service_account.Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)

    # Determinar folha (sheet) se não especificado
    if not sheet_name:
        meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = meta.get('sheets', [])
        if not sheets:
            print("❌ Nenhuma folha encontrada na planilha.")
            sys.exit(1)
        sheet_name = sheets[0]['properties']['title']
        print(f"ℹ️ Usando primeira aba: {sheet_name}")

    range_name = f"'{sheet_name}'"
    print(f"⏳ Solicitando dados: {spreadsheet_id} -> {sheet_name}")

    result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])

    if not values:
        print("⚠️ Nenhum dado retornado da planilha.")
        return

    # Salvar CSV
    with open(output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in values:
            writer.writerow(row)

    total = max(0, len(values) - 1)  # assumindo primeira linha header
    print(f"✅ Salvo {output} ({total} registros)")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Baixa Google Sheet como CSV usando Service Account')
    parser.add_argument('--spreadsheet-id', required=True, help='ID da planilha (ex: 16a4_OrUalTX5pPD43DVk...)')
    parser.add_argument('--credentials', default='credentials/service_account.json', help='Caminho para o JSON da Service Account')
    parser.add_argument('--sheet', default=None, help='Nome da aba (opcional). Se omitido, usa primeira aba')
    parser.add_argument('--output', default='convidados.csv', help='Arquivo CSV de saída')

    args = parser.parse_args()

    fetch_sheet_to_csv(args.spreadsheet_id, args.credentials, args.sheet, args.output)
