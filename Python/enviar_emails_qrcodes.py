#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Envio Automatizado de Emails com QR Codes
====================================================
Envia emails de confirmação e QR codes aos convidados.

Requisitos:
    pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client

Uso:
    python enviar_emails_qrcodes.py --arquivo convidados.csv --teste
    python enviar_emails_qrcodes.py --arquivo convidados.csv --enviar
"""

import os
import sys
import csv
import json
import smtplib
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders


class GerenciadorEmails:
    """Gerenciador de envio de emails com QR codes."""
    
    def __init__(self, arquivo_qrcodes: str = "registro_qrcodes.json",
                 pasta_qrcodes: str = "./qrcodes",
                 smtp_config: Optional[Dict] = None):
        """
        Inicializa o gerenciador de emails.
        
        Args:
            arquivo_qrcodes: Arquivo JSON com registro dos QR codes
            pasta_qrcodes: Pasta contendo as imagens dos QR codes
            smtp_config: Dicionário com configurações SMTP
        """
        self.arquivo_qrcodes = arquivo_qrcodes
        self.pasta_qrcodes = Path(pasta_qrcodes)
        self.smtp_config = smtp_config or self._config_padrao()
        self.dados_qrcodes = self._carregar_qrcodes()
        self.emails_enviados = []
        
    def _config_padrao(self) -> Dict:
        """Retorna configuração padrão de SMTP (Gmail)."""
        # IMPORTANTE: Para usar com Gmail, ativar "Senhas de Aplicativos"
        # https://myaccount.google.com/apppasswords
        return {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "remetente_email": "seu_email@gmail.com",
            "remetente_senha": "sua_senha_app",  # Usar senha de app, não senha real
            "remetente_nome": "Evento 2026"
        }
    
    def _carregar_qrcodes(self) -> Dict:
        """Carrega dados dos QR codes gerados."""
        if os.path.exists(self.arquivo_qrcodes):
            try:
                with open(self.arquivo_qrcodes, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                print(f"✅ Registro de QR codes carregado")
                return dados
            except Exception as e:
                print(f"❌ Erro ao carregar QR codes: {e}")
        return {}
    
    def _criar_html_email(self, nome: str, email: str, 
                         confirmacao_dias: List[str],
                         acompanhantes: List[str] = None) -> str:
        """
        Cria conteúdo HTML do email.
        
        Args:
            nome: Nome do convidado
            email: Email do convidado
            confirmacao_dias: Lista de dias confirmados
            acompanhantes: Lista com nomes dos acompanhantes
            
        Returns:
            HTML formatado
        """
        dias_text = ", ".join([f"Dia {d}" for d in confirmacao_dias])
        acompanhantes_text = ""
        
        if acompanhantes:
            acompanhantes_text = f"""
            <h3 style=\"color: #333; margin-top: 20px;\">Acompanhantes:</h3>
            <ul>
            """
            for acomp in acompanhantes:
                acompanhantes_text += f"<li>{acomp}</li>"
            acompanhantes_text += "</ul>"
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset=\"UTF-8\">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
        }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .content {{ background: #f9f9f9; padding: 20px; margin-top: 20px; border-radius: 5px; }}
        .confirmacao {{ background: #e8f5e9; padding: 15px; border-left: 4px solid #4caf50; margin: 15px 0; }}
        .info-box {{
            background: white;
            border: 1px solid #ddd;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .qr-section {{
            text-align: center;
            margin: 20px 0;
            padding: 20px;
            background: white;
            border: 2px dashed #667eea;
            border-radius: 5px;
        }}
        .qr-section img {{ max-width: 300px; margin: 10px 0; }}
        .footer {{
            text-align: center;
            font-size: 12px;
            color: #666;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
        .alerta {{ color: #d32f2f; font-weight: bold; }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div class=\"container\">
        <div class=\"header\">
            <h1>🎉 Evento 2026</h1>
            <p>Confirmação de Presença e QR Code de Acesso</p>
        </div>
        
        <div class=\"content\">
            <h2>Olá, {nome}!</h2>
            
            <p>Agradecemos sua confirmação de presença no <strong>Evento 2026</strong>.</p>
            
            <div class=\"confirmacao\">
                <h3>✅ Sua Confirmação</h3>
                <p><strong>Dias confirmados:</strong> {dias_text}</p>
                <p><strong>Email registrado:</strong> {email}</p>
            </div>
            
            {acompanhantes_text}
            
            <div class=\"qr-section\">
                <h3>📱 Seu QR Code de Acesso</h3>
                <p>Apresente este QR code na portaria do evento.</p>
                <p class=\"alerta\">⚠️ IMPORTANTE: Cada QR code é único e intransferível</p>
                <p><em>(Imagens anexadas ao email)</em></p>
            </div>
            
            <div class=\"info-box\">
                <h3>ℹ️ Informações Importantes</h3>
                <ul>
                    <li>Apresente o QR code na portaria ao chegar</li>
                    <li>Cada QR code é válido apenas para o dia indicado</li>
                    <li>Documentos podem ser solicitados para verificação</li>
                    <li>Acompanhantes precisam estar cadastrados</li>
                    <li>Chegue com antecedência para verificação</li>
                </ul>
            </div>
            
            <div class=\"info-box\">
                <h3>📍 Local e Data</h3>
                <p><strong>Evento:</strong> Evento 2026<br>
                   <strong>Datas:</strong> 10 a 12 de Abril de 2026<br>
                   <strong>Local:</strong> Centro de Convenções (a confirmar)<br>
                   <strong>Horário:</strong> 09:00 - 18:00</p>
            </div>
            
            <div class=\"info-box\">
                <h3>❓ Dúvidas?</h3>
                <p>Entre em contato conosco:<br>
                   Email: <strong>evento2026@example.com</strong><br>
                   Telefone: <strong>(11) 3000-0000</strong></p>
            </div>
        </div>
        
        <div class=\"footer\">
            <p>Email enviado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
            <p>Este é um email automatizado. Não responda diretamente.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    def _obter_qrcodes_convidado(self, nome: str, email: str) -> List[Dict]:
        """
        Obtém QR codes de um convidado do registro.
        
        Args:
            nome: Nome do convidado
            email: Email do convidado
            
        Returns:
            Lista de dicionários com informações dos QR codes
        """
        convidados = self.dados_qrcodes.get("convidados", [])
        
        for convidado in convidados:
            if convidado.get("nome") == nome and convidado.get("email") == email:
                return convidado.get("qrcodes", [])
        
        return []
    
    def enviar_email(self, email_destinatario: str, nome: str, 
                    confirmacao_dias: List[str],
                    qrcodes_info: List[Dict],
                    acompanhantes: List[str] = None,
                    teste: bool = False) -> bool:
        """
        Envia email com QR code.
        
        Args:
            email_destinatario: Email do convidado
            nome: Nome do convidado
            confirmacao_dias: Dias confirmados
            qrcodes_info: Informações dos QR codes
            acompanhantes: Nomes dos acompanhantes
            teste: Se True, apenas exibe, não envia
            
        Returns:
            True se enviado com sucesso
        """
        try:
            # Criar mensagem
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🎉 Seu QR Code - Evento 2026"
            msg['From'] = f"{self.smtp_config['remetente_nome']} <{self.smtp_config['remetente_email']}>"
            msg['To'] = email_destinatario
            
            # HTML do email
            html_content = self._criar_html_email(
                nome=nome,
                email=email_destinatario,
                confirmacao_dias=confirmacao_dias,
                acompanhantes=acompanhantes
            )
            
            # Anexar HTML
            msg.attach(MIMEText(html_content, 'html'))
            
            # Anexar imagens de QR codes
            for qr_info in qrcodes_info:
                arquivo_qr = self.pasta_qrcodes / qr_info.get("arquivo", "")
                
                if arquivo_qr.exists():
                    try:
                        with open(arquivo_qr, 'rb') as anexo:
                            img = MIMEImage(anexo.read())
                            img.add_header('Content-ID', f'<{qr_info[\"arquivo\"]}>')
                            img.add_header('Content-Disposition', 'attachment', 
                                         filename=qr_info.get("arquivo", "qrcode.png"))
                            msg.attach(img)
                    except Exception as e:
                        print(f"⚠️  Aviso: Não foi possível anexar {arquivo_qr}: {e}")
            
            # Modo teste
            if teste:
                print(f"\n📧 [TESTE] Email para {email_destinatario}:")
                print(f"   De: {msg['From']}")
                print(f"   Para: {email_destinatario}")
                print(f"   Assunto: {msg['Subject']}")
                print(f"   QR codes anexados: {len(qrcodes_info)}")
                return True
            
            # Enviar email
            print(f"📧 Enviando para {email_destinatario}...", end=" ")
            
            with smtplib.SMTP(self.smtp_config['smtp_server'], 
                            self.smtp_config['smtp_port']) as server:
                server.starttls()
                server.login(
                    self.smtp_config['remetente_email'],
                    self.smtp_config['remetente_senha']
                )
                server.send_message(msg)
            
            print("✅")
            self.emails_enviados.append({
                "para": email_destinatario,
                "nome": nome,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao enviar para {email_destinatario}: {e}")
            return False
    
    def enviar_lote(self, arquivo_convidados: str, teste: bool = False) -> Dict:
        """
        Envia emails para lote de convidados.
        
        Args:
            arquivo_convidados: Arquivo CSV com dados dos convidados
            teste: Se True, apenas exibe, não envia
            
        Returns:
            Dicionário com estatísticas
        """
        stats = {
            "total_convidados": 0,
            "emails_enviados": 0,
            "emails_falhados": 0,
            "detalhes": []
        }
        
        try:
            with open(arquivo_convidados, 'r', encoding='utf-8') as f:
                leitor = csv.DictReader(f)
                
                for idx, linha in enumerate(leitor, 1):
                    stats["total_convidados"] += 1
                    
                    nome = linha.get('nome', 'Convidado').strip()
                    email = linha.get('email', '').strip()
                    dias = linha.get('dias', '1,2,3')
                    
                    if not email:
                        print(f"⚠️  Linha {idx}: Email vazio para {nome}")
                        stats["emails_falhados"] += 1
                        continue
                    
                    # Converter dias para lista
                    if isinstance(dias, str):
                        dias_list = [d.strip() for d in dias.split(',')]
                    else:
                        dias_list = dias
                    
                    # Obter acompanhantes
                    acompanhantes = []
                    for i in range(1, 3):
                        acomp = linha.get(f'acompanhante_{i}_nome', '').strip()
                        if acomp:
                            acompanhantes.append(acomp)
                    
                    # Obter QR codes
                    qrcodes = self._obter_qrcodes_convidado(nome, email)
                    
                    if not qrcodes:
                        print(f"⚠️  Linha {idx}: Nenhum QR code encontrado para {nome}")
                        stats["emails_falhados"] += 1
                        continue
                    
                    # Enviar email
                    sucesso = self.enviar_email(
                        email_destinatario=email,
                        nome=nome,
                        confirmacao_dias=dias_list,
                        qrcodes_info=qrcodes,
                        acompanhantes=acompanhantes,
                        teste=teste
                    )
                    
                    if sucesso:
                        stats["emails_enviados"] += 1
                    else:
                        stats["emails_falhados"] += 1
                    
                    stats["detalhes"].append({
                        "nome": nome,
                        "email": email,
                        "sucesso": sucesso
                    })
                    
        except Exception as e:
            print(f"❌ Erro ao processar arquivo: {e}")
        
        return stats
    
    def gerar_relatorio(self, stats: Dict) -> str:
        """Gera relatório de envio de emails."""
        relatorio = f"""
