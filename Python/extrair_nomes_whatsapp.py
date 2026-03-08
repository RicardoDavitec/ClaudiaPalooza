#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para Extrair Nomes de Chats WhatsApp
============================================
Extrai nomes únicos de um chat exportado do WhatsApp e gera CSV.

Uso:
    python extrair_nomes_whatsapp.py export_chat.txt --saida convidados.csv
    python extrair_nomes_whatsapp.py export_chat.txt --formato json

Formato esperado do arquivo exportado:
    01/04/2026, 10:30 - João Silva: Confirmado!
    01/04/2026, 10:35 - Maria Santos: Eu também!
"""

import re
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Set, Dict
import argparse


class ExtractorWhatsApp:
    """Extrator de nomes de chats WhatsApp."""
    
    def __init__(self, arquivo_txt: str):
        """
        Inicializa o extrator.
        
        Args:
            arquivo_txt: Caminho do arquivo exportado do WhatsApp
        """
        self.arquivo = Path(arquivo_txt)
        
        if not self.arquivo.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {arquivo_txt}")
        
        self.nomes_unicos = set()
        self.linhas_processadas = 0
        self.linhas_invalidas = 0
    
    def extrair_nomes(self) -> Set[str]:
        """
        Extrai nomes únicos do chat.
        
        Padrão: "DATA, HORA - Nome: Mensagem"
        
        Returns:
            Set com nomes únicos
        """
        try:
            with open(self.arquivo, 'r', encoding='utf-8') as f:
                for linha in f:
                    linha = linha.strip()
                    
                    if not linha:
                        continue
                    
                    # Padrão: "01/04/2026, 10:30 - Nome: Mensagem"
                    # ou "01/04/2026, 10:30 - Nome da Pessoa: Olá!"
                    
                    # Tentar encontrar padrão de timestamp + nome
                    match = re.search(r'^\d{1,2}/\d{1,2}/\d{4},\s+\d{1,2}:\d{2}\s*-\s+(.+?):\s+', linha)
                    
                    if match:
                        nome = match.group(1).strip()
                        
                        # Filtrar mensagens de sistema
                        if nome not in [
                            'Mensagens de mídia',
                            'Este é um chat criptografado',
                            'Mensagem deletada',
                            '<Mídia omitida>',
                            'contato',
                            'chamada',
                        ]:
                            # Validar se parece ser um nome real
                            if self._validar_nome(nome):
                                self.nomes_unicos.add(nome)
                                self.linhas_processadas += 1
                    else:
                        self.linhas_invalidas += 1
        
        except Exception as e:
            print(f"❌ Erro ao processar arquivo: {e}")
        
        return self.nomes_unicos
    
    def _validar_nome(self, nome: str) -> bool:
        """
        Valida se o texto é provavelmente um nome.
        
        Args:
            nome: Texto a validar
            
        Returns:
            True se parece ser um nome
        """
        # Nome deve ter pelo menos 2 caracteres
        if len(nome) < 2:
            return False
        
        # Nome não deve ser apenas números
        if nome.isdigit():
            return False
        
        # Nome não deve ter caracteres especiais demais
        special_chars = len(re.findall(r'[!@#$%^&*(){}[\]:";\'<>,.?/|\\]', nome))
        if special_chars > 2:
            return False
        
        # Nome deve ter pelo menos uma letra
        if not re.search(r'[a-záàâãéèêíïóôõöúçñA-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ]', nome):
            return False
        
        return True
    
    def gerar_csv(self, arquivo_saida: str, incluir_email: bool = True):
        """
        Gera arquivo CSV com nomes extraídos.
        
        Args:
            arquivo_saida: Caminho do arquivo CSV
            incluir_email: Se incluir colunas vazias para email/telefone
        """
        try:
            nomes_ordenados = sorted(list(self.nomes_unicos))
            
            with open(arquivo_saida, 'w', newline='', encoding='utf-8') as f:
                if incluir_email:
                    writer = csv.writer(f)
                    writer.writerow(['nome', 'email', 'telefone', 'cpf', 'notas'])
                    for nome in nomes_ordenados:
                        writer.writerow([nome, '', '', '', ''])
                else:
                    writer = csv.writer(f)
                    writer.writerow(['nome'])
                    for nome in nomes_ordenados:
                        writer.writerow([nome])
            
            print(f"✅ Arquivo CSV gerado: {arquivo_saida}")
            return True
        
        except Exception as e:
            print(f"❌ Erro ao gerar CSV: {e}")
            return False
    
    def gerar_json(self, arquivo_saida: str):
        """
        Gera arquivo JSON com nomes extraídos.
        
        Args:
            arquivo_saida: Caminho do arquivo JSON
        """
        try:
            dados = {
                "data_extracao": datetime.now().isoformat(),
                "total_nomes": len(self.nomes_unicos),
                "linhas_processadas": self.linhas_processadas,
                "linhas_invalidas": self.linhas_invalidas,
                "nomes": sorted(list(self.nomes_unicos))
            }
            
            with open(arquivo_saida, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Arquivo JSON gerado: {arquivo_saida}")
            return True
        
        except Exception as e:
            print(f"❌ Erro ao gerar JSON: {e}")
            return False
    
    def gerar_relatorio(self) -> str:
        """Gera relatório de extração."""
        relatorio = f"""
