#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Dashboard e Relatórios para Evento
==============================================
Gera relatórios e dashboards a partir dos dados coletados.

Requisitos:
    pip install pandas matplotlib seaborn reportlab

Uso:
    python dashboard_relatorios.py --arquivo convidados.csv --gerar-todos
    python dashboard_relatorios.py --arquivo convidados.csv --graficos
    python dashboard_relatorios.py --checkins checkins.csv --relatorio-diario 1
"""

import os
import sys
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
import argparse

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    from matplotlib.backends.backend_pdf import PdfPages
except ImportError:
    print("❌ Erro: Bibliotecas necessárias não instaladas.")
    print("Execute: pip install pandas matplotlib seaborn")
    sys.exit(1)


class GeradorDashboard:
    """Gerador de dashboards e relatórios para eventos."""
    
    def __init__(self, arquivo_convidados: str = None, 
                 arquivo_checkins: str = None,
                 pasta_saida: str = "./relatorios"):
        """
        Inicializa o gerador.
        
        Args:
            arquivo_convidados: Arquivo CSV com dados de convidados
            arquivo_checkins: Arquivo CSV com registro de check-ins
            pasta_saida: Pasta para salvar relatórios
        """
        self.pasta_saida = Path(pasta_saida)
        self.pasta_saida.mkdir(parents=True, exist_ok=True)
        
        self.df_convidados = None
        self.df_checkins = None
        
        if arquivo_convidados and os.path.exists(arquivo_convidados):
            self._carregar_convidados(arquivo_convidados)
        
        if arquivo_checkins and os.path.exists(arquivo_checkins):
            self._carregar_checkins(arquivo_checkins)
        
        # Configurar estilo dos gráficos
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 10
    
    def _carregar_convidados(self, arquivo: str):
        """Carrega dados de convidados."""
        try:
            self.df_convidados = pd.read_csv(arquivo)
            print(f"✅ Convidados carregados: {len(self.df_convidados)} registros")
        except Exception as e:
            print(f"❌ Erro ao carregar convidados: {e}")
    
    def _carregar_checkins(self, arquivo: str):
        """Carrega dados de check-ins."""
        try:
            self.df_checkins = pd.read_csv(arquivo)
            self.df_checkins['Timestamp'] = pd.to_datetime(self.df_checkins['Timestamp'])
            print(f"✅ Check-ins carregados: {len(self.df_checkins)} registros")
        except Exception as e:
            print(f"❌ Erro ao carregar check-ins: {e}")
    
    def gerar_relatorio_confirmacoes(self) -> str:
        """Gera relatório de confirmações."""
        if self.df_convidados is None:
            return "❌ Nenhum dado de convidados disponível"
        
        df = self.df_convidados
        
        # Estatísticas básicas
        total = len(df)
        
        # Contar dias (assumindo coluna 'dias' com formato "1 2 3")
        total_dia_1 = df['dias'].astype(str).str.contains('1').sum()
        total_dia_2 = df['dias'].astype(str).str.contains('2').sum()
        total_dia_3 = df['dias'].astype(str).str.contains('3').sum()
        
        # Acompanhantes
        total_acompanhantes = df['num_acompanhantes'].astype(int).sum()
        
        # Restrições alimentares
        restricoes = {}
        for _, row in df.iterrows():
            restr = str(row.get('restricoes_alimentares', 'Nenhuma'))
            restricoes[restr] = restricoes.get(restr, 0) + 1
        
        relatorio = f"""
╔════════════════════════════════════════════════════╗
║        RELATÓRIO DE CONFIRMAÇÕES - EVENTO           ║
╚════════════════════════════════════════════════════╝

Data do Relatório: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

RESUMO GERAL:
───────────────────────────────────────────────────
  • Total de Convidados: {total}
  • Total de Acompanhantes: {total_acompanhantes}
  • Total de Pessoas: {total + total_acompanhantes}

