#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Envio de Convites via WhatsApp e SMS
===============================================
Envia convites para convidados via WhatsApp ou SMS com link do Google Forms.

Requisitos:
    pip install twilio python-dotenv

Uso:
    python enviar_convites_whatsapp_sms.py --arquivo convidados.csv --metodo whatsapp --teste
    python enviar_convites_whatsapp_sms.py --arquivo convidados.csv --metodo sms --enviar

Configuração:
    Crie arquivo .env com:
    TWILIO_ACCOUNT_SID=seu_sid
    TWILIO_AUTH_TOKEN=seu_token
    TWILIO_WHATSAPP_NUMBER=whatsapp:+55XXXXXXXXX  (ou vazio para SMS)
    TWILIO_SMS_FROM=+551133334444  (seu número SMS)
    EVENTO_LINK=https://bit.ly/seu_evento
"""

import os
import sys
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple
import argparse
import re

try:
    from twilio.rest import Client
    from dotenv import load_dotenv
except ImportError:
    print("❌ Erro: Bibliotecas necessárias não instaladas.")
    print("Execute: pip install twilio python-dotenv")
    sys.exit(1)


class GerenciadorConvites:
    """Gerenciador de envio de convites via WhatsApp/SMS."""
    
    def __init__(self, arquivo_env: str = ".env"):
        """
        Inicializa o gerenciador.
        
        Args:
            arquivo_env: Arquivo com configurações
        """
        load_dotenv(arquivo_env)
        
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_whatsapp = os.getenv('TWILIO_WHATSAPP_NUMBER', '')
        self.twilio_sms = os.getenv('TWILIO_SMS_FROM', '')
        self.evento_link = os.getenv('EVENTO_LINK', '')
        self.evento_nome = os.getenv('EVENTO_NOME', 'Evento 2026')
        
        # Validar configuração
        if not all([self.account_sid, self.auth_token, self.evento_link]):
            print("⚠️  Aviso: Arquivo .env incompleto")
            print("   Defina: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, EVENTO_LINK")
        
        self.client = Client(self.account_sid, self.auth_token) if self.account_sid else None
        self.convites_enviados = []
        self.erros = []
    
    def formatar_telefone(self, telefone: str, pais: str = "55") -> str:
        """
        Formata número de telefone para padrão internacional.
        
        Args:
            telefone: Número em qualquer formato
            pais: Código do país (padrão Brasil: 55)
            
        Returns:
            Número formatado com código do país
        """
        # Remover caracteres especiais
        telefone_limpo = re.sub(r'\D', '', telefone)
        
        # Se já tem código do país, retornar
        if telefone_limpo.startswith(pais):
            return telefone_limpo
        
        # Remover leading zeros
        telefone_limpo = telefone_limpo.lstrip('0')
        
        # Adicionar código do país
        if len(telefone_limpo) >= 10:
            return pais + telefone_limpo
        
        return None
    
    def criar_mensagem_whatsapp(self, nome: str) -> str:
        """Cria mensagem para WhatsApp."""
        mensagem = f"""Olá {nome}! 👋

Você está convidado para o *{self.evento_nome}*! 🎉

📅 *Datas:* 10-12 de Abril de 2026
🕐 *Horário:* 09:00 - 18:00
📍 *Local:* Centro de Convenções

Confirme sua presença clicando no link abaixo:

{self.evento_link}

Qualquer dúvida, entre em contato!

