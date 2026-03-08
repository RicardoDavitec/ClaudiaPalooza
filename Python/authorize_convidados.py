#!/usr/bin/env python3
"""
Script para o organizador autorizar convidados diretamente na Google Sheet.

Uso:
  python authorize_convidados.py --spreadsheet-id ID --emails a@e.com,b@e.com
  python authorize_convidados.py --spreadsheet-id ID --arquivo convidados_para_autorizar.csv

O script adiciona a coluna `Autorizado` (se não existir) e marca 'Sim' nas linhas com email correspondente.
"""

import argparse
import csv
import os
import sys
from pathlib import Path

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except Exception:
    print('Erro: bibliotecas Google não instaladas. Execute: pip install google-api-python-client google-auth')
    raise


def load_emails_from_csv(path):
    emails = []
    with open(path, 'r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            e = row.get('email') or row.get('Email') or row.get('E-mail')
            if e:
                emails.append(e.strip().lower())
    return emails


def index_to_col(n: int) -> str:
    # 1-based index to Excel-style column letters
    result = ''
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--left-insert', action='store_true', help='Inserir coluna Autorizado à esquerda (compatibilidade antiga)')
    parser.add_argument('--spreadsheet-id', required=True)
    parser.add_argument('--credentials', default='credentials/service_account.json')
    parser.add_argument('--sheet', default='Respostas ao formulário 1')
    parser.add_argument('--left-insert', action='store_true', help='Inserir coluna Autorizado à esquerda (compatibilidade antiga)')
    parser.add_argument('--emails', help='Lista separada por vírgula de emails para autorizar')
    parser.add_argument('--arquivo', help='CSV com coluna email para autorizar')
    args = parser.parse_args()

    creds_path = Path(args.credentials)
    if not creds_path.exists():
        print(f'Credenciais não encontradas: {creds_path}')
        sys.exit(1)

    emails = []
    if args.emails:
        emails = [e.strip().lower() for e in args.emails.split(',') if e.strip()]
    if args.arquivo:
        emails += load_emails_from_csv(args.arquivo)

    if not emails:
        print('Nenhum email fornecido para autorizar')
        sys.exit(1)

    creds = service_account.Credentials.from_service_account_file(str(creds_path), scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    sheet_name = args.sheet
    sid = args.spreadsheet_id

    # Ler planilha
    res = service.spreadsheets().values().get(spreadsheetId=sid, range=f"'{sheet_name}'").execute()
    values = res.get('values', [])
    if not values:
        print('Planilha vazia')
        sys.exit(1)

    header = values[0]
    # localizar colunas
    email_col = None
    autorizado_col = None
    for i, h in enumerate(header):
        if not h:
            continue
        key = h.strip().lower()
        if 'email' in key:
            email_col = i
        if 'autoriz' in key or 'autor' in key:
            autorizado_col = i

    if email_col is None:
        print('Não foi possível localizar coluna de email na planilha')
        sys.exit(1)

    # se não existir coluna Autorizado, adicionar ao header
    modified = False
    if autorizado_col is None:
        # Inserir coluna: por padrão adicionar ao final (não desloca colunas do Form).
        # Para compatibilidade com a versão antiga, use --left-insert para inserir na posição 0.
        if args.left_insert:
            meta = service.spreadsheets().get(spreadsheetId=sid, includeGridData=False).execute()
            sheet_id = None
            for s in meta.get('sheets', []):
                props = s.get('properties', {})
                if props.get('title') == sheet_name:
                    sheet_id = props.get('sheetId')
                    break
            if sheet_id is None:
                print('Não foi possível localizar sheetId para inserir coluna')
                sys.exit(1)

            # Inserir dimensão (coluna) na posição 0
            requests = [
                {
                    'insertDimension': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 0,
                            'endIndex': 1
                        },
                        'inheritFromBefore': False
                    }
                }
            ]
            service.spreadsheets().batchUpdate(spreadsheetId=sid, body={'requests': requests}).execute()
            # após inserção, atualizar header local
            res2 = service.spreadsheets().values().get(spreadsheetId=sid, range=f"'{sheet_name}'").execute()
            values = res2.get('values', [])
            header = values[0]
            # garantir que a primeira coluna tenha o header correto
            header[0] = 'Autorizado'
            modified = True
        else:
            # modo seguro: acrescentar coluna ao final do header local e depois escrever
            header.append('Autorizado')
            modified = True

    if modified:
        body = {'values': [header]}
        service.spreadsheets().values().update(spreadsheetId=sid, range=f"'{sheet_name}'!1:1", valueInputOption='RAW', body=body).execute()
        # recarregar valores
        res = service.spreadsheets().values().get(spreadsheetId=sid, range=f"'{sheet_name}'").execute()
        values = res.get('values', [])
        header = values[0]
        for i, h in enumerate(header):
            if 'autoriz' in (h or '').lower() or 'autor' in (h or '').lower():
                autorizado_col = i
                break
        # preencher com 'Não' por padrão (linhas existentes)
        if autorizado_col is not None:
            updates = []
            for row_idx, row in enumerate(values[1:], start=2):
                # se já houver valor, pular
                if autorizado_col < len(row) and row[autorizado_col].strip():
                    continue
                col_letter = index_to_col(autorizado_col + 1)
                updates.append({'range': f"'{sheet_name}'!{col_letter}{row_idx}", 'values': [['Não']]})
            if updates:
                service.spreadsheets().values().batchUpdate(spreadsheetId=sid, body={'valueInputOption': 'RAW', 'data': updates}).execute()

    # preparar batch update para marcar 'Sim'
    updates = []
    for row_idx, row in enumerate(values[1:], start=2):
        if email_col < len(row):
            e = row[email_col].strip().lower()
        else:
            e = ''
        if e in emails:
            start_col = autorizado_col + 1
            col_letter = index_to_col(start_col)
            range_a1 = f"'{sheet_name}'!{col_letter}{row_idx}"
            updates.append({'range': range_a1, 'values': [['Sim']]})

    if updates:
        body = {'valueInputOption': 'RAW', 'data': updates}
        service.spreadsheets().values().batchUpdate(spreadsheetId=sid, body=body).execute()
        print(f'Autorizados {len(updates)} convidados')
    else:
        print('Nenhum email correspondente encontrado para autorizar')

    # Adicionar filtro básico na planilha para a coluna 'Autorizado'
    try:
        meta = service.spreadsheets().get(spreadsheetId=sid, includeGridData=False).execute()
        sheet_id = None
        for s in meta.get('sheets', []):
            props = s.get('properties', {})
            if props.get('title') == sheet_name:
                sheet_id = props.get('sheetId')
                break
        if sheet_id is not None and autorizado_col is not None:
            # definir range do filtro: todas as colunas do header
            end_col = len(header)
            req = {
                'requests': [
                    {
                        'setBasicFilter': {
                            'filter': {
                                'range': {
                                    'sheetId': sheet_id,
                                    'startRowIndex': 0,
                                    'endRowIndex': len(values),
                                    'startColumnIndex': 0,
                                    'endColumnIndex': end_col
                                }
                            }
                        }
                    }
                ]
            }
            service.spreadsheets().batchUpdate(spreadsheetId=sid, body=req).execute()
            print('Filtro básico adicionado na planilha (coluna Autorizado)')
    except Exception:
        pass


if __name__ == '__main__':
    main()
