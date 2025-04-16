#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extrator de dados de faturas da Claro
Este script extrai informações de faturas da Claro em formato PDF,
identificando números de telefone, serviços e valores correspondentes.
Versão com compatibilidade aprimorada para Windows.
"""

import os
import re
import pandas as pd
import subprocess
import platform
import tempfile
from collections import defaultdict

class ExtratorFaturaClaro:
    def __init__(self):
        """Inicializa o extrator de faturas da Claro."""
        self.telefones = []
        self.servicos = set()
        self.dados = defaultdict(dict)
    
    def extrair_texto_pdf(self, caminho_pdf, caminho_saida=None):
        """
        Extrai o texto do arquivo PDF usando pdftotext.
        
        Args:
            caminho_pdf: Caminho para o arquivo PDF
            caminho_saida: Caminho para salvar o texto extraído (opcional)
            
        Returns:
            Caminho do arquivo de texto extraído
        """
        # Normalizar o caminho do PDF
        caminho_pdf = os.path.normpath(caminho_pdf)
        
        # Verificar se o arquivo existe
        if not os.path.isfile(caminho_pdf):
            raise FileNotFoundError(f"O arquivo PDF '{caminho_pdf}' não foi encontrado")
        
        # Verificar se o arquivo tem tamanho maior que zero
        if os.path.getsize(caminho_pdf) == 0:
            raise ValueError(f"O arquivo PDF '{caminho_pdf}' está vazio")
        
        if caminho_saida is None:
            # Criar um arquivo temporário para o texto extraído
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp:
                caminho_saida = temp.name
        
        # Normalizar o caminho de saída
        caminho_saida = os.path.normpath(caminho_saida)
        
        try:
            # Usar pdftotext com a opção -layout para preservar o layout do texto
            # Escapar os caminhos com aspas para lidar com espaços e caracteres especiais
            if platform.system() == 'Windows':
                # No Windows, usamos aspas duplas para os caminhos
                comando = f'pdftotext -layout "{caminho_pdf}" "{caminho_saida}"'
                subprocess.run(comando, shell=True, check=True)
            else:
                # Em sistemas Unix, podemos usar o método padrão
                subprocess.run(["pdftotext", "-layout", caminho_pdf, caminho_saida], check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Falha ao executar pdftotext: {str(e)}")
        
        return caminho_saida
    
    def processar_fatura(self, caminho_pdf):
        """
        Processa uma fatura da Claro em formato PDF.
        
        Args:
            caminho_pdf: Caminho para o arquivo PDF da fatura
            
        Returns:
            DataFrame com os dados extraídos
        """
        # Extrair texto do PDF
        arquivo_texto = self.extrair_texto_pdf(caminho_pdf)
        
        try:
            # Ler o conteúdo do arquivo de texto
            with open(arquivo_texto, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            
            # Limpar dados anteriores
            self.telefones = []
            self.servicos = set()
            self.dados = defaultdict(dict)
            
            # Extrair informações
            self._extrair_telefones_e_servicos(conteudo)
            
            # Converter para DataFrame
            return self._criar_dataframe()
        except UnicodeDecodeError:
            # Tentar novamente com encoding latin-1 se utf-8 falhar
            try:
                with open(arquivo_texto, 'r', encoding='latin-1') as f:
                    conteudo = f.read()
                
                # Limpar dados anteriores
                self.telefones = []
                self.servicos = set()
                self.dados = defaultdict(dict)
                
                # Extrair informações
                self._extrair_telefones_e_servicos(conteudo)
                
                # Converter para DataFrame
                return self._criar_dataframe()
            except Exception as e:
                raise RuntimeError(f"Erro ao processar o texto extraído: {str(e)}")
        finally:
            # Remover o arquivo temporário se foi criado
            try:
                if os.path.exists(arquivo_texto) and arquivo_texto.startswith(tempfile.gettempdir()):
                    os.remove(arquivo_texto)
            except:
                pass
    
    def _extrair_telefones_e_servicos(self, conteudo):
        """
        Extrai números de telefone, serviços e valores do conteúdo da fatura.
        
        Args:
            conteudo: Texto extraído da fatura
        """
        # Padrão para encontrar seções de detalhamento de telefones
        padrao_telefone = r"DETALHAMENTO DE LIGAÇÕES E SERVIÇOS DO CELULAR \((\d+)\) (\d+) (\d+)"
        
        # Encontrar todas as ocorrências de números de telefone
        matches_telefone = re.finditer(padrao_telefone, conteudo)
        
        # Para cada telefone encontrado
        for match in matches_telefone:
            # Extrair o número de telefone completo
            ddd = match.group(1)
            parte1 = match.group(2)
            parte2 = match.group(3)
            telefone = f"({ddd}) {parte1}-{parte2}"
            
            # Adicionar à lista de telefones
            self.telefones.append(telefone)
            
            # Obter a posição do início da seção deste telefone
            pos_inicio = match.start()
            
            # Encontrar a próxima ocorrência de "DETALHAMENTO DE LIGAÇÕES" ou o final do texto
            proximo_match = re.search(r"DETALHAMENTO DE LIGAÇÕES", conteudo[pos_inicio + 1:])
            if proximo_match:
                pos_fim = pos_inicio + 1 + proximo_match.start()
            else:
                pos_fim = len(conteudo)
            
            # Extrair a seção deste telefone
            secao_telefone = conteudo[pos_inicio:pos_fim]
            
            # Encontrar a seção "Mensalidades e Pacotes Promocionais"
            match_mensalidades = re.search(r"Mensalidades e Pacotes Promocionais\s+Descrição\s+Total \(R\$\)", secao_telefone)
            if match_mensalidades:
                pos_mensalidades = match_mensalidades.end()
                
                # Encontrar o final da seção de mensalidades (até "TOTAL" ou "Serviços")
                match_fim_mensalidades = re.search(r"TOTAL\s+R\$\s+[\d,\.]+|Serviços \(Torpedos", secao_telefone[pos_mensalidades:])
                if match_fim_mensalidades:
                    pos_fim_mensalidades = pos_mensalidades + match_fim_mensalidades.start()
                    
                    # Extrair a seção de mensalidades
                    secao_mensalidades = secao_telefone[pos_mensalidades:pos_fim_mensalidades]
                    
                    # Extrair serviços e valores
                    linhas = secao_mensalidades.strip().split('\n')
                    for linha in linhas:
                        # Remover espaços extras
                        linha = re.sub(r'\s+', ' ', linha.strip())
                        
                        # Procurar por um padrão de descrição seguido por valor
                        match_servico = re.search(r'^(.+?)\s+([\d,\.]+)$', linha)
                        if match_servico:
                            servico = match_servico.group(1).strip()
                            valor = match_servico.group(2).replace(',', '.')
                            
                            # Filtrar serviços inválidos (como números de página)
                            if not re.match(r'^Pág\. A \d+\/$', servico):
                                # Adicionar à lista de serviços
                                self.servicos.add(servico)
                                
                                # Armazenar o valor para este telefone e serviço
                                self.dados[telefone][servico] = float(valor)
            
            # NOVA FUNCIONALIDADE: Extrair dados de Ligações Locais
            match_ligacoes_locais = re.search(r"Ligações Locais", secao_telefone)
            if match_ligacoes_locais:
                # Procurar por "Valor Cobrado (R$)" e extrair o valor correspondente
                # Padrão mais específico para capturar o valor cobrado de ligações locais
                match_valor_cobrado = re.search(r"Valor Cobrado \(R\$\)[\s\n]+([\d,\.]+)[\s\n]+TOTAL", secao_telefone[match_ligacoes_locais.end():])
                if match_valor_cobrado:
                    valor = match_valor_cobrado.group(1).replace(',', '.')
                    # Adicionar à lista de serviços
                    servico = "Ligações Locais - Valor Cobrado"
                    self.servicos.add(servico)
                    # Armazenar o valor para este telefone e serviço
                    self.dados[telefone][servico] = float(valor)
            
            # NOVA FUNCIONALIDADE: Extrair dados de Serviços (Torpedos, Hits, Jogos, etc.)
            match_servicos = re.search(r"Serviços \(Torpedos, Hits, Jogos, etc\.\)", secao_telefone)
            if match_servicos:
                # Procurar diretamente por "Valor Cobrado (R$)" após a seção de serviços
                # Usar um padrão mais específico para capturar o valor cobrado
                match_valor_cobrado_servicos = re.search(r"Valor Cobrado \(R\$\)[\s\n]+([\d,\.]+)", secao_telefone[match_servicos.end():])
                if match_valor_cobrado_servicos:
                    valor = match_valor_cobrado_servicos.group(1).replace(',', '.')
                    if float(valor) > 0:  # Verificar se o valor é maior que zero
                        # Adicionar à lista de serviços
                        servico = "Serviços (Torpedos, Hits, Jogos) - Valor Cobrado"
                        self.servicos.add(servico)
                        # Armazenar o valor para este telefone e serviço
                        self.dados[telefone][servico] = float(valor)
            
            # NOVA FUNCIONALIDADE: Extrair dados de Internet (MB)
            match_internet = re.search(r"Internet \(MB\)", secao_telefone)
            if match_internet:
                # Procurar por "Subtotal" e depois por "Valor Cobrado (R$)" para Internet
                match_subtotal = re.search(r"Subtotal[\s\n]+[\d,\.]+[\s\n]+", secao_telefone[match_internet.end():])
                if match_subtotal:
                    pos_subtotal = match_internet.end() + match_subtotal.end()
                    # Procurar pelo valor cobrado após o subtotal
                    match_valor_cobrado_internet = re.search(r"([\d,\.]+)[\s\n]*$", secao_telefone[pos_subtotal:pos_subtotal+100])
                    if match_valor_cobrado_internet:
                        valor = match_valor_cobrado_internet.group(1).replace(',', '.')
                        if float(valor) > 0:  # Verificar se o valor é maior que zero
                            # Adicionar à lista de serviços
                            servico = "Internet (MB) - Valor Cobrado"
                            self.servicos.add(servico)
                            # Armazenar o valor para este telefone e serviço
                            self.dados[telefone][servico] = float(valor)
    
    def _criar_dataframe(self):
        """
        Cria um DataFrame com os dados extraídos.
        
        Returns:
            DataFrame com telefones nas linhas, serviços nas colunas e valores nas células
        """
        # Verificar se temos dados para criar o DataFrame
        if not self.telefones or not self.servicos:
            raise ValueError("Nenhum dado extraído da fatura. Verifique se o formato da fatura é compatível.")
        
        # Criar DataFrame vazio
        df = pd.DataFrame(index=self.telefones, columns=sorted(list(self.servicos)))
        
        # Preencher com os dados extraídos
        for telefone, servicos in self.dados.items():
            for servico, valor in servicos.items():
                df.at[telefone, servico] = valor
        
        # Preencher valores NaN com 0
        df = df.fillna(0)
        
        # Adicionar coluna de total por telefone
        df['Total'] = df.sum(axis=1)
        
        return df

def processar_fatura(caminho_pdf, caminho_saida=None):
    """
    Processa uma fatura da Claro e retorna um DataFrame com os dados extraídos.
    
    Args:
        caminho_pdf: Caminho para o arquivo PDF da fatura
        caminho_saida: Caminho para salvar o resultado em CSV (opcional)
        
    Returns:
        DataFrame com os dados extraídos
    """
    extrator = ExtratorFaturaClaro()
    df = extrator.processar_fatura(caminho_pdf)
    
    # Salvar em CSV se caminho_saida for fornecido
    if caminho_saida:
        # Normalizar o caminho de saída
        caminho_saida = os.path.normpath(caminho_saida)
        
        # Criar o diretório de saída se não existir
        diretorio_saida = os.path.dirname(caminho_saida)
        if diretorio_saida and not os.path.exists(diretorio_saida):
            os.makedirs(diretorio_saida, exist_ok=True)
            
        df.to_csv(caminho_saida)
    
    return df

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python extrator_fatura.py <caminho_pdf> [caminho_saida.csv]")
        sys.exit(1)
    
    caminho_pdf = sys.argv[1]
    # Remover aspas se o usuário copiou o caminho com aspas (comum no Windows)
    caminho_pdf = caminho_pdf.strip('"\'')
    
    caminho_saida = sys.argv[2] if len(sys.argv) > 2 else None
    if caminho_saida:
        caminho_saida = caminho_saida.strip('"\'')
    
    try:
        df = processar_fatura(caminho_pdf, caminho_saida)
        print(df)
    except Exception as e:
        print(f"Erro ao processar a fatura: {str(e)}")
        sys.exit(1)