Obrigado!"""
        
        return mensagem
    
    def criar_mensagem_sms(self, nome: str) -> str:
        """Cria mensagem para SMS."""
        mensagem = f"""Oi {nome}! Você está convidado para {self.evento_nome} (10-12 de Abril)! Confirme: {self.evento_link}"""
        
        return mensagem
    
    def enviar_whatsapp(self, telefone: str, mensagem: str) -> Tuple[bool, str]:
        """
        Envia mensagem via WhatsApp.
        
        Args:
            telefone: Número com código do país
            mensagem: Texto da mensagem
            
        Returns:
            (sucesso, message_id ou erro)
        """
        if not self.client:
            return False, "Cliente Twilio não configurado"
        
        if not self.twilio_whatsapp:
            return False, "Número WhatsApp Twilio não configurado"
        
        try:
            msg = self.client.messages.create(
                from_=self.twilio_whatsapp,
                body=mensagem,
                to=f"whatsapp:+{telefone}"
            )
            return True, msg.sid
        except Exception as e:
            return False, str(e)
    
    def enviar_sms(self, telefone: str, mensagem: str) -> Tuple[bool, str]:
        """
        Envia mensagem via SMS.
        
        Args:
            telefone: Número com código do país
            mensagem: Texto da mensagem
            
        Returns:
            (sucesso, message_id ou erro)
        """
        if not self.client:
            return False, "Cliente Twilio não configurado"
        
        if not self.twilio_sms:
            return False, "Número SMS Twilio não configurado"
        
        try:
            msg = self.client.messages.create(
                from_=self.twilio_sms,
                body=mensagem,
                to=f"+{telefone}"
            )
            return True, msg.sid
        except Exception as e:
            return False, str(e)
    
    def processar_lote(self, arquivo_csv: str, metodo: str = "whatsapp",
                       teste: bool = False) -> Dict:
        """
        Processa envio em lote.
        
        Args:
            arquivo_csv: Arquivo com lista de convidados
            metodo: 'whatsapp' ou 'sms'
            teste: Se True, apenas exibe sem enviar
            
        Returns:
            Dicionário com estatísticas
        """
        stats = {
            "total": 0,
            "enviados": 0,
            "falhados": 0,
            "telefonos_invalidos": 0,
            "detalhes": []
        }
        
        try:
            with open(arquivo_csv, 'r', encoding='utf-8') as f:
                leitor = csv.DictReader(f)
                
                for idx, linha in enumerate(leitor, 1):
                    stats["total"] += 1
                    
                    nome = linha.get('nome', 'Convidado').strip()
                    telefone_raw = linha.get('telefone', '').strip()
                    
                    if not telefone_raw:
                        print(f"⚠️  Linha {idx}: Telefone vazio para {nome}")
                        stats["telefonos_invalidos"] += 1
                        continue
                    
                    # Formatar telefone
                    telefone = self.formatar_telefone(telefone_raw)
                    
                    if not telefone:
                        print(f"❌ Linha {idx}: Telefone inválido para {nome}: {telefone_raw}")
                        stats["telefonos_invalidos"] += 1
                        continue
                    
                    # Criar mensagem
                    if metodo == "whatsapp":
                        mensagem = self.criar_mensagem_whatsapp(nome)
                    else:
                        mensagem = self.criar_mensagem_sms(nome)
                    
                    # Modo teste
                    if teste:
                        print(f"\n[TESTE {idx}] {nome}")
                        print(f"  Telefone: +{telefone}")
                        print(f"  Método: {metodo.upper()}")
                        print(f"  Mensagem preview: {mensagem[:100]}...")
                        
                        stats["enviados"] += 1
                        stats["detalhes"].append({
                            "nome": nome,
                            "telefone": telefone,
                            "metodo": metodo,
                            "status": "teste",
                            "message_id": "N/A"
                        })
                    else:
                        # Enviar de verdade
                        if metodo == "whatsapp":
                            sucesso, resultado = self.enviar_whatsapp(telefone, mensagem)
                        else:
                            sucesso, resultado = self.enviar_sms(telefone, mensagem)
                        
                        if sucesso:
                            print(f"✅ {idx:3d}. {nome:<25} (+{telefone}) - {metodo.upper()}")
                            stats["enviados"] += 1
                            stats["detalhes"].append({
                                "nome": nome,
                                "telefone": telefone,
                                "metodo": metodo,
                                "status": "enviado",
                                "message_id": resultado
                            })
                        else:
                            print(f"❌ {idx:3d}. {nome:<25} - Erro: {resultado}")
                            stats["falhados"] += 1
                            stats["detalhes"].append({
                                "nome": nome,
                                "telefone": telefone,
                                "metodo": metodo,
                                "status": "erro",
                                "erro": resultado
                            })
        
        except Exception as e:
            print(f"❌ Erro ao processar arquivo: {e}")
        
        return stats
    
    def gerar_relatorio(self, stats: Dict) -> str:
        """Gera relatório do envio."""
        relatorio = f"""
╔════════════════════════════════════════════════════╗
║        RELATÓRIO DE ENVIO DE CONVITES              ║
╚════════════════════════════════════════════════════╝

Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
Evento: {self.evento_nome}

RESUMO:
───────────────────────────────────────────────────
  • Total de Convidados: {stats['total']}
  • Convites Enviados: {stats['enviados']}
  • Falhas: {stats['falhados']}
  • Telefones Inválidos: {stats['telefonos_invalidos']}
  • Taxa de Sucesso: {(stats['enviados'] / max(stats['total'], 1) * 100):.1f}%

