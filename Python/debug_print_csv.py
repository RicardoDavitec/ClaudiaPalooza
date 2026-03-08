from gerar_qrcodes import carregar_csv, CSV_HEADERS
rows = carregar_csv('convidados_live.csv')
print('CSV_HEADERS:', CSV_HEADERS)
for i,r in enumerate(rows[:10],1):
    print(i, r)