CONFIRMAÇÃO POR DIA:
───────────────────────────────────────────────────
  • Dia 10 de Abril: {total_dia_1} confirmações
  • Dia 11 de Abril: {total_dia_2} confirmações
  • Dia 12 de Abril: {total_dia_3} confirmações
  • Média por dia: {(total_dia_1 + total_dia_2 + total_dia_3) / 3:.0f}

DADOS DE ACOMPANHANTES:
───────────────────────────────────────────────────
"""
        
        # Contar distribuição de acompanhantes
        dist_acomp = df['num_acompanhantes'].astype(int).value_counts().sort_index()
        relatorio += f"  • Nenhum: {dist_acomp.get(0, 0)}\n"
        relatorio += f"  • 1 acompanhante: {dist_acomp.get(1, 0)}\n"
        relatorio += f"  • 2 acompanhantes: {dist_acomp.get(2, 0)}\n"
        
        relatorio += f"\nRESTRIÇÕES ALIMENTARES:\n───────────────────────────────────────────────────\n"
        
        for restr, count in sorted(restricoes.items(), key=lambda x: x[1], reverse=True):
            relatorio += f"  • {restr}: {count}\n"
        
        relatorio += f"""

PRÓXIMAS AÇÕES:
───────────────────────────────────────────────────
[ ] Enviar confirmação para todos os convidados
[ ] Gerar QR codes
[ ] Preparar lista de restrições alimentares para catering
[ ] Confirmar espaço e recursos para número total
[ ] Enviar lembretes 7 dias antes
"""
        
        return relatorio
    
    def gerar_relatorio_checkins_diario(self, dia: str) -> str:
        """Gera relatório de check-ins de um dia específico."""
        if self.df_checkins is None:
            return "❌ Nenhum dado de check-in disponível"
        
        df = self.df_checkins[self.df_checkins['Dia'] == dia].copy()
        
        if len(df) == 0:
            return f"⚠️ Nenhum check-in registrado para o Dia {dia}"
        
        total_checkins = len(df)
        convidados = len(df[df['Tipo'] == 'convidado'])
        acompanhantes = total_checkins - convidados
        
        # Horários
        df['Hora'] = pd.to_datetime(df['Timestamp']).dt.strftime('%H:%M')
        primeira_hora = df['Timestamp'].min()
        ultima_hora = df['Timestamp'].max()
        
        relatorio = f"""
╔════════════════════════════════════════════════════╗
║       RELATÓRIO DE PRESENÇA - DIA {dia}              ║
╚════════════════════════════════════════════════════╝

Data: {datetime.now().strftime('%d/%m/%Y')}

RESUMO DO DIA:
───────────────────────────────────────────────────
  • Check-ins Totais: {total_checkins}
  • Convidados Presentes: {convidados}
  • Acompanhantes Presentes: {acompanhantes}
  • Primeira Entrada: {primeira_hora.strftime('%H:%M')}
  • Última Entrada: {ultima_hora.strftime('%H:%M')}

CRONOGRAMA DE ENTRADA:
───────────────────────────────────────────────────
"""
        
        # Contar por hora
        df['HoraInt'] = pd.to_datetime(df['Timestamp']).dt.hour
        entrada_por_hora = df.groupby('HoraInt').size()
        
        for hora, count in entrada_por_hora.items():
            relatorio += f"  • {hora:02d}:00-{hora:02d}:59 → {count} pessoas\n"
        
        relatorio += f"""

LOCAIS DE ENTRADA:
───────────────────────────────────────────────────
"""
        
        locais = df['Local'].value_counts()
        for local, count in locais.items():
            relatorio += f"  • {local}: {count}\n"
        
        relatorio += f"""

STATUS DA VALIDAÇÃO:
───────────────────────────────────────────────────
"""
        
        status = df['Status'].value_counts()
        for s, count in status.items():
            relatorio += f"  • {s}: {count}\n"
        
        relatorio += f"""

DETALHES:
───────────────────────────────────────────────────
"""
        
        for idx, (_, row) in enumerate(df.iterrows(), 1):
            relatorio += f"{idx:3d}. {row['Timestamp'].strftime('%H:%M')} | "
            relatorio += f"{row['Nome']:<25} | "
            relatorio += f"{row['Tipo']:<12} | "
            relatorio += f"{row['Local']}\n"
        
        relatorio += f"""

