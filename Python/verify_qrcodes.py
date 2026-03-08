import json
import csv
import os
import re
import sys


def find_file(*candidates):
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


registro_path = find_file('qrcodes/registro_qrcodes.json', 'Python/qrcodes/registro_qrcodes.json')
csv_path = find_file('convidados_normalizado.csv', 'Python/convidados_normalizado.csv', 'convidados.csv')

if not registro_path:
    print('Arquivo de registro de QRs não encontrado (qrcodes/registro_qrcodes.json)')
    sys.exit(2)
if not csv_path:
    print('CSV de convidados normalizado não encontrado (convidados_normalizado.csv)')
    sys.exit(2)

with open(registro_path, encoding='utf-8') as f:
    registro = json.load(f)

# normalize registro into list of entries
entries = []
if isinstance(registro, dict):
    # values are entries
    for v in registro.values():
        entries.append(v)
elif isinstance(registro, list):
    entries = registro
else:
    print('Formato do registro desconhecido')
    sys.exit(2)


def extract_strings(obj):
    out = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(extract_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(extract_strings(v))
    else:
        try:
            out.append(str(obj))
        except Exception:
            pass
    return out


code_re = re.compile(r'EVT-[A-Z0-9\-]+')

registro_map = {}
for ent in entries:
    # try to find email field in entry
    email = None
    if isinstance(ent, dict):
        for k, v in ent.items():
            if k and 'email' in k.lower():
                email = str(v).strip().lower()
                break
    if not email:
        # try to find an email-like string in values
        for s in extract_strings(ent):
            if isinstance(s, str) and '@' in s and '.' in s:
                email = s.strip().lower()
                break
    codes = []
    for s in extract_strings(ent):
        if not isinstance(s, str):
            continue
        for m in code_re.findall(s.upper()):
            codes.append(m)
        if s.lower().endswith('.png') or s.lower().endswith('.jpg'):
            codes.append(os.path.basename(s))
    if email:
        registro_map[email] = list(dict.fromkeys(codes))

# fallback: try filename-based mapping scanning qrcodes/ dir
if os.path.isdir('qrcodes'):
    for fn in os.listdir('qrcodes'):
        if not fn.lower().endswith('.png'):
            continue
        # try to find an email in filename
        if '_' in fn:
            parts = fn.split('_')
            for p in parts:
                if '@' in p and '.' in p:
                    registro_map.setdefault(p.lower(), []).append(fn)

problems = []
checked = 0
ok = 0

with open(csv_path, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    headers = [h.lower() for h in reader.fieldnames or []]
    # detect email column
    email_key = None
    for k in reader.fieldnames:
        if k and ('email' == k.strip().lower() or 'e-mail' == k.strip().lower()):
            email_key = k
            break
    if email_key is None:
        for k in reader.fieldnames:
            if k and 'email' in k.lower():
                email_key = k
                break
    # detect num_acompanhantes
    num_key = None
    for k in reader.fieldnames:
        if k and ('num_acompanhantes' in k.lower() or 'acompanhantes' in k.lower() or 'n' in k.lower() and 'acomp' in k.lower()):
            num_key = k
            break

    for row in reader:
        checked += 1
        email = row.get(email_key, '').strip().lower() if email_key else ''
        try:
            num_ac = int(row.get(num_key, '0') or 0) if num_key else 0
        except Exception:
            num_ac = 0
        expected = 1 + max(0, num_ac)
        codes = registro_map.get(email, [])
        if len(codes) >= expected and len(codes) > 0:
            ok += 1
        else:
            problems.append({'nome': row.get('nome') or row.get('nome_completo') or '', 'email': email, 'expected': expected, 'found': len(codes), 'codes': codes})

print(f'Conferência completa: {checked} convidados verificados')
print(f'OK: {ok}  | Com problemas: {len(problems)}')
if problems:
    print('\nDetalhes dos registros com inconsistências:')
    for p in problems:
        print(f"- {p['nome']} <{p['email']}> — esperado {p['expected']}, encontrado {p['found']} — códigos: {p['codes']}")

sys.exit(0)
