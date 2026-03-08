#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Geração de QR Codes para Evento
==========================================
Gera QR codes únicos para convidados e acompanhantes de um evento.

Requisitos:
    pip install qrcode pillow openpyxl google-auth-oauthlib google-auth-httplib2 google-api-python-client

Uso:
    python gerar_qrcodes.py [arquivo_entrada.xlsx] [pasta_saida]
    
    Se não especificado, usa:
    - Entrada: convidados.xlsx (primeira aba)
    - Saída: ./qrcodes/
"""

import os
import sys
import csv
import json
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple
import argparse

try:
    import qrcode
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer, CircleModuleDrawer
    from qrcode.image.styles.colormasks import SquareGradiantColorMask
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("❌ Erro: Bibliotecas necessárias não instaladas.")
    print("Execute: pip install qrcode[pil] pillow")
    sys.exit(1)


class GeradorQRCodes:
    """Gerenciador de geração de QR codes para eventos."""
    
    def __init__(self, pasta_saida: str = "./qrcodes", nome_evento: str = "EVENTO 2026", dry_run: bool = False):
        """
        Inicializa o gerador de QR codes.
        
        Args:
            pasta_saida: Caminho da pasta para salvar os QR codes
            nome_evento: Nome do evento (usado nas imagens)
        """
        self.pasta_saida = Path(pasta_saida)
        self.pasta_saida.mkdir(parents=True, exist_ok=True)
        self.nome_evento = nome_evento
        self.dry_run = dry_run
        self.registro_qrcodes = []
        # carregar registro existente para permitir geração idempotente
        self.registro_path = self.pasta_saida / "registro_qrcodes.json"
        self.registro_map = {}
        if self.registro_path.exists():
            try:
                with open(self.registro_path, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                for c in dados.get('convidados', []):
                    email = c.get('email')
                    if email:
                        self.registro_map[email] = c
                print(f"ℹ️ Registro existente carregado: {len(self.registro_map)} convidados")
            except Exception as e:
                print(f"⚠️ Não foi possível carregar registro existente: {e}")
        
    def gerar_id_unico(self, nome: str, email: str, tipo: str) -> str:
        """
        Gera um ID único baseado em hash SHA256.
        
        Args:
            nome: Nome do convidado
            email: Email do convidado
            tipo: 'convidado' ou 'acompanhante'
            
        Returns:
            String hexadecimal de 16 caracteres
        """
        timestamp = datetime.now().isoformat()
        dados = f"{nome}|{email}|{tipo}|{timestamp}".encode('utf-8')
        hash_obj = hashlib.sha256(dados)
        return hash_obj.hexdigest()[:16].upper()
    
    def gerar_codigo_acesso(self, id_unico: str, dia: str) -> str:
        """
        Gera código de acesso no formato: EVENTO-DIA-ID
        
        Exemplo: EVT-D1-A3F5B2C1E9D4K7L2
        
        Args:
            id_unico: ID único de 16 caracteres
            dia: Número do dia ('1', '2', '3')
            
        Returns:
            Código formatado
        """
        # sanitize dia para evitar caracteres inválidos em filenames (ex: '11/04')
        safe_dia = ''.join(ch if (ch.isalnum() or ch in ('-','_')) else '_' for ch in str(dia))
        # collapse multiple underscores
        while '__' in safe_dia:
            safe_dia = safe_dia.replace('__', '_')
        safe_dia = safe_dia.strip('_') or str(dia)
        return f"EVT-D{safe_dia}-{id_unico}"
    
    def criar_qrcode(self, dados: str, arquivo_saida: str, 
                     com_logo: bool = False, nome_pessoa: str = "") -> bool:
        """
        Cria um QR code e salva em arquivo.
        
        Args:
            dados: Dados a codificar no QR code
            arquivo_saida: Caminho do arquivo de saída
            com_logo: Se True, adiciona moldura personalizada
            nome_pessoa: Nome da pessoa (para exibir na moldura)
            
        Returns:
            True se bem-sucedido, False caso contrário
        """
        try:
            # Gerar QR code
            qr = qrcode.QRCode(
                version=None,  # usar fit automático para escolher versão adequada
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(dados)
            qr.make(fit=True)
            
            # Criar imagem com cores
            try:
                img_qr = qr.make_image(fill_color="black", back_color="white")
            except Exception:
                # fallback simples: usar qrcode.make
                try:
                    img_qr = qrcode.make(dados)
                except Exception as e:
                    raise
            
            if com_logo:
                # Adicionar moldura e informações ao redor do QR code
                tamanho_qr = img_qr.size[0]
                margem = 40
                tamanho_final = tamanho_qr + (2 * margem)
                
                # Criar imagem com fundo branco
                img_final = Image.new('RGB', (tamanho_final, tamanho_final + 60), 'white')
                
                # Colar QR code no centro
                img_final.paste(img_qr, (margem, margem))
                
                # Adicionar texto
                try:
                    fonte_grande = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
                    fonte_pequena = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
                except:
                    # Fallback se fonte não encontrada
                    fonte_grande = ImageFont.load_default()
                    fonte_pequena = ImageFont.load_default()
                
                draw = ImageDraw.Draw(img_final)
                
                # Nome da pessoa
                if nome_pessoa:
                    bbox = draw.textbbox((0, 0), nome_pessoa, font=fonte_grande)
                    largura_texto = bbox[2] - bbox[0]
                    x_texto = (tamanho_final - largura_texto) // 2
                    draw.text((x_texto, tamanho_qr + margem + 10), nome_pessoa, 
                             fill="black", font=fonte_grande)
                
                # Nome do evento
                bbox = draw.textbbox((0, 0), self.nome_evento, font=fonte_pequena)
                largura_texto = bbox[2] - bbox[0]
                x_texto = (tamanho_final - largura_texto) // 2
                draw.text((x_texto, tamanho_qr + margem + 35), self.nome_evento, 
                         fill="gray", font=fonte_pequena)
                
                if not getattr(self, 'dry_run', False):
                    caminho = Path(arquivo_saida)
                    caminho.parent.mkdir(parents=True, exist_ok=True)
                    img_final.save(arquivo_saida, quality=95)
            else:
                if not getattr(self, 'dry_run', False):
                    caminho = Path(arquivo_saida)
                    caminho.parent.mkdir(parents=True, exist_ok=True)
                    img_qr.save(arquivo_saida, quality=95)
                else:
                    # quando em dry_run, apenas simular criação
                    pass
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar QR code: {e}")
            return False
    
    def processar_convidados(self, dados_convidados: List[Dict]) -> Dict:
        """
        Processa lista de convidados e gera QR codes.
        
        Args:
            dados_convidados: Lista de dicionários com dados dos convidados
                Campos esperados: nome, email, dias (lista de dias), acompanhante_nome
                
        Returns:
            Dicionário com estatísticas e informações dos QR codes gerados
        """
        stats = {
            "total_convidados": len(dados_convidados),
            "qrcodes_gerados": 0,
            "acompanhantes_processados": 0,
            "erros": 0,
            "convidados": []
        }
        
        for idx, convidado in enumerate(dados_convidados, 1):
            try:
                nome = convidado.get('nome', 'Desconhecido').strip()
                email = convidado.get('email', f'guest{idx}@event.local').strip()
                dias = convidado.get('dias', ['1', '2', '3'])
                
                # Garantir que dias é uma lista
                if isinstance(dias, str):
                    dias = [dias]
                
                # verificar registro existente (idempotência)
                existing = self.registro_map.get(email)
                if existing and existing.get('qrcodes'):
                    # Mesclar: verificar se faltam códigos para alguns dias/acompanhantes
                    info_convidado = existing
                    # identificar dias já gerados para convidado e acompanhantes
                    existentes_por_tipo_dia = set()
                    for qr in info_convidado.get('qrcodes', []):
                        chave = (qr.get('tipo'), str(qr.get('dia')))
                        existentes_por_tipo_dia.add(chave)
                else:
                    info_convidado = {
                        "nome": nome,
                        "email": email,
                        "qrcodes": []
                    }
                    existentes_por_tipo_dia = set()
                
                # Gerar QR codes para cada dia de presença
                for dia in dias:
                    chave = ("convidado", str(dia))
                    if chave in existentes_por_tipo_dia:
                        # já existe para este convidado/dia
                        continue

                    id_unico = self.gerar_id_unico(nome, email, f"convidado_dia{dia}")
                    codigo_acesso = self.gerar_codigo_acesso(id_unico, str(dia))

                    # Nome do arquivo
                    nome_arquivo = f"QR_{codigo_acesso}.png"
                    # sanitize filename to remove any slash or unsafe chars
                    import re
                    nome_arquivo = re.sub(r"[^A-Za-z0-9._-]", "_", nome_arquivo)
                    caminho_arquivo = self.pasta_saida / nome_arquivo

                    # Criar QR code simples
                    sucesso = self.criar_qrcode(
                        dados=codigo_acesso,
                        arquivo_saida=str(caminho_arquivo),
                        com_logo=False,
                        nome_pessoa=f"{nome} - Dia {dia}"
                    )

                    if sucesso:
                        info_qr = {
                            "arquivo": nome_arquivo,
                            "codigo": codigo_acesso,
                            "dia": dia,
                            "tipo": "convidado"
                        }
                        info_convidado["qrcodes"].append(info_qr)
                        stats["qrcodes_gerados"] += 1
                        existentes_por_tipo_dia.add(chave)
                
                # Processar acompanhante(s) se existir(em)
                for i in range(1, 3):  # Suportar até 2 acompanhantes
                    acomp_nome = convidado.get(f'acompanhante_{i}_nome', '').strip()
                    if acomp_nome:
                        for dia in dias:
                            chave_acomp = (f"acompanhante_{i}", str(dia))
                            if chave_acomp in existentes_por_tipo_dia:
                                continue

                            id_unico = self.gerar_id_unico(
                                acomp_nome,
                                f"{acomp_nome.replace(' ', '_')}_{idx}@event.local",
                                f"acompanhante_{i}_dia{dia}"
                            )
                            codigo_acesso = self.gerar_codigo_acesso(id_unico, str(dia))

                            nome_arquivo = f"QR_{codigo_acesso}.png"
                            import re
                            nome_arquivo = re.sub(r"[^A-Za-z0-9._-]", "_", nome_arquivo)
                            caminho_arquivo = self.pasta_saida / nome_arquivo

                            sucesso = self.criar_qrcode(
                                dados=codigo_acesso,
                                arquivo_saida=str(caminho_arquivo),
                                com_logo=False,
                                nome_pessoa=f"{acomp_nome} (Acomp.) - Dia {dia}"
                            )

                            if sucesso:
                                info_qr = {
                                    "arquivo": nome_arquivo,
                                    "codigo": codigo_acesso,
                                    "dia": dia,
                                    "tipo": f"acompanhante_{i}"
                                }
                                info_convidado["qrcodes"].append(info_qr)
                                stats["qrcodes_gerados"] += 1
                                stats["acompanhantes_processados"] += 1
                                existentes_por_tipo_dia.add(chave_acomp)
                
                # atualizar registro em memória
                self.registro_map[email] = info_convidado
                stats["convidados"].append(info_convidado)
                
                # Feedback a cada 10 convidados
                if idx % 10 == 0:
                    print(f"✅ Processados {idx}/{len(dados_convidados)} convidados...")
                    
            except Exception as e:
                print(f"❌ Erro processando convidado {idx} ({nome}): {e}")
                stats["erros"] += 1
        
        return stats
    
    def exportar_registro(self, stats: Dict, formato: str = "json") -> str:
        """
        Exporta registro de QR codes gerados.
        
        Args:
            stats: Dicionário com estatísticas
            formato: 'json' ou 'csv'
            
        Returns:
            Caminho do arquivo gerado
        """
        # Ao exportar, preferir salvar o registro mesclado em disco (self.registro_map)
        if formato == "json":
            arquivo = self.pasta_saida / "registro_qrcodes.json"
            try:
                dados = {
                    "convidados": list(self.registro_map.values()),
                    "total_convidados": len(self.registro_map)
                }
                with open(arquivo, 'w', encoding='utf-8') as f:
                    json.dump(dados, f, indent=2, ensure_ascii=False)
            except Exception:
                # fallback: salvar stats
                arquivo = self.pasta_saida / "registro_qrcodes.json"
                with open(arquivo, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, indent=2, ensure_ascii=False)
        
        elif formato == "csv":
            arquivo = self.pasta_saida / "registro_qrcodes.csv"
            with open(arquivo, 'w', newline='', encoding='utf-8') as f:
                if stats["convidados"]:
                    writer = csv.writer(f)
                    writer.writerow([
                        "Nome Convidado", "Email", "Tipo QR", 
                        "Dia", "Código Acesso", "Arquivo"
                    ])
                    
                    for convidado in stats["convidados"]:
                        for qr in convidado["qrcodes"]:
                            writer.writerow([
                                convidado["nome"],
                                convidado["email"],
                                qr["tipo"],
                                qr["dia"],
                                qr["codigo"],
                                qr["arquivo"]
                            ])
        
        return str(arquivo)
    
    def gerar_relatorio(self, stats: Dict) -> str:
        """
        Gera relatório em texto com resumo da geração.
        
        Args:
            stats: Dicionário com estatísticas
            
        Returns:
            Relatório formatado
        """
        relatorio = f"""