ANÁLISE:
───────────────────────────────────────────────────
  • Taxa de Presença: {(convidados / max(convidados, 1) * 100):.1f}%
  • Pico de Entrada: {entrada_por_hora.idxmax():02d}:00 com {entrada_por_hora.max()} pessoas
  • Tempo Médio entre Entradas: {(ultima_hora - primeira_hora).total_seconds() / total_checkins:.0f}s
"""
        
        return relatorio
    
    def gerar_grafico_confirmacoes(self):
        """Gera gráfico de confirmações por dia."""
        if self.df_convidados is None:
            print("❌ Dados de convidados não disponíveis")
            return
        
        df = self.df_convidados
        
        # Contar por dia
        dias = ['1', '2', '3']
        confirmacoes = []
        
        for dia in dias:
            count = df['dias'].astype(str).str.contains(dia).sum()
            confirmacoes.append(count)
        
        # Criar gráfico
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        
        cores = ['#667eea', '#764ba2', '#f093fb']
        barras = ax.bar(['Dia 10\n(Abril)', 'Dia 11\n(Abril)', 'Dia 12\n(Abril)'], 
                        confirmacoes, color=cores, alpha=0.8, edgecolor='black', linewidth=1.5)
        
        # Adicionar valores nas barras
        for barra, valor in zip(barras, confirmacoes):
            altura = barra.get_height()
            ax.text(barra.get_x() + barra.get_width()/2., altura,
                   f'{int(valor)}',
                   ha='center', va='bottom', fontsize=12, fontweight='bold')
        
        ax.set_ylabel('Número de Confirmações', fontsize=12, fontweight='bold')
        ax.set_xlabel('Dias do Evento', fontsize=12, fontweight='bold')
        ax.set_title('Confirmações de Presença por Dia', fontsize=14, fontweight='bold', pad=20)
        ax.set_ylim(0, max(confirmacoes) * 1.2)
        ax.grid(axis='y', alpha=0.3)
        
        # Salvar
        arquivo = self.pasta_saida / 'grafico_confirmacoes_por_dia.png'
        plt.savefig(arquivo, dpi=300, bbox_inches='tight')
        print(f"✅ Gráfico salvo: {arquivo}")
        plt.close()
    
    def gerar_grafico_acompanhantes(self):
        """Gera gráfico de distribuição de acompanhantes."""
        if self.df_convidados is None:
            print("❌ Dados de convidados não disponíveis")
            return
        
        df = self.df_convidados
        dist = df['num_acompanhantes'].astype(int).value_counts().sort_index()
        
        # Criar gráfico
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        
        cores_pizza = ['#667eea', '#764ba2', '#f093fb']
        
        wedges, texts, autotexts = ax.pie(
            dist.values,
            labels=[f'Sem Acompanhante\n({dist.get(0, 0)})', 
                   f'1 Acompanhante\n({dist.get(1, 0)})',
                   f'2 Acompanhantes\n({dist.get(2, 0)})'],
            autopct='%1.1f%%',
            colors=cores_pizza,
            startangle=90,
            textprops={'fontsize': 11, 'fontweight': 'bold'}
        )
        
        # Estilizar
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(12)
            autotext.set_fontweight('bold')
        
        ax.set_title('Distribuição de Acompanhantes', fontsize=14, fontweight='bold', pad=20)
        
        # Salvar
        arquivo = self.pasta_saida / 'grafico_distribuicao_acompanhantes.png'
        plt.savefig(arquivo, dpi=300, bbox_inches='tight')
        print(f"✅ Gráfico salvo: {arquivo}")
        plt.close()
    
    def gerar_grafico_restricoes_alimentares(self):
        """Gera gráfico de restrições alimentares."""
        if self.df_convidados is None:
            print("❌ Dados de convidados não disponíveis")
            return
        
        df = self.df_convidados
        
        # Contar restrições
        restricoes = {}
        for _, row in df.iterrows():
            restr = str(row.get('restricoes_alimentares', 'Nenhuma'))
            restricoes[restr] = restricoes.get(restr, 0) + 1
        
        # Ordenar por quantidade
        restricoes = dict(sorted(restricoes.items(), key=lambda x: x[1], reverse=True))
        
        # Criar gráfico
        fig, ax = plt.subplots(1, 1, figsize=(12, 6))
        
        cores = plt.cm.Set3(range(len(restricoes)))
        barras = ax.barh(list(restricoes.keys()), list(restricoes.values()), 
                         color=cores, edgecolor='black', linewidth=1.5)
        
        # Adicionar valores nas barras
        for barra, valor in zip(barras, restricoes.values()):
            largura = barra.get_width()
            ax.text(largura, barra.get_y() + barra.get_height()/2.,
                   f' {int(valor)}',
                   ha='left', va='center', fontsize=10, fontweight='bold')
        
        ax.set_xlabel('Número de Pessoas', fontsize=12, fontweight='bold')
        ax.set_title('Restrições Alimentares dos Convidados', fontsize=14, fontweight='bold', pad=20)
        ax.grid(axis='x', alpha=0.3)
        
        # Salvar
        arquivo = self.pasta_saida / 'grafico_restricoes_alimentares.png'
        plt.savefig(arquivo, dpi=300, bbox_inches='tight')
        print(f"✅ Gráfico salvo: {arquivo}")
        plt.close()
    
    def gerar_grafico_checkins_por_hora(self, dia: str = '1'):
        """Gera gráfico de check-ins por hora do dia."""
        if self.df_checkins is None:
            print("❌ Dados de check-in não disponíveis")
            return
        
        df = self.df_checkins[self.df_checkins['Dia'] == dia].copy()
        
        if len(df) == 0:
            print(f"⚠️ Nenhum check-in para o Dia {dia}")
            return
        
        # Agrupar por hora
        df['Hora'] = pd.to_datetime(df['Timestamp']).dt.hour
        checkins_por_hora = df.groupby('Hora').size()
        
        # Completar horas vazias
        todas_horas = pd.Series(0, index=range(0, 24))
        checkins_por_hora = todas_horas.add(checkins_por_hora, fill_value=0)
        
        # Criar gráfico
        fig, ax = plt.subplots(1, 1, figsize=(14, 6))
        
        cores = plt.cm.viridis(checkins_por_hora / checkins_por_hora.max())
        barras = ax.bar(range(24), checkins_por_hora.values, color=cores, 
                       edgecolor='black', linewidth=1)
        
        ax.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
        ax.set_ylabel('Número de Check-ins', fontsize=12, fontweight='bold')
        ax.set_title(f'Check-ins por Hora - Dia {dia}', fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(range(0, 24, 2))
        ax.set_xticklabels([f'{h:02d}:00' for h in range(0, 24, 2)], rotation=45)
        ax.grid(axis='y', alpha=0.3)
        
        # Salvar
        arquivo = self.pasta_saida / f'grafico_checkins_por_hora_dia{dia}.png'
        plt.savefig(arquivo, dpi=300, bbox_inches='tight')
        print(f"✅ Gráfico salvo: {arquivo}")
        plt.close()
    
    def gerar_pdf_relatorio_completo(self):
        """Gera PDF com relatório completo."""
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle
        from reportlab.lib.units import inch
        
        arquivo_pdf = self.pasta_saida / 'Relatorio_Completo_Evento.pdf'
        
        # Criar documento
        doc = SimpleDocTemplate(str(arquivo_pdf), pagesize=letter,
                              rightMargin=0.75*inch, leftMargin=0.75*inch,
                              topMargin=1*inch, bottomMargin=1*inch)
        
        # Preparar conteúdo
        story = []
        styles = getSampleStyleSheet()
        
        # Título
        titulo = Paragraph("<b>RELATÓRIO COMPLETO DO EVENTO 2026</b>", 
                          styles['Heading1'])
        story.append(titulo)
        story.append(Spacer(1, 0.3*inch))
        
        # Resumo
        if self.df_convidados is not None:
            resumo_text = f"""
            <b>Total de Confirmações:</b> {len(self.df_convidados)}<br/>
            <b>Data do Relatório:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/>
            <b>Acompanhantes Confirmados:</b> {self.df_convidados['num_acompanhantes'].astype(int).sum()}
            """
            resumo = Paragraph(resumo_text, styles['Normal'])
            story.append(resumo)
            story.append(Spacer(1, 0.3*inch))
        
        # Gráficos
        graficos = [
            'grafico_confirmacoes_por_dia.png',
            'grafico_distribuicao_acompanhantes.png',
            'grafico_restricoes_alimentares.png'
        ]
        
        for grafico in graficos:
            caminho = self.pasta_saida / grafico
            if caminho.exists():
                img = Image(str(caminho), width=6*inch, height=4*inch)
                story.append(img)
                story.append(Spacer(1, 0.2*inch))
        
        # Salvar PDF
        doc.build(story)
        print(f"✅ PDF gerado: {arquivo_pdf}")
    
    def gerar_todos_relatorios(self):
        """Gera todos os relatórios e gráficos."""
        print("\\n📊 Gerando todos os relatórios e gráficos...\\n")
        
        # Relatórios em texto
        if self.df_convidados is not None:
            relatorio = self.gerar_relatorio_confirmacoes()
            print(relatorio)
            
            # Salvar em arquivo
            arquivo = self.pasta_saida / 'relatorio_confirmacoes.txt'
            with open(arquivo, 'w', encoding='utf-8') as f:
                f.write(relatorio)
            print(f"✅ Relatório salvo: {arquivo}\\n")
        
        # Gráficos
        print("📈 Gerando gráficos...\\n")
        self.gerar_grafico_confirmacoes()
        self.gerar_grafico_acompanhantes()
        self.gerar_grafico_restricoes_alimentares()
        
        if self.df_checkins is not None:
            for dia in ['1', '2', '3']:
                self.gerar_grafico_checkins_por_hora(dia)
        
        # PDF
        print("\\n📄 Gerando PDF...\\n")
        self.gerar_pdf_relatorio_completo()
        
        print(f"\\n✅ Todos os relatórios gerados em: {self.pasta_saida}\\n")


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description='Gerador de relatórios e dashboards para evento',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python dashboard_relatorios.py --arquivo convidados.csv --gerar-todos
  python dashboard_relatorios.py --arquivo convidados.csv --graficos
  python dashboard_relatorios.py --checkins checkins.csv --relatorio-diario 1
        """
    )
    
    parser.add_argument('--arquivo', 
                       help='Arquivo CSV com dados de convidados')
    parser.add_argument('--checkins',
                       help='Arquivo CSV com dados de check-in')
    parser.add_argument('--saida', default='./relatorios',
                       help='Pasta de saída dos relatórios')
    parser.add_argument('--gerar-todos', action='store_true',
                       help='Gerar todos os relatórios')
    parser.add_argument('--graficos', action='store_true',
                       help='Gerar apenas gráficos')
    parser.add_argument('--relatorio-diario', metavar='DIA',
                       choices=['1', '2', '3'],
                       help='Gerar relatório diário de check-in')
    
    args = parser.parse_args()
    
    print("\\n" + "="*50)
    print("GERADOR DE RELATÓRIOS - EVENTO")
    print("="*50 + "\\n")
    
    gerador = GeradorDashboard(
        arquivo_convidados=args.arquivo,
        arquivo_checkins=args.checkins,
        pasta_saida=args.saida
    )
    
    if args.gerar_todos:
        gerador.gerar_todos_relatorios()
    elif args.graficos:
        print("📈 Gerando gráficos...\\n")
        gerador.gerar_grafico_confirmacoes()
        gerador.gerar_grafico_acompanhantes()
        gerador.gerar_grafico_restricoes_alimentares()
    elif args.relatorio_diario:
        relatorio = gerador.gerar_relatorio_checkins_diario(args.relatorio_diario)
        print(relatorio)


if __name__ == "__main__":
    main()
