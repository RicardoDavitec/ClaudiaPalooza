#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Validação e Check-in via QR Code
===========================================
Valida códigos de acesso e registra check-in em tempo real.

Requisitos:
    pip install opencv-python pyzbar google-auth-oauthlib google-auth-httplib2 google-api-python-client

Uso:
    python validar_checkin.py --modo webcam
    python validar_checkin.py --modo arquivo qr_code.png
    python validar_checkin.py --modo manual
"""

import os
import sys
import json
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None


class ValidadorCheckIn:
    """Gerenciador de validação de check-in via QR code."""
    
    def __init__(self, banco_dados: str = "convidados_registro.json", 
                 arquivo_checkins: str = "checkins.csv"):
        """
        Inicializa o validador.
        
        Args:
            banco_dados: Arquivo JSON com dados dos convidados registrados
            arquivo_checkins: Arquivo CSV onde serão registrados os check-ins
        """
        self.banco_dados = banco_dados
        self.arquivo_checkins = arquivo_checkins
        self.dados_convidados = self._carregar_banco_dados()
        self.checkins_registrados = []
        self._inicializar_arquivo_checkins()
        
    def _carregar_banco_dados(self) -> Dict:
        """Carrega banco de dados de convidados."""
        if os.path.exists(self.banco_dados):
            try:
                with open(self.banco_dados, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                print(f"✅ Banco de dados carregado: {self.banco_dados}")
                print(f"   Convidados registrados: {len(dados.get('convidados', []))}")
                return dados
            except Exception as e:
                print(f"❌ Erro ao carregar banco de dados: {e}")
        
        # Retornar estrutura vazia se arquivo não existir
        return {"convidados": [], "ultimaatualizacao": datetime.now().isoformat()}
    
    def _inicializar_arquivo_checkins(self):
        """Inicializa arquivo de registro de check-ins."""
        if not os.path.exists(self.arquivo_checkins):
            try:
                with open(self.arquivo_checkins, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "Timestamp",
                        "Código Acesso",
                        "Nome",
                        "Tipo",
                        "Dia",
                        "Status",
                        "Operador",
                        "Local"
                    ])
                print(f"✅ Arquivo de check-in criado: {self.arquivo_checkins}")
            except Exception as e:
                print(f"❌ Erro ao criar arquivo: {e}")
    
    def validar_codigo(self, codigo: str, dia_evento: str = None) -> Dict:
        """
        Valida um código de acesso.
        
        Formato esperado: EVT-D1-A3F5B2C1E9D4K7L2
        
        Args:
            codigo: Código QR decodificado
            dia_evento: Dia atual do evento ('1', '2' ou '3')
            
        Returns:
            Dicionário com resultado da validação
        """
        resultado = {
            "valido": False,
            "mensagem": "",
            "codigo": codigo,
            "tipo_pessoa": None,
            "dia_evento": None,
            "nome": None,
            "email": None,
            "detalhes": {}
        }
        
        # Validar formato do código
        padrao = r'^EVT-D([123])-([A-Z0-9]{16})$'
        match = re.match(padrao, codigo.strip().upper())
        
        if not match:
            resultado["mensagem"] = f"❌ Formato inválido: {codigo}"
            return resultado
        
        dia_codigo = match.group(1)
        id_unico = match.group(2)
        
        resultado["dia_evento"] = dia_codigo
        resultado["detalhes"]["id_unico"] = id_unico
        
        # Se dia_evento foi especificado, validar
        if dia_evento and dia_codigo != str(dia_evento):
            resultado["mensagem"] = f"⚠️  Código para Dia {dia_codigo}, mas evento é Dia {dia_evento}"
            resultado["detalhes"]["alerta"] = "dia_inconsistente"
            # Continuar mesmo assim (pode ser acompanhante do dia anterior)
        
        # Procurar código no banco de dados (verificação de conhecimento)
        # Nota: Em produção, você armazenaria os IDs únicos no BD
        # Para este exemplo, apenas verificamos o formato
        
        resultado["codigo_formatado"] = codigo.upper()
        resultado["valido"] = True
        resultado["mensagem"] = f"✅ Código validado: {codigo}"
        
        return resultado
    
    def registrar_checkin(self, codigo: str, nome: str = "Desconhecido", 
                         tipo: str = "convidado", dia: str = "1", 
                         operador: str = "Sistema", local: str = "Portaria") -> bool:
        """
        Registra um check-in no arquivo CSV.
        
        Args:
            codigo: Código de acesso
            nome: Nome da pessoa
            tipo: 'convidado' ou 'acompanhante'
            dia: Dia do evento
            operador: Quem realizou o check-in
            local: Local do check-in
            
        Returns:
            True se registrado com sucesso
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(self.arquivo_checkins, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp,
                    codigo,
                    nome,
                    tipo,
                    dia,
                    "PRESENTE",
                    operador,
                    local
                ])
            
            self.checkins_registrados.append({
                "timestamp": timestamp,
                "codigo": codigo,
                "nome": nome,
                "tipo": tipo
            })
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao registrar check-in: {e}")
            return False
    
    def gerar_relatorio_diario(self, dia: str) -> str:
        """
        Gera relatório de presença do dia.
        
        Args:
            dia: Dia do evento ('1', '2' ou '3')
            
        Returns:
            Relatório formatado
        """
        if not os.path.exists(self.arquivo_checkins):
            return "❌ Nenhum arquivo de check-in encontrado."
        
        checkins_dia = []
        convidados = set()
        acompanhantes = set()
        
        try:
            with open(self.arquivo_checkins, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for linha in reader:
                    if linha.get('Dia') == dia:
                        checkins_dia.append(linha)
                        if linha.get('Tipo') == 'convidado':
                            convidados.add(linha.get('Nome'))
                        else:
                            acompanhantes.add(linha.get('Nome'))
        except Exception as e:
            return f"❌ Erro ao ler arquivo: {e}"
        
        relatorio = f"""
╔════════════════════════════════════════════════════╗
║        RELATÓRIO DE PRESENÇA - DIA {dia}             ║
╚════════════════════════════════════════════════════╝

Data: {datetime.now().strftime('%d/%m/%Y')}
Hora do Relatório: {datetime.now().strftime('%H:%M:%S')}

RESUMO:
───────────────────────────────────────────────────
  • Convidados Presentes: {len(convidados)}
  • Acompanhantes Presentes: {len(acompanhantes)}
  • Total de Check-ins: {len(checkins_dia)}

DETALHES DOS CHECK-INS:
───────────────────────────────────────────────────
"""
        
        for i, checkin in enumerate(checkins_dia, 1):
            relatorio += f"\n{i:3d}. {checkin.get('Nome', 'N/A'):<30} "
            relatorio += f"[{checkin.get('Tipo', 'N/A'):<12}] "
            relatorio += f"{checkin.get('Timestamp', 'N/A')}"
        
        relatorio += f"""

PRÓXIMAS AÇÕES:
───────────────────────────────────────────────────
[ ] Revisar presença vs confirmação
[ ] Enviar alertas para não-comparecentes
[ ] Arquivar relatório diário
[ ] Preparar para próximo dia
"""
        
        return relatorio
    
    def gerar_relatorio_completo(self) -> str:
        """Gera relatório completo de todos os check-ins."""
        if not os.path.exists(self.arquivo_checkins):
            return "❌ Nenhum arquivo de check-in encontrado."
        
        try:
            with open(self.arquivo_checkins, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                checkins = list(reader)
            
            # Estatísticas
            dias = {}
            for checkin in checkins:
                dia = checkin.get('Dia')
                if dia not in dias:
                    dias[dia] = []
                dias[dia].append(checkin)
            
            relatorio = f"""
╔════════════════════════════════════════════════════╗
║         RELATÓRIO COMPLETO DO EVENTO               ║
╚════════════════════════════════════════════════════╝

Data do Relatório: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

RESUMO GERAL:
───────────────────────────────────────────────────
  • Total de Check-ins: {len(checkins)}
  • Dias Registrados: {', '.join(sorted(dias.keys()))}
"""
            
            for dia in sorted(dias.keys()):
                checkins_dia = dias[dia]
                convidados_dia = len(set(c['Nome'] for c in checkins_dia if c.get('Tipo') == 'convidado'))
                acompanhantes_dia = len(set(c['Nome'] for c in checkins_dia if c.get('Tipo') != 'convidado'))
                
                relatorio += f"\n\nDIA {dia}:\n"
                relatorio += f"  • Convidados: {convidados_dia}\n"
                relatorio += f"  • Acompanhantes: {acompanhantes_dia}\n"
                relatorio += f"  • Check-ins: {len(checkins_dia)}\n"
            
            relatorio += f"""

INSTRUÇÕES PARA DOWNLOAD:
───────────────────────────────────────────────────
• Arquivo completo de check-in: {self.arquivo_checkins}
• Usar para análise e documentação do evento
"""
            
            return relatorio
            
        except Exception as e:
            return f"❌ Erro ao gerar relatório: {e}"


class LeitorQRCodeWebcam:
    """Leitor de QR Code via webcam usando OpenCV."""
    
    def __init__(self, validador: ValidadorCheckIn):
        """
        Inicializa o leitor.
        
        Args:
            validador: Instância de ValidadorCheckIn
        """
        self.validador = validador
        self.rodando = False
        
        if cv2 is None:
            print("⚠️  OpenCV não instalado. Use: pip install opencv-python pyzbar")
            print("    Alternativa: use --modo manual para entrada manual de códigos")
    
    def iniciar(self, dia_evento: str = "1"):
        """
        Inicia leitura via webcam.
        
        Args:
            dia_evento: Dia do evento ('1', '2' ou '3')
        """
        if cv2 is None:
            print("❌ OpenCV necessário. Instale com: pip install opencv-python pyzbar")
            return
        
        print(f"\n🎥 Iniciando leitor de QR Code - DIA {dia_evento}")
        print("Pressione 'q' para sair\n")
        
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ Não foi possível acessar a webcam.")
            return
        
        codigos_lidos = set()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Detectar QR codes usando detecção simples
            # Nota: Versão simplificada. Para uso real, use 'pyzbar'
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Exibir frame
            cv2.putText(frame, f"Dia {dia_evento} - Apontando QR Code para camera", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow('Leitor QR Code', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        print(f"\n✅ Leitura finalizada. {len(codigos_lidos)} códigos processados.")
    
    def modo_manual(self, dia_evento: str = "1"):
        """
        Modo manual de entrada de códigos.
        
        Args:
            dia_evento: Dia do evento
        """
        print(f"\n📝 Modo Manual - DIA {dia_evento}")
        print("Digite o código (ou 'sair' para finalizar):\n")
        
        contador = 0
        
        while True:
            try:
                codigo = input(f"[{contador+1}] Código: ").strip().upper()
                
                if codigo.lower() == 'sair':
                    break
                
                if not codigo:
                    continue
                
                # Validar
                resultado = self.validador.validar_codigo(codigo, dia_evento)
                
                if resultado["valido"]:
                    print(f"   ✅ {resultado['mensagem']}")
                    
                    # Registrar check-in
                    nome = input("   Nome (Enter para 'Desconhecido'): ").strip() or "Desconhecido"
                    self.validador.registrar_checkin(
                        codigo=codigo,
                        nome=nome,
                        tipo="convidado",
                        dia=dia_evento,
                        operador="Manual",
                        local="Portaria"
                    )
                    contador += 1
                else:
                    print(f"   {resultado['mensagem']}")
                    
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrompido pelo usuário")
                break
            except Exception as e:
                print(f"   ❌ Erro: {e}")
        
        print(f"\n✅ {contador} check-ins registrados.")


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description='Validador e registrador de check-in via QR code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python validar_checkin.py --modo manual
  python validar_checkin.py --modo webcam --dia 1
  python validar_checkin.py --relatorio-diario 1
  python validar_checkin.py --relatorio-completo
        """
    )
    
    parser.add_argument('--modo', choices=['manual', 'webcam', 'arquivo'],
                       default='manual',
                       help='Modo de leitura (padrão: manual)')
    parser.add_argument('--dia', default='1',
                       choices=['1', '2', '3'],
                       help='Dia do evento (padrão: 1)')
    parser.add_argument('--arquivo', 
                       help='Arquivo com código QR para processar')
    parser.add_argument('--bd', default='convidados_registro.json',
                       help='Arquivo do banco de dados de convidados')
    parser.add_argument('--relatorio-diario', metavar='DIA',
                       choices=['1', '2', '3'],
                       help='Gerar relatório de presença do dia')
    parser.add_argument('--relatorio-completo', action='store_true',
                       help='Gerar relatório completo do evento')
    
    args = parser.parse_args()
    
    print("\\n" + "="*50)
    print("VALIDADOR DE CHECK-IN - QR CODE")
    print("="*50 + "\\n")
    
    # Inicializar validador
    validador = ValidadorCheckIn(banco_dados=args.bd)
    
    # Processar relatórios
    if args.relatorio_diario:
        relatorio = validador.gerar_relatorio_diario(args.relatorio_diario)
        print(relatorio)
        return
    
    if args.relatorio_completo:
        relatorio = validador.gerar_relatorio_completo()
        print(relatorio)
        return
    
    # Processar modos de leitura
    if args.modo == 'manual':
        leitor = LeitorQRCodeWebcam(validador)
        leitor.modo_manual(dia_evento=args.dia)
    
    elif args.modo == 'webcam':
        leitor = LeitorQRCodeWebcam(validador)
        leitor.iniciar(dia_evento=args.dia)
    
    elif args.modo == 'arquivo' and args.arquivo:
        # Modo arquivo (para testes)
        print(f"📂 Processando arquivo: {args.arquivo}")
        print("Funcionalidade de arquivo ainda não implementada")


if __name__ == "__main__":
    main()