╔════════════════════════════════════════════════════╗
║         RELATÓRIO DE GERAÇÃO DE QR CODES           ║
╚════════════════════════════════════════════════════╝

Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
Evento: {self.nome_evento}
Pasta de Saída: {self.pasta_saida}

RESUMO:
───────────────────────────────────────────────────
  • Total de Convidados: {stats['total_convidados']}
  • QR Codes Gerados: {stats['qrcodes_gerados']}
  • Acompanhantes Processados: {stats['acompanhantes_processados']}
  • Erros: {stats['erros']}

DETALHES POR CONVIDADO:
───────────────────────────────────────────────────
"""
        
        for convidado in stats["convidados"]:
            relatorio += f"\n{convidado['nome']} ({convidado['email']})\n"
            relatorio += f"  QR Codes: {len(convidado['qrcodes'])}\n"
            for qr in convidado['qrcodes']:
                relatorio += f"    - {qr['tipo']:<15} Dia {qr['dia']}: {qr['arquivo']}\n"
        
        relatorio += f"""
INSTRUÇÕES:
───────────────────────────────────────────────────
1. Os arquivos de QR code estão em: {self.pasta_saida}
2. Registros em JSON: {self.pasta_saida / 'registro_qrcodes.json'}
3. Registros em CSV: {self.pasta_saida / 'registro_qrcodes.csv'}
4. Cada QR code é único e vinculado a uma pessoa e dia específico
5. Use um leitor de QR code (smartphone/scanner) para verificar no evento