DETALHES:
───────────────────────────────────────────────────
"""
        
        for detalhe in stats['detalhes']:
            status_icon = "✅" if detalhe['status'] == "enviado" else "❌" if detalhe['status'] == "erro" else "📋"
            relatorio += f"\n{status_icon} {detalhe['nome']:<20} (+{detalhe['telefone']})"
            
            if detalhe['status'] == "erro":
                relatorio += f"\n   ⚠️  {detalhe.get('erro', 'Erro desconhecido')}"
            elif detalhe['status'] == "teste":
                relatorio += f"\n   🧪 ID: {detalhe.get('message_id', 'N/A')}"
            else:
                relatorio += f"\n   ID: {detalhe.get('message_id', 'N/A')}"
        
        relatorio += f"""

PRÓXIMAS AÇÕES:
───────────────────────────────────────────────────
[ ] Verificar convidados que não receberam
[ ] Tentar reenviar para falhas
[ ] Monitorar confirmações no Google Forms
[ ] Preparar lembretes para não-respondentes
[ ] Gerar QR codes após confirações

CUSTO (se usado Twilio):
───────────────────────────────────────────────────
  • {stats['enviados']} mensagens × R$ 0,15 = R$ {stats['enviados'] * 0.15:.2f}
"""
        
        return relatorio
    
    def salvar_relatorio(self, stats: Dict, pasta_saida: str = "./relatorios"):
        """Salva relatório em arquivo."""
        pasta = Path(pasta_saida)
        pasta.mkdir(exist_ok=True)
        
        relatorio = self.gerar_relatorio(stats)
        
        # Salvar texto
        arquivo_txt = pasta / f"relatorio_convites_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(arquivo_txt, 'w', encoding='utf-8') as f:
            f.write(relatorio)
        
        # Salvar JSON
        arquivo_json = pasta / f"convites_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(arquivo_json, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        return arquivo_txt, arquivo_json


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description='Enviar convites para convidados via WhatsApp ou SMS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python enviar_convites_whatsapp_sms.py --arquivo convidados.csv --metodo whatsapp --teste
  python enviar_convites_whatsapp_sms.py --arquivo convidados.csv --metodo sms --enviar
  python enviar_convites_whatsapp_sms.py --arquivo convidados.csv --metodo whatsapp --enviar

Arquivo .env obrigatório:
  TWILIO_ACCOUNT_SID=seu_sid
  TWILIO_AUTH_TOKEN=seu_token
  TWILIO_WHATSAPP_NUMBER=whatsapp:+55XXXXXXXXX
  TWILIO_SMS_FROM=+551133334444
  EVENTO_LINK=https://bit.ly/seu_evento
  EVENTO_NOME=Nome do Evento
        """
    )
    
    parser.add_argument('--arquivo', required=True,
                       help='Arquivo CSV com dados dos convidados')
    parser.add_argument('--metodo', choices=['whatsapp', 'sms'],
                       default='whatsapp',
                       help='Método de envio (padrão: whatsapp)')
    parser.add_argument('--env', default='.env',
                       help='Arquivo de configuração .env')
    parser.add_argument('--teste', action='store_true',
                       help='Modo teste (não envia realmente)')
    parser.add_argument('--enviar', action='store_true',
                       help='Realmente enviar mensagens')
    parser.add_argument('--saida', default='./relatorios',
                       help='Pasta para relatórios')
    
    args = parser.parse_args()
    
    print("\\n" + "="*50)
    print("ENVIO DE CONVITES - WHATSAPP/SMS")
    print("="*50 + "\\n")
    
    # Inicializar gerenciador
    gerenciador = GerenciadorConvites(arquivo_env=args.env)
    
    # Modo teste ou envio real
    if args.teste:
        print("🧪 MODO TESTE - Mensagens NÃO serão enviadas\\n")
        stats = gerenciador.processar_lote(
            args.arquivo,
            metodo=args.metodo,
            teste=True
        )
    elif args.enviar:
        print(f"📤 Enviando {args.metodo.upper()}...\\n")
        stats = gerenciador.processar_lote(
            args.arquivo,
            metodo=args.metodo,
            teste=False
        )
    else:
        print("⚠️  Use --teste para visualizar ou --enviar para realmente enviar\\n")
        return
    
    # Gerar relatório
    relatorio = gerenciador.gerar_relatorio(stats)
    print(relatorio)
    
    # Salvar
    arquivo_txt, arquivo_json = gerenciador.salvar_relatorio(stats, args.saida)
    print(f"\\n✅ Relatório salvo em: {arquivo_txt}")


if __name__ == "__main__":
    main()