╔════════════════════════════════════════════════════╗
║          RELATÓRIO DE ENVIO DE EMAILS              ║
╚════════════════════════════════════════════════════╝

Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

RESUMO:
───────────────────────────────────────────────────
  • Total de Convidados: {stats['total_convidados']}
  • Emails Enviados: {stats['emails_enviados']}
  • Emails Falhados: {stats['emails_falhados']}
  • Taxa de Sucesso: {(stats['emails_enviados'] / max(stats['total_convidados'], 1) * 100):.1f}%

DETALHES:
───────────────────────────────────────────────────
"""
        
        for detalhe in stats['detalhes']:
            status = "✅" if detalhe['sucesso'] else "❌"
            relatorio += f"\n{status} {detalhe['nome']:<30} {detalhe['email']}"
        
        relatorio += f"""

PRÓXIMAS AÇÕES:
───────────────────────────────────────────────────
[ ] Verificar emails falhados
[ ] Reenviar para emails que falharam
[ ] Confirmar recebimento dos convidados
[ ] Atualizar lista de presença
"""
        
        return relatorio


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description='Envia emails com QR codes para convidados',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python enviar_emails_qrcodes.py --arquivo convidados.csv --teste
  python enviar_emails_qrcodes.py --arquivo convidados.csv --enviar
  python enviar_emails_qrcodes.py --config config.json --enviar
        """
    )
    
    parser.add_argument('--arquivo', required=True,
                       help='Arquivo CSV com dados dos convidados')
    parser.add_argument('--qrcodes', default='registro_qrcodes.json',
                       help='Arquivo com registro dos QR codes')
    parser.add_argument('--pasta-qrcodes', default='./qrcodes',
                       help='Pasta contendo os arquivos de QR code')
    parser.add_argument('--config', 
                       help='Arquivo JSON com configuração de SMTP')
    parser.add_argument('--teste', action='store_true',
                       help='Modo teste (não envia realmente)')
    parser.add_argument('--enviar', action='store_true',
                       help='Realmente enviar emails')
    
    args = parser.parse_args()
    
    print("\\n" + "="*50)
    print("ENVIO DE EMAILS COM QR CODES")
    print("="*50 + "\\n")
    
    # Carregar configuração SMTP
    smtp_config = None
    if args.config:
        try:
            with open(args.config, 'r') as f:
                smtp_config = json.load(f)
            print(f"✅ Configuração SMTP carregada de {args.config}")
        except Exception as e:
            print(f"❌ Erro ao carregar configuração: {e}")
            return
    
    # Inicializar gerenciador
    gerenciador = GerenciadorEmails(
        arquivo_qrcodes=args.qrcodes,
        pasta_qrcodes=args.pasta_qrcodes,
        smtp_config=smtp_config
    )
    
    # Enviar lote
    if args.teste:
        print("🧪 Modo TESTE (emails não serão realmente enviados)\\n")
    elif not args.enviar:
        print("⚠️  Use --teste para visualizar ou --enviar para realmente enviar\\n")
        return
    
    print(f"📧 Processando {args.arquivo}...\\n")
    stats = gerenciador.enviar_lote(args.arquivo, teste=args.teste or not args.enviar)
    
    # Gerar relatório
    relatorio = gerenciador.gerar_relatorio(stats)
    print(relatorio)


if __name__ == "__main__":
    main()