Próximos Passos:
───────────────────────────────────────────────────
[ ] Revisar QR codes gerados na pasta de saída
[ ] Imprimir os QR codes para distribuição
[ ] Testar leitura com 2-3 QR codes reais
[ ] Configurar app de leitura na portaria
[ ] Treinar operadores da portaria
"""
        
        return relatorio


CSV_HEADERS = []

def carregar_csv(arquivo_csv: str) -> List[Dict]:
    """Carrega dados de um arquivo CSV e expõe os cabeçalhos em `CSV_HEADERS`."""
    global CSV_HEADERS
    dados = []
    try:
        import unicodedata
        def normalize_header(h: str) -> str:
            if not h:
                return ''
            s = h.strip().lower()
            s = unicodedata.normalize('NFKD', s)
            s = ''.join([c for c in s if not unicodedata.combining(c)])
            # replace non-alnum with underscore
            import re
            s = re.sub(r'[^a-z0-9]+', '_', s)
            s = s.strip('_')
            # map common variants
            if 'autoriz' in s:
                return 'autorizado'
            # prefer exact 'e-mail' or 'email' header to map to 'email'
            if s in ('e_mail', 'email'):
                return 'email'
            # 'endereco de e-mail' or similar -> map to endereco_email
            if 'endereco' in s and 'email' in s:
                return 'endereco_email'
            # map to 'email' only for genuine email columns (avoid 'email_status' or 'enviado_email')
            if ('email' in s or 'e_mail' in s) and ('status' not in s and 'enviado' not in s and 'opcao' not in s):
                return 'email'
            if 'nome' in s:
                return 'nome'
            if 'telefone' in s or 'whatsapp' in s:
                return 'telefone'
            if 'dia' in s:
                return 'dias'
            if 'acompanhante' in s:
                # map to first acompanhante name
                return 'acompanhante_1_nome'
            return s

        with open(arquivo_csv, 'r', encoding='utf-8') as f:
            leitor = csv.reader(f)
            rows = list(leitor)
            if not rows:
                print(f"❌ CSV vazio: {arquivo_csv}")
                return []
            raw_headers = rows[0]
            # build CSV_HEADERS ensuring unique keys (avoid collisions like multiple 'email')
            seen = {}
            CSV_HEADERS = []
            for h in raw_headers:
                k = normalize_header(h)
                if not k:
                    # fallback to positional key
                    k = f'col_{len(CSV_HEADERS)}'
                if k in seen:
                    # append numeric suffix to keep unique
                    seen[k] += 1
                    k = f"{k}_{seen[k]}"
                else:
                    seen[k] = 1
                CSV_HEADERS.append(k)
            for linha in rows[1:]:
                # mapear cabeçalho normalizado -> valor
                row_dict = {}
                for i, h in enumerate(CSV_HEADERS):
                    row_dict[h] = (linha[i] if i < len(linha) else '')
                dados.append(row_dict)
        print(f"✅ Carregados {len(dados)} registros de {arquivo_csv}")
    except Exception as e:
        print(f"❌ Erro ao carregar {arquivo_csv}: {e}")
    return dados


def exemplo_dados_teste() -> List[Dict]:
    """Retorna dados de exemplo para teste."""
    return [
        {
            "nome": "João Silva",
            "email": "joao@example.com",
            "dias": "1,2,3",  # Pode ser "1,2,3" ou lista Python
            "acompanhante_1_nome": "Maria Silva"
        },
        {
            "nome": "Ana Costa",
            "email": "ana@example.com",
            "dias": "1,2",
            "acompanhante_1_nome": "Pedro Costa",
            "acompanhante_2_nome": "Lucas Costa"
        },
        {
            "nome": "Carlos Oliveira",
            "email": "carlos@example.com",
            "dias": "2,3",
            "acompanhante_1_nome": ""
        },
    ]


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description='Gera QR codes únicos para convidados de evento',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python gerar_qrcodes.py
  python gerar_qrcodes.py convidados.csv
  python gerar_qrcodes.py convidados.csv ./qr_output
  python gerar_qrcodes.py --teste
        """
    )
    
    parser.add_argument('arquivo', nargs='?', default=None,
                       help='Arquivo CSV com dados dos convidados')
    parser.add_argument('pasta', nargs='?', default='./qrcodes',
                       help='Pasta de saída para os QR codes')
    parser.add_argument('--teste', action='store_true',
                       help='Usar dados de teste')
    parser.add_argument('--evento', default='EVENTO 2026',
                       help='Nome do evento (padrão: EVENTO 2026)')
    parser.add_argument('--incremental', action='store_true', help='Processar apenas convidados novos (pular emails já presentes no registro)')
    parser.add_argument('--batch-size', type=int, default=0, help='Processar em lotes de N convidados (0 = sem batching)')
    parser.add_argument('--limit', type=int, default=0, help='Limitar processamento a N convidados (0 = sem limite)')
    parser.add_argument('--dry-run', action='store_true', help='Simular execução sem gravar arquivos nem atualizar registro')
    parser.add_argument('--no-authorization', action='store_true', help='Desabilitar verificação de autorização (não recomendado)')
    parser.add_argument('--force', action='store_true', help='Forçar geração mesmo sem autorização (override)')
    
    args = parser.parse_args()
    
    print("\n" + "="*50)
    print("GERADOR DE QR CODES PARA EVENTO")
    print("="*50 + "\n")
    
    # Carregar dados
    if args.teste:
        print("🧪 Usando dados de teste...")
        dados = exemplo_dados_teste()
    elif args.arquivo:
        print(f"📂 Carregando {args.arquivo}...")
        dados = carregar_csv(args.arquivo)
    else:
        print("⚠️  Nenhum arquivo especificado. Use --teste para exemplo.")
        parser.print_help()
        return
    
    if not dados:
        print("❌ Nenhum dado para processar.")
        return
    
    # Processar dados
    print(f"\n📋 Processando {len(dados)} convidados...\n")
    
    # Converter string de dias para lista se necessário
    for convidado in dados:
        if isinstance(convidado.get('dias'), str):
            convidado['dias'] = convidado['dias'].split(',')
    gerador = GeradorQRCodes(pasta_saida=args.pasta, nome_evento=args.evento, dry_run=args.dry_run)

    # Se modo incremental, filtrar apenas convidados cujo email não está no registro
    if args.incremental:
        filtrados = []
        for c in dados:
            email = (c.get('email') or '').strip().lower()
            if not email:
                filtrados.append(c)
                continue
            if email in gerador.registro_map:
                continue
            filtrados.append(c)
        print(f"ℹ️ Modo incremental: {len(dados)-len(filtrados)} convidados pulados; {len(filtrados)} a processar")
        dados = filtrados

    # aplicar limit e batch-size
    if args.limit and args.limit > 0:
        dados = dados[:args.limit]
    if args.batch_size and args.batch_size > 0:
        dados = dados[:args.batch_size]

    if args.dry_run:
        print("ℹ️ Dry-run habilitado: arquivos não serão gravados nem registro exportado")

    # Por padrão, a geração exige autorização; use --no-authorization para desativar
    def is_authorized(row: dict) -> bool:
        # Priorizar a coluna A (primeira coluna) como fonte de autorização
        try:
            if CSV_HEADERS:
                primeira_chave = CSV_HEADERS[0]
                val = row.get(primeira_chave, '')
            else:
                # fallback: procurar chave 'autorizado' em qualquer lugar
                val = ''
                for k in row.keys():
                    if k and 'autoriz' in k.strip().lower():
                        val = row.get(k, '')
                        break
        except Exception:
            val = ''

        if not isinstance(val, str) or not val.strip():
            return False
        return val.strip().lower() == 'sim'

    if not args.no_authorization and not args.force:
        filtrados = []
        skipped = 0
        for c in dados:
            if is_authorized(c):
                filtrados.append(c)
            else:
                skipped += 1
        print(f"ℹ️ Requer autorização (padrão): {skipped} convidados pulados por não autorizados; {len(filtrados)} a processar")
        dados = filtrados

    stats = gerador.processar_convidados(dados)
    
    # Exportar registros (pular se dry-run)
    print("\n📊 Exportando registros...")
    if not args.dry_run:
        gerador.exportar_registro(stats, formato="json")
        gerador.exportar_registro(stats, formato="csv")
    else:
        print("ℹ️ Dry-run: exportação de registro pulada")
    
    # Exibir relatório
    relatorio = gerador.gerar_relatorio(stats)
    print(relatorio)
    
    # Salvar relatório
    arquivo_relatorio = gerador.pasta_saida / "relatorio_geracao.txt"
    with open(arquivo_relatorio, 'w', encoding='utf-8') as f:
        f.write(relatorio)
    
    print(f"✅ Relatório salvo em: {arquivo_relatorio}\n")


if __name__ == "__main__":
    main()
