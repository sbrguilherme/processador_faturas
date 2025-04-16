# Script final com deduplicação por telefone+serviço+valor
import os
import sys
import pandas as pd
import glob
import datetime
import logging
import re
import pdfplumber
from collections import defaultdict

logging.getLogger("pdfminer").setLevel(logging.ERROR)

def parse_num(s: str) -> float:
    s_clean = re.sub(r"[^0-9\.,]", "", s)
    if s_clean.count(',') > 0 and s_clean.count('.') > 0:
        if s_clean.rfind(',') > s_clean.rfind('.'):
            s_num = s_clean.replace('.', '').replace(',', '.')
        else:
            s_num = s_clean.replace(',', '')
    elif s_clean.count(',') > 0:
        s_num = s_clean.replace('.', '').replace(',', '.')
    else:
        s_num = s_clean.replace(',', '')
    try:
        return float(s_num)
    except ValueError:
        return 0.0

def normalizar_nome_coluna(nome):
    nome_limpo = re.sub(r"\s*-\s*de\s*\d{2}/\d{2}/\d{4}(\s*a\s*\d{2}/\d{2}/\d{4})?", "", nome)
    return nome_limpo.strip()

class ProcessadorMultiplasFaturas:
    def __init__(self):
        self.dados_por_arquivo = {}
        self.df_consolidado = None

    def extrair_totais_por_telefone(self, arquivo_pdf: str) -> pd.DataFrame:
        full_lines = []
        with pdfplumber.open(arquivo_pdf) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                full_lines.extend(line.strip() for line in text.splitlines())

        registros = defaultdict(lambda: defaultdict(float))
        ja_processado = set()

        bloco_idx = []
        for idx, line in enumerate(full_lines):
            if re.search(r'DETALHAMENTO DE LIGA.*CELULAR.*\(\d{2}\)\s*\d{4,5}[-\s]?\d{4}', line):
                bloco_idx.append(idx)

        for i, start in enumerate(bloco_idx):
            end = bloco_idx[i+1] if i+1 < len(bloco_idx) else len(full_lines)
            bloco = full_lines[start:end]
            m_tel = re.search(r'\(\d{2}\)\s*\d{4,5}[-\s]?\d{4}', bloco[0])
            tel = m_tel.group(0)

            total_r = 0.0
            valor_cobrado = 0.0
            in_servicos = False
            for j, line in enumerate(bloco):
                if re.search(r'Mensalidades e Pacotes Promocionais', line, re.IGNORECASE):
                    in_servicos = True
                elif in_servicos and re.match(r'TOTAL\s+R\$', line):
                    total_r = parse_num(line)
                    in_servicos = False
                elif in_servicos:
                    match = re.match(r'(.+?)\s+(\d+[\.,]\d{2})$', line)
                    if match:
                        nome = normalizar_nome_coluna(match.group(1).strip())
                        valor = parse_num(match.group(2))
                        chave = (tel, nome, valor)
                        if chave not in ja_processado:
                            registros[tel][nome] += valor
                            ja_processado.add(chave)
            for j, line in enumerate(bloco):
                if 'Valor Cobrado' in line:
                    for k in range(j+1, len(bloco)):
                        if bloco[k].lower().startswith('total'):
                            partes = bloco[k].split()
                            valor_cobrado = parse_num(partes[-1])
                            break
                    break
            registros[tel]['Total (R$)'] += total_r
            registros[tel]['Valor Cobrado (R$)'] += valor_cobrado

        idx = 0
        while idx < len(full_lines):
            if re.search(r'Cobran[çc]as e Descontos', full_lines[idx], re.IGNORECASE):
                while idx < len(full_lines) and not re.search(r'\(\d{2}\)\s*\d{4,5}[-\s]?\d{4}', full_lines[idx]):
                    idx += 1
                if idx >= len(full_lines):
                    break
                telefones = re.findall(r'\(\d{2}\)\s*\d{4,5}[-\s]?\d{4}', full_lines[idx])
                idx += 1
                while idx < len(full_lines):
                    linha = full_lines[idx]
                    if 'TOTAL PARA CADA CELULAR' in linha.upper():
                        break
                    if not re.search(r'R\$\s*[\d\.,]+', linha):
                        idx += 1
                        continue
                    servico = re.sub(r'R\$.*', '', linha).strip()
                    servico = normalizar_nome_coluna(servico)
                    valores = re.findall(r'R\$\s*[\d\.,]+', linha)
                    if len(valores) == len(telefones):
                        for i, tel in enumerate(telefones):
                            valor = parse_num(valores[i])
                            chave = (tel, servico, valor)
                            if chave not in ja_processado:
                                registros[tel][servico] += valor
                                ja_processado.add(chave)
                    idx += 1
            else:
                idx += 1

        return pd.DataFrame.from_dict(registros, orient='index')

    def extrair_total_a_pagar(self, arquivo_pdf: str) -> float:
        with pdfplumber.open(arquivo_pdf) as pdf:
            text = pdf.pages[0].extract_text() or ""
            m = re.search(r'Total a pagar\s*R\$\s*([\d\.,]+)', text, re.IGNORECASE)
            if m:
                return parse_num(m.group(1))
        return None

    def processar_diretorio(self, diretorio: str, padrao: str = "*.pdf") -> pd.DataFrame:
        self.dados_por_arquivo.clear()
        diretorio = os.path.normpath(diretorio)
        arquivos_pdf = []
        for ext in ["*.pdf", "*.PDF"]:
            arquivos_pdf.extend(glob.glob(os.path.join(diretorio, ext)))
        arquivos_pdf = sorted(set(arquivos_pdf))
        for arquivo in arquivos_pdf:
            nome_base = os.path.splitext(os.path.basename(arquivo))[0]
            print(f"Processando {arquivo}...")
            try:
                df = self.extrair_totais_por_telefone(arquivo).fillna(0)
                colunas_totais = ["Total (R$)", "Valor Cobrado (R$)"]
                colunas_servicos = [c for c in df.columns if c not in colunas_totais]
                df = df[colunas_servicos + colunas_totais]
                self.dados_por_arquivo[nome_base] = df
            except Exception as e:
                print(f"Erro ao processar {arquivo}: {e}")
        if self.dados_por_arquivo:
            self.df_consolidado = pd.concat(self.dados_por_arquivo.values())
        return self.df_consolidado

    def salvar_em_excel_multiplas_planilhas(self, caminho_saida: str) -> bool:
        if not self.dados_por_arquivo:
            print("Nenhum dado para salvar")
            return False
        try:
            with pd.ExcelWriter(caminho_saida, engine='xlsxwriter') as writer:
                for nome_aba, df in self.dados_por_arquivo.items():
                    df.to_excel(writer, sheet_name=nome_aba[:31], index_label="Telefone")
            print(f"Arquivo Excel salvo em {caminho_saida}")
            return True
        except Exception as e:
            print(f"Erro ao salvar Excel: {e}")
            return False

def verificar_dependencias():
    try:
        import pdfplumber
        import pandas
        import xlsxwriter
        return True
    except ImportError as e:
        print(f"ERRO: Biblioteca não encontrada - {e}")
        print("Para instalar: pip install pdfplumber pandas xlsxwriter")
        return False

def gerar_nome_excel():
    agora = datetime.datetime.now()
    return f"faturas_claro_{agora.strftime('%Y%m%d_%H%M%S')}.xlsx"

def main():
    if not verificar_dependencias():
        sys.exit(1)
    print("\n=== Processador de Faturas Claro com múltiplas planilhas Excel ===\n")
    diretorio = input("Informe o diretório com os PDFs:\n> ").strip().strip('"\'')
    saida_excel = os.path.join(os.getcwd(), gerar_nome_excel())
    proc = ProcessadorMultiplasFaturas()
    df_total = proc.processar_diretorio(diretorio)
    if df_total is not None:
        proc.salvar_em_excel_multiplas_planilhas(saida_excel)
        print("Processamento finalizado com sucesso.")
    else:
        print("Nenhum dado extraído.")

if __name__ == '__main__':
    main()
