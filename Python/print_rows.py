import csv
with open('convidados_live.csv','r',encoding='utf-8') as f:
    r=list(csv.reader(f))
    print('HEADER ROW:', r[0])
    for i,row in enumerate(r[1:6],1):
        print(i, row)
