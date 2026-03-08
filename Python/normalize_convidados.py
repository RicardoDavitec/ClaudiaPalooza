#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Normaliza CSV de convidados para o formato esperado pelos scripts do projeto.

Uso:
    python normalize_convidados.py --input convidados.csv --output convidados_normalizado.csv

O script mapeia variações de cabeçalho (pt-BR/EN) para colunas padrão:
    nome, email, telefone, dias, num_acompanhantes, acompanhante_1_nome, acompanhante_1_telefone, restricoes_alimentares

Também limpa telefones e converte 'Dias de participação' em números de dia (1,2,3).
"""

import csv
import re
import argparse
from pathlib import Path

# Mapeamentos possíveis de cabeçalhos para campos padrão
HEADER_MAP = {
    # nome
    'nome': 'nome',
    'nome completo': 'nome',
    'full name': 'nome',

    # email
    'email': 'email',
    'e-mail': 'email',
    'endereço de e-mail': 'email',
    'endereco de e-mail': 'email',
    'email address': 'email',

    # telefone
    'telefone': 'telefone',
    'telefone com whatsapp': 'telefone',
    'telefone (whatsapp)': 'telefone',
    'telefone com whatsapp': 'telefone',

    # dias
    'dias': 'dias',
    'dias de participação:': 'dias',
    'dias de participação': 'dias',
    'dias de participacao': 'dias',

    # restricoes
    'restrições alimentares': 'restricoes_alimentares',
    'restricoes alimentares:': 'restricoes_alimentares',
    'restricoes alimentares': 'restricoes_alimentares',

    # acompanhante
    'acompanhante? (até um por convidado.)': 'tem_acompanhante',
    'acompanhante': 'acompanhante_1_nome',
    'nome do acompanhante': 'acompanhante_1_nome',
    'nome do acompanhante:': 'acompanhante_1_nome',

    'telefone (whatsapp) do acompanhante': 'acompanhante_1_telefone',
    'telefone do acompanhante': 'acompanhante_1_telefone',

    # generic
    'pontuação': 'pontuacao',
    'timestamp': 'timestamp',
    'carimbo de data/hora': 'timestamp',
}


# Detecta se texto contém dia 10/04,11/04,12/04 e converte para 1,2,3
def parse_dias(text: str):
    if not text:
        return ''
    s = str(text)
    dias = set()
    if re.search(r'10\D?04|10/04|\b10\b', s):
        dias.add('1')
    if re.search(r'11\D?04|11/04|\b11\b', s):
        dias.add('2')
    if re.search(r'12\D?04|12/04|\b12\b', s):
        dias.add('3')
    if not dias:
        found = re.findall(r'\b[123]\b', s)
        for f in found:
            dias.add(f)
    return ','.join(sorted(dias, key=int))


# Limpar telefone: remover não-dígitos
def clean_phone(phone: str):
    if not phone:
        return ''
    digits = re.sub(r'\D', '', str(phone))
    return digits


def normalize_row(row, header_map):
    out = {
        'nome': '',
        'email': '',
        'telefone': '',
        'dias': '',
        'num_acompanhantes': '0',
        'acompanhante_1_nome': '',
        'acompanhante_1_telefone': '',
        'restricoes_alimentares': ''
    }

    for key, val in row.items():
        if key is None:
            continue
        k = key.strip().lower()
        mapped = header_map.get(k)
        if not mapped:
            continue
        v = val.strip() if isinstance(val, str) else val

        if mapped == 'nome':
            out['nome'] = v
        elif mapped == 'email':
            out['email'] = v
        elif mapped == 'telefone':
            out['telefone'] = clean_phone(v)
        elif mapped == 'dias':
            out['dias'] = parse_dias(v)
        elif mapped == 'restricoes_alimentares':
            out['restricoes_alimentares'] = v
        elif mapped == 'tem_acompanhante':
            if str(v).strip().lower() in ['sim', 's', 'yes', 'y', 'true']:
                out['num_acompanhantes'] = '1'
            else:
                out['num_acompanhantes'] = '0'
        elif mapped == 'acompanhante_1_nome':
            out['acompanhante_1_nome'] = v
        elif mapped == 'acompanhante_1_telefone':
            out['acompanhante_1_telefone'] = clean_phone(v)

    return out


def build_header_map(headers):
    hm = {}
    for h in headers:
        if h is None:
            continue
        key = h.strip().lower()
        if key in HEADER_MAP:
            hm[key] = HEADER_MAP[key]
        else:
            k2 = re.sub(r'[^a-z0-9 ]', '', key)
            if k2 in HEADER_MAP:
                hm[key] = HEADER_MAP[k2]
            else:
                if 'nome' in key and 'acompan' not in key:
                    hm[key] = 'nome'
                elif 'e-mail' in key or 'email' in key or 'endereço' in key or 'endereco' in key:
                    hm[key] = 'email'
                elif 'telefone' in key or 'whatsapp' in key:
                    if 'acompanhante' in key:
                        hm[key] = 'acompanhante_1_telefone'
                    else:
                        hm[key] = 'telefone'
                elif 'dia' in key:
                    hm[key] = 'dias'
                elif 'restri' in key:
                    hm[key] = 'restricoes_alimentares'
                elif 'acompanhante' in key:
                    if 'nome' in key:
                        hm[key] = 'acompanhante_1_nome'
                    else:
                        hm[key] = 'tem_acompanhante'
                else:
                    hm[key] = None
    return hm


def main():
    parser = argparse.ArgumentParser(description='Normaliza CSV de convidados para formato do projeto')
    parser.add_argument('--input', default='convidados.csv', help='CSV de entrada')
    parser.add_argument('--output', default='convidados_normalizado.csv', help='CSV de saída normalizado')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Arquivo não encontrado: {input_path}")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        header_map = build_header_map(headers)

        rows = [normalize_row(r, header_map) for r in reader]

    out_path = Path(args.output)
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['nome','email','telefone','dias','num_acompanhantes','acompanhante_1_nome','acompanhante_1_telefone','restricoes_alimentares']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"✅ Normalizado salvo em: {out_path} ({len(rows)} registros)")


if __name__ == '__main__':
    main()
