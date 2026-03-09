#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Persistir QR codes gerados de volta na Google Sheet.

Uso:
  python persistir_qrcodes.py --spreadsheet-id SPREADSHEET_ID \
      --credentials credentials/service_account.json \
      --sheet "Respostas ao formulário 1" \
      --registro qrcodes/registro_qrcodes.json

O script adiciona as colunas (se inexistentes):
  Codigo_D1, Codigo_D2, Codigo_D3,
  Codigo_A1_D1, Codigo_A1_D2, Codigo_A1_D3

E preenche as células correspondentes buscando por `email` na planilha.
"""

import argparse
import json
import os
import sys
from pathlib import Path
import time
import random
import subprocess
import csv
import tempfile

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except Exception:
    print("❌ Erro: bibliotecas Google não instaladas. Instale: google-auth-oauthlib google-api-python-client")
    raise

try:
    from gerar_qrcodes import GeradorQRCodes
except Exception:
    GeradorQRCodes = None


DEFAULT_COLUMNS = [
    'Codigo_D1', 'Codigo_D2', 'Codigo_D3',
    'Codigo_A1_D1', 'Codigo_A1_D2', 'Codigo_A1_D3'
]

# colunas de controle de envio
TRACK_COLUMNS = [
    'Enviado_Email', 'Email_Status',
    'Enviado_WhatsApp', 'Whatsapp_Status',
    'Last_Sent_At'
]


def load_registro(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_map(registro: dict):
    # retorna map email -> dict dias/tipos
    m = {}
    def normalize_email(e: str):
        if not e:
            return ''
        return e.strip().lower()

    for c in registro.get('convidados', []):
        email = normalize_email(c.get('email'))
        if not email:
            continue
        entry = {
            'convidado': {},
            'acompanhante_1': {}
        }
        for qr in c.get('qrcodes', []):
            tip = qr.get('tipo')
            dia = str(qr.get('dia'))
            codigo = qr.get('codigo')
            if tip == 'convidado':
                entry['convidado'][dia] = codigo
            elif tip.startswith('acompanhante'):
                # assume acompanhante_1
                entry['acompanhante_1'][dia] = codigo
        m[email] = entry
        # também indexar por UID se presente no registro
        uid = c.get('uid')
        if uid:
            m[str(uid).strip()] = entry
    return m


def index_to_col(n: int) -> str:
    # 1-based index to Excel-style column letters
    result = ''
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--spreadsheet-id', required=True)
    parser.add_argument('--credentials', default='credentials/service_account.json')
    parser.add_argument('--sheet', default='Processamento')
    parser.add_argument('--dry-run', action='store_true', help='Simular execução sem gravar na planilha')
    parser.add_argument('--registro', default='qrcodes/registro_qrcodes.json')
    parser.add_argument('--auto-generate', action='store_true', help='Gerar automaticamente QRs faltantes antes de persistir')
    parser.add_argument('--retries', type=int, default=4, help='Número de tentativas para chamadas à API (retry)')
    parser.add_argument('--backoff-base', type=float, default=1.0, help='Base do backoff exponencial em segundos')
    parser.add_argument('--backoff-max', type=float, default=16.0, help='Máximo tempo de backoff em segundos')
    parser.add_argument('--send-method', choices=['email','whatsapp','sms'], help='Método para enviar convites após persistir')
    parser.add_argument('--send-dry-run', action='store_true', help='Simular envio (não envia realmente)')
    parser.add_argument('--send-batch-size', type=int, default=0, help='Tamanho de lote para envios (0 = enviar tudo de uma vez)')

    args = parser.parse_args()

    creds_path = Path(args.credentials)
    if not creds_path.exists():
        print(f"❌ Credenciais não encontradas: {creds_path}")
        sys.exit(1)

    registro_path = Path(args.registro)
    if not registro_path.exists():
        print(f"❌ Registro não encontrado: {registro_path}")
        sys.exit(1)

    registro = load_registro(str(registro_path))
    mapa = build_map(registro)
    # construir ordem de dias observada no registro (preserva ordem de aparição)
    dias_ordenados = []
    for c in registro.get('convidados', []):
        for qr in c.get('qrcodes', []):
            if qr.get('tipo') == 'convidado':
                d = str(qr.get('dia')).strip()
                if d and d not in dias_ordenados:
                    dias_ordenados.append(d)

    # mapear colunas Codigo_D1..DN para os dias detectados (se houver menos dias, restante ficará vazio)
    col_to_dia = {}
    for i, col in enumerate(DEFAULT_COLUMNS):
        if col.startswith('Codigo_D'):
            idx = int(col.split('Codigo_D')[-1]) - 1
            if idx < len(dias_ordenados):
                col_to_dia[col] = dias_ordenados[idx]
            else:
                col_to_dia[col] = None
        else:
            # Codigo_A1_Dx -> map também pelo sufixo Dx
            parts = col.split('_')
            if len(parts) == 3 and parts[0].startswith('Codigo') and parts[2].startswith('D'):
                dia_idx = parts[2].replace('D','')
                try:
                    idx = int(dia_idx) - 1
                    col_to_dia[col] = dias_ordenados[idx] if idx < len(dias_ordenados) else None
                except Exception:
                    col_to_dia[col] = None
            else:
                col_to_dia[col] = None

    creds = service_account.Credentials.from_service_account_file(str(creds_path), scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    sheet_name = args.sheet
    spreadsheet_id = args.spreadsheet_id

    # Ler toda a planilha (primeira aba especificada)
    range_all = f"'{sheet_name}'"

    def call_with_retry(fn, retries=4, backoff_base=1.0, backoff_max=16.0):
        attempt = 0
        while True:
            try:
                return fn()
            except HttpError as e:
                attempt += 1
                if attempt > retries:
                    raise
                sleep = min(backoff_max, backoff_base * (2 ** (attempt - 1)))
                sleep = sleep * (0.5 + random.random() * 0.5)  # jitter
                print(f"⚠️ HttpError: tentativa {attempt}/{retries}, aguardando {sleep:.1f}s: {e}")
                time.sleep(sleep)
            except Exception as e:
                attempt += 1
                if attempt > retries:
                    raise
                sleep = min(backoff_max, backoff_base * (2 ** (attempt - 1)))
                sleep = sleep * (0.5 + random.random() * 0.5)
                print(f"⚠️ Erro: tentativa {attempt}/{retries}, aguardando {sleep:.1f}s: {e}")
                time.sleep(sleep)

    res = call_with_retry(lambda: service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_all).execute(),
                          retries=args.retries, backoff_base=args.backoff_base, backoff_max=args.backoff_max)
    values = res.get('values', [])
    if not values:
        print('⚠️ Planilha vazia.')
        return

    header = values[0]

    # detectar coluna UID (se existir)
    uid_col = None
    for idx, h in enumerate(header):
        if not h:
            continue
        if h.strip().lower() == 'uid':
            uid_col = idx
            break

    # localizar coluna de email (preferir coluna intitulada exatamente 'E-mail')
    email_col = None
    # primeira prioridade: cabeçalho exato 'e-mail' ou 'email'
    for idx, h in enumerate(header):
        if not h:
            continue
        key = h.strip().lower()
        if key == 'e-mail' or key == 'email':
            email_col = idx
            break

    # segunda prioridade: cabeçalho comum 'endereço de e-mail' ou variações
    if email_col is None:
        email_candidates = ['endereço de e-mail','endereco de e-mail','endereco de email','endereco','email address']
        for idx, h in enumerate(header):
            if h and h.strip().lower() in email_candidates:
                email_col = idx
                break

    # fallback heurística: qualquer coluna que contenha 'email'
    if email_col is None:
        for idx, h in enumerate(header):
            if h and 'email' in h.strip().lower():
                email_col = idx
                break

    if email_col is None:
        print('❌ Não foi possível localizar coluna de email na planilha. Verifique cabeçalho.')
        return

    # garantir colunas de código no cabeçalho
    modified = False
    for col in DEFAULT_COLUMNS + TRACK_COLUMNS:
        if col not in header:
            header.append(col)
            modified = True

    # atualizar cabeçalho se modificado
    if modified:
        body = { 'values': [header] }
        if args.dry_run:
            print('ℹ️ Dry-run: cabeçalho a ser atualizado (simulado):', header)
        else:
            call_with_retry(lambda: service.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=f"'{sheet_name}'!1:1", valueInputOption='RAW', body=body).execute(),
                    retries=args.retries, backoff_base=args.backoff_base, backoff_max=args.backoff_max)
            print('✅ Cabeçalho atualizado com colunas de código')

    # recalcular índice das colunas alvo
    col_index = {h: i for i, h in enumerate(header)}

    def normalize_email(e: str):
        if not e:
            return ''
        return e.strip().lower()

    unmatched = []
    updated_rows = 0

    # preparar batchUpdate de valores
    data = []

    # iterar sobre linhas de dados
    for row_idx, row in enumerate(values[1:], start=2):
        # obter email da linha
        # tentar encontrar por UID primeiro (se coluna UID presente)
        entry = None
        if uid_col is not None and uid_col < len(row):
            uid_val = str(row[uid_col]).strip()
            if uid_val:
                entry = mapa.get(uid_val)

        # fallback para email
        if entry is None:
            if email_col < len(row):
                email = row[email_col].strip()
            else:
                email = ''
            if not email:
                unmatched.append({'row': row_idx, 'reason': 'email vazio', 'row': row})
                continue
            email_norm = normalize_email(email)
            entry = mapa.get(email_norm)
        if not entry:
            # tentar correspondência por email sem pontos (Gmail-like) e sem tags
            alt = email_norm
            if '@' in alt:
                local, domain = alt.split('@', 1)
                local = local.split('+', 1)[0].replace('.', '')
                alt2 = f"{local}@{domain}"
                entry = mapa.get(alt2)
        if not entry:
            unmatched.append({'row': row_idx, 'email': email, 'reason': 'email não encontrado no registro'})
            continue

        # construir valores para as colunas DEFAULT_COLUMNS mapeando para as datas reais
        row_values = []
        for col in DEFAULT_COLUMNS:
            dia_key = col_to_dia.get(col)
            if dia_key:
                if col.startswith('Codigo_D'):
                    val = entry.get('convidado', {}).get(dia_key, '')
                else:
                    # Codigo_A1_Dx -> acompanhante_1
                    val = entry.get('acompanhante_1', {}).get(dia_key, '')
            else:
                val = ''
            row_values.append(val)

        # montar range: col_start-col_end for this row
        start_col = col_index[DEFAULT_COLUMNS[0]] + 1  # 1-based
        end_col = col_index[DEFAULT_COLUMNS[-1]] + 1
        range_a1 = f"'{sheet_name}'!{chr(64+start_col)}{row_idx}:{chr(64+end_col)}{row_idx}"
        # Nota: esta conversão simples do índice para letra funciona para colunas até Z (suficiente aqui)
        data.append({
            'range': range_a1,
            'values': [row_values]
        })
        updated_rows += 1

    # gravar log de linhas não encontradas
    if unmatched:
        logp = Path('qrcodes')
        logp.mkdir(parents=True, exist_ok=True)
        log_file = logp / 'persist_log.txt'
        with open(log_file, 'a', encoding='utf-8') as lf:
            import datetime
            lf.write(f"\n=== {datetime.datetime.utcnow().isoformat()}Z - tentativa de persistência\n")
            for u in unmatched:
                lf.write(str(u) + "\n")
        print(f"⚠️ {len(unmatched)} linhas não encontradas (detalhes em {log_file})")

    # se houver linhas não encontradas e opção --auto-generate, tentar gerar QRs faltantes
    if unmatched and args.auto_generate:
        if GeradorQRCodes is None:
            print('❌ Não foi possível importar GeradorQRCodes. Verifique Python/gerar_qrcodes.py e dependências.')
        else:
            # construir lista de convidados a partir das linhas não encontradas
            to_generate = []
            import unicodedata
            def _norm_key(s: str):
                if not s:
                    return ''
                nk = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode()
                nk = nk.lower().strip().replace(' ', '_').replace('-', '_')
                return nk

            header_idx = {_norm_key(h): i for i, h in enumerate(header)}
            for u in unmatched:
                r = values[u['row'] - 1]
                # Usar explicitamente a coluna A (índice 0) como controle de autorização.
                autoriz_idx = 0 if len(header) > 0 else None
                if autoriz_idx is not None:
                    val_aut = ''
                    if autoriz_idx < len(r):
                        val_aut = str(r[autoriz_idx]).strip().lower()
                    # considerar somente 'sim' (case-insensitive) como autorizado
                    if val_aut != 'sim':
                        # pular geração para não autorizados
                        continue
                # extrair nome
                nome = ''
                if 'nome' in header_idx and header_idx['nome'] < len(r):
                    nome = r[header_idx['nome']]
                # extrair email
                email = ''
                if 'email' in header_idx and header_idx['email'] < len(r):
                    email = r[header_idx['email']]
                if not email:
                    for k,i in header_idx.items():
                        kl = (k or '').lower()
                        kl_norm = kl.replace('-', '').replace('_', '').replace('ã','a').replace('ó','o')
                        if ('email' in kl) or ('e-mail' in kl) or ('endereco' in kl_norm) or ('endereço' in kl):
                            if i < len(r):
                                email = r[i]
                                break
                # extrair dias
                dias = []
                for k,i in header_idx.items():
                    if 'dia' in k.lower() or 'dias' in k.lower():
                        if i < len(r):
                            val = r[i]
                            if isinstance(val, str) and ',' in val:
                                dias = [d.strip() for d in val.split(',') if d.strip()]
                            elif val:
                                dias = [val]
                        break
                # acompanhante 1
                acomp1 = ''
                for k,i in header_idx.items():
                    if 'acompanhante_1' in k.lower() or ('acompanhante' in k.lower() and '1' in k):
                        if i < len(r):
                            acomp1 = r[i]
                            break

                convidado_obj = {
                    'nome': nome or (email.split('@')[0] if email else 'Convidado'),
                    'email': email,
                    'dias': dias or ['1','2','3'],
                    'acompanhante_1_nome': acomp1
                }
                to_generate.append(convidado_obj)

            if to_generate:
                print(f"ℹ️ Gerando QR codes para {len(to_generate)} convidados ausentes...")
                ger = GeradorQRCodes(pasta_saida='./qrcodes')
                stats_gen = ger.processar_convidados(to_generate)
                ger.exportar_registro(stats_gen, formato='json')
                # recarregar registro e mapa
                registro = load_registro(str(registro_path))
                mapa = build_map(registro)
                # recarregar valores da planilha para reconstruir batch
                res = call_with_retry(lambda: service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_all).execute(),
                                      retries=args.retries, backoff_base=args.backoff_base, backoff_max=args.backoff_max)
                values = res.get('values', [])
                # rebuild data
                data = []
                updated_rows = 0
                for row_idx, row in enumerate(values[1:], start=2):
                    if email_col < len(row):
                        email = row[email_col].strip()
                    else:
                        email = ''
                    if not email:
                        continue
                    email_norm = normalize_email(email)
                    entry = mapa.get(email_norm)
                    if not entry:
                        alt = email_norm
                        if '@' in alt:
                            local, domain = alt.split('@', 1)
                            local = local.split('+', 1)[0].replace('.', '')
                            alt2 = f"{local}@{domain}"
                            entry = mapa.get(alt2)
                    if not entry:
                        continue
                    row_values = []
                    for col in DEFAULT_COLUMNS:
                        if col.startswith('Codigo_D'):
                            dia = col.split('Codigo_D')[-1]
                            val = entry.get('convidado', {}).get(dia, '')
                        else:
                            parts = col.split('_')
                            if len(parts) == 3 and parts[0].startswith('Codigo'):
                                dia = parts[-1].replace('D','')
                                val = entry.get('acompanhante_1', {}).get(dia, '')
                            else:
                                val = ''
                        row_values.append(val)
                    start_col = col_index[DEFAULT_COLUMNS[0]] + 1
                    end_col = col_index[DEFAULT_COLUMNS[-1]] + 1
                    range_a1 = f"'{sheet_name}'!{index_to_col(start_col)}{row_idx}:{index_to_col(end_col)}{row_idx}"
                    data.append({'range': range_a1, 'values': [row_values]})
                    updated_rows += 1

    if data:
        body = { 'valueInputOption': 'RAW', 'data': data }
        if args.dry_run:
            print(f"ℹ️ Dry-run: {len(data)} linhas seriam atualizadas na aba '{sheet_name}' (simulado). Total a atualizar: {updated_rows}")
            # mostrar detalhes das primeiras atualizações para inspeção
            for i, d in enumerate(data[:20], start=1):
                print(f"  {i}. Range: {d.get('range')}, Values: {d.get('values')}")
        else:
            result = call_with_retry(lambda: service.spreadsheets().values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute(),
                                     retries=args.retries, backoff_base=args.backoff_base, backoff_max=args.backoff_max)
            print(f"✅ Atualizadas {len(data)} linhas na planilha")
            print(f"ℹ️ Total de linhas atualizadas: {updated_rows}")
    else:
        print('ℹ️ Nenhuma linha para atualizar (nenhum email correspondido no registro)')

    # Integração com envio em lotes
    if args.send_method:
        print(f"ℹ️ Preparando envio via {args.send_method}...")
        import unicodedata
        def _norm_key(s: str):
            if not s:
                return ''
            nk = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode()
            nk = nk.lower().strip().replace(' ', '_').replace('-', '_')
            return nk

        header_idx = {_norm_key(h): i for i, h in enumerate(header)}
        rows_to_send = []
        # Selecionar TODAS as linhas autorizadas (coluna A == 'sim', case-insensitive)
        for row_idx, row in enumerate(values[1:], start=2):
            # verificar autorizacao na coluna A (indice 0)
            auth_val = ''
            if 0 < len(row):
                # normalmente row[0] existe; mas proteger
                try:
                    auth_val = str(row[0])
                except Exception:
                    auth_val = ''
            if auth_val.strip().lower() != 'sim':
                continue

            # obter email (usar email_col detectado previamente)
            email = ''
            if 'email_col' in locals() and email_col is not None and email_col < len(row):
                email = row[email_col]
            else:
                # tentar encontrar coluna 'email' no header_idx
                for k, i in header_idx.items():
                    if k and 'email' in k.lower() and i < len(row):
                        email = row[i]
                        break

            if not email or not str(email).strip():
                continue

            # verificar se a linha já possui códigos gerados (pelo menos uma das DEFAULT_COLUMNS)
            has_code = False
            for col in DEFAULT_COLUMNS:
                idx = col_index.get(col)
                if idx is not None and idx < len(row):
                    if str(row[idx]).strip():
                        has_code = True
                        break

            if not has_code:
                # pular linhas sem código (não enviar)
                continue

            rows_to_send.append((row_idx, row))

        if not rows_to_send:
            print('⚠️ Nenhuma linha disponível para envio.')
        else:
            def write_batches(rows_with_idx, batch_size):
                files = []
                mappings = []  # list of row_idx lists per file
                if batch_size <= 0:
                    batch_size = len(rows_with_idx)
                for i in range(0, len(rows_with_idx), batch_size):
                    block = rows_with_idx[i:i+batch_size]
                    fd, path = tempfile.mkstemp(prefix='send_batch_', suffix='.csv', dir='.')
                    os.close(fd)
                    with open(path, 'w', newline='', encoding='utf-8') as wf:
                        writer = csv.writer(wf)
                        hdr = ['nome','email','telefone','dias','acompanhante_1_nome','acompanhante_1_telefone']
                        writer.writerow(hdr)
                        row_indices = []
                        for (ridx, r) in block:
                            row_out = []
                            for h in hdr:
                                # Prefer explicit email column detected earlier for the 'email' field
                                if h == 'email' and 'email_col' in locals() and email_col is not None and email_col < len(r):
                                    row_out.append(r[email_col])
                                    continue
                                idx = header_idx.get(h)
                                if idx is not None and idx < len(r):
                                    row_out.append(r[idx])
                                else:
                                    row_out.append('')
                            writer.writerow(row_out)
                            row_indices.append(ridx)
                    files.append(path)
                    mappings.append(row_indices)
                return files, mappings

            files, mappings = write_batches(rows_to_send, args.send_batch_size or 0)

            for idx_f, fpath in enumerate(files):
                row_indices = mappings[idx_f]
                if args.send_method == 'email':
                    cmd = ['python', 'Python/enviar_emails_qrcodes.py', '--arquivo', fpath]
                    if not args.send_dry_run:
                        cmd.append('--enviar')
                    else:
                        cmd.append('--teste')
                else:
                    metodo = 'whatsapp' if args.send_method == 'whatsapp' else 'sms'
                    cmd = ['python', 'Python/enviar_convites_whatsapp_sms.py', '--arquivo', fpath, '--metodo', metodo]
                    if not args.send_dry_run:
                        cmd.append('--enviar')
                    else:
                        cmd.append('--teste')

                print(f"ℹ️ Executando envio: {' '.join(cmd)}")
                success = False
                status_msg = ''
                try:
                    subprocess.run(cmd, check=True)
                    success = True
                    status_msg = 'OK' if not args.send_dry_run else 'TESTE'
                except Exception as e:
                    status_msg = str(e)
                    print(f"❌ Erro ao executar envio para {fpath}: {e}")

                # atualizar colunas de status para as linhas deste batch
                updates = []
                for rownum in row_indices:
                    vals = []
                    # Enviado_Email, Email_Status, Enviado_WhatsApp, Whatsapp_Status, Last_Sent_At
                    if args.send_method == 'email':
                        vals = [ 'Sim' if success and not args.send_dry_run else ('Teste' if args.send_dry_run else 'Falha'), status_msg, '', '', '']
                    elif args.send_method == 'whatsapp':
                        vals = [ '', '', 'Sim' if success and not args.send_dry_run else ('Teste' if args.send_dry_run else 'Falha'), status_msg, '']
                    else:
                        vals = [ '', '', '', '', '']

                    start_col = col_index[TRACK_COLUMNS[0]] + 1
                    end_col = col_index[TRACK_COLUMNS[-1]] + 1
                    range_a1 = f"'{sheet_name}'!{index_to_col(start_col)}{rownum}:{index_to_col(end_col)}{rownum}"
                    updates.append({'range': range_a1, 'values': [vals]})

                if updates:
                    body_upd = {'valueInputOption': 'RAW', 'data': updates}
                    try:
                        if args.dry_run:
                            print(f"ℹ️ Dry-run: status de envio para {len(updates)} linhas seria atualizado (simulado)")
                        else:
                            call_with_retry(lambda: service.spreadsheets().values().batchUpdate(spreadsheetId=spreadsheet_id, body=body_upd).execute(), retries=args.retries, backoff_base=args.backoff_base, backoff_max=args.backoff_max)
                            print(f"✅ Status de envio atualizado para {len(updates)} linhas")
                    except Exception as e:
                        print(f"❌ Falha ao atualizar status de envio: {e}")

                # remover arquivo temporário após tentativa de envio
                try:
                    os.remove(fpath)
                    print(f"🧹 Arquivo temporário removido: {fpath}")
                except Exception:
                    pass

if __name__ == '__main__':
    main()