╔════════════════════════════════════════════════════╗
║        RELATÓRIO DE EXTRAÇÃO - WHATSAPP            ║
╚════════════════════════════════════════════════════╝

Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
Arquivo: {self.arquivo}

ESTATÍSTICAS:
───────────────────────────────────────────────────
  • Total de Nomes Únicos: {len(self.nomes_unicos)}
  • Linhas Válidas Processadas: {self.linhas_processadas}
  • Linhas Inválidas: {self.linhas_invalidas}

NOMES EXTRAÍDOS:
───────────────────────────────────────────────────
"""
        
        nomes_ordenados = sorted(list(self.nomes_unicos))
        for idx, nome in enumerate(nomes_ordenados, 1):
            relatorio += f"{idx:3d}. {nome}\n"
        
        relatorio += f"""

PRÓXIMAS AÇÕES:
───────────────────────────────────────────────────
1. Revisar nomes extraídos
2. Adicionar emails e telefones faltantes
3. Remover duplicatas ou nomes incorretos
4. Usar arquivo gerado com scripts de envio
5. Enviar convites via WhatsApp/SMS ou Email

DICA:
───────────────────────────────────────────────────
Se alguns nomes estão faltando ou incorretos:
1. Adicione manualmente ao CSV
2. Corrija nomes com erros de digitação
3. Peça para convidados preencherem dados no Google Form
"""
        
        return relatorio


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description='Extrair nomes de chat exportado do WhatsApp',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python extrair_nomes_whatsapp.py export_chat.txt --saida convidados.csv
  python extrair_nomes_whatsapp.py export_chat.txt --formato json
  python extrair_nomes_whatsapp.py export_chat.txt --formato ambos

Como exportar chat do WhatsApp:
  Android: Chat → Menu → Exportar chat → Sem mídia
  iPhone: Chat → Swipe left → Info → Exportar chat
        """
    )
    
    parser.add_argument('arquivo', help='Arquivo TXT exportado do WhatsApp')
    parser.add_argument('--saida', default='convidados_extraidos.csv',
                       help='Arquivo CSV de saída')
    parser.add_argument('--formato', choices=['csv', 'json', 'ambos'],
                       default='csv',
                       help='Formato do arquivo de saída')
    parser.add_argument('--relatorio', action='store_true',
                       help='Exibir relatório')
    
    args = parser.parse_args()
    
    print("\\n" + "="*50)
    print("EXTRATOR DE NOMES - WHATSAPP")
    print("="*50 + "\\n")
    
    try:
        extrator = ExtractorWhatsApp(args.arquivo)
        
        print(f"📂 Processando {args.arquivo}...\\n")
        nomes = extrator.extrair_nomes()
        
        print(f"✅ Encontrados {len(nomes)} nomes únicos\\n")
        
        # Gerar saídas
        if args.formato in ['csv', 'ambos']:
            extrator.gerar_csv(args.saida)
        
        if args.formato in ['json', 'ambos']:
            arquivo_json = args.saida.replace('.csv', '.json')
            extrator.gerar_json(arquivo_json)
        
        # Exibir relatório
        if args.relatorio:
            relatorio = extrator.gerar_relatorio()
            print(relatorio)
            
            # Salvar relatório
            arquivo_rel = args.saida.replace('.csv', '_relatorio.txt')
            with open(arquivo_rel, 'w', encoding='utf-8') as f:
                f.write(relatorio)
            print(f"✅ Relatório salvo: {arquivo_rel}\\n")
    
    except FileNotFoundError as e:
        print(f"❌ {e}")
    except Exception as e:
        print(f"❌ Erro: {e}")


if __name__ == "__main__":
    main()
