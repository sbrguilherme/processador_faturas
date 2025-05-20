# Script Final Corrigido e Testado (Claro + Vivo + TIM + Globalstar)

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
    s_clean = s_clean.replace('.', '').replace(',', '.') if ',' in s_clean else s_clean.replace(',', '')
    try:
        return float(s_clean)
    except ValueError:
        return 0.0

def parse_valor(valor):
    try:
        return float(valor.replace("R$", "").replace(".", "").replace(",", ".").strip())
    except:
        return valor

def normalizar_nome_coluna(nome):
    return re.sub(r"\s*-\s*de\s*\d{2}/\d{2}/\d{4}(\s*a\s*\d{2}/\d{2}/\d{4})?", "", nome).strip()

class ProcessadorFaturas:
    def __init__(self):
        self.dados_por_arquivo = {}
        self.df_consolidado = None

    def processar_vivo(self, pdf):
        registros = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            if "DETALHAMENTO TOTAL DA CONTA" in text:
                linhas = text.splitlines()
                for linha in linhas:
                    blocos = re.findall(r'(\d{2}-\d{5}-\d{4})\s+(PLANO [^\d]+?)\s+(\d+[\.,]\d{2})', linha)
                    for numero, plano, valor in blocos:
                        registros.append({
                            "Número Vivo": numero.strip(),
                            "Plano": plano.strip(),
                            "Valor Total R$": parse_num(valor)
                        })
        return pd.DataFrame(registros)

    def processar_claro(self, pdf):
        registros = defaultdict(lambda: defaultdict(float))
        ja_processado = set()
        full_lines = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_lines.extend(line.strip() for line in text.splitlines())

        bloco_idx = [i for i, line in enumerate(full_lines) if re.search(r'DETALHAMENTO DE LIGA.*CELULAR.*\(\d{2}\)', line)]

        for i, start in enumerate(bloco_idx):
            end = bloco_idx[i+1] if i+1 < len(bloco_idx) else len(full_lines)
            bloco = full_lines[start:end]
            m_tel = re.search(r'\(\d{2}\)\s*\d{4,5}[-\s]?\d{4}', bloco[0])
            if not m_tel:
                continue
            tel = m_tel.group(0)

            total_r = 0.0
            valor_cobrado = 0.0
            in_servicos = False

            for line in bloco:
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

        df = pd.DataFrame.from_dict(registros, orient='index').fillna(0)
        df['Telefone'] = df.index
        colunas_totais = ["Total (R$)", "Valor Cobrado (R$)"]
        colunas_servico = [c for c in df.columns if c not in colunas_totais + ["Telefone"]]
        df = df[["Telefone"] + colunas_servico + colunas_totais]
        return df.reset_index(drop=True)

    def processar_tim(self, pdf):
        registros = []
        linhas = []
        for page in pdf.pages:
            palavras = page.extract_words(use_text_flow=False, keep_blank_chars=True)
            agrupadas = {}
            for palavra in palavras:
                top = round(palavra['top'], 1)
                agrupadas.setdefault(top, []).append((palavra['x0'], palavra['text']))
            for top in sorted(agrupadas.keys()):
                linha = " ".join(txt for _, txt in sorted(agrupadas[top], key=lambda x: x[0]))
                linhas.append(linha)

        for linha in linhas:
            if not re.search(r'\d{2}/\d{2}\s+a\s+\d{2}/\d{2}', linha):
                continue
            try:
                partes = linha.strip().split()
                valor = parse_num(partes[-1])
                iss = partes[-2]
                pis = partes[-3]
                icms = partes[-4]

                periodo_match = re.search(r"\d{2}/\d{2}\s+a\s+\d{2}/\d{2}", linha)
                if not periodo_match:
                    continue
                periodo = periodo_match.group(0)
                periodo_pos = linha.find(periodo)

                anteriores = re.findall(r"\d+", linha[:periodo_pos])
                if len(anteriores) < 2:
                    continue
                quantidade = int(anteriores[-2])
                dias = int(anteriores[-1])

                padrao_descr = re.compile(r"^(.*?)\s+" + str(quantidade) + r"\s+" + str(dias))
                m_descr = padrao_descr.match(linha)
                descricao = m_descr.group(1).strip() if m_descr else "DESCONHECIDO"

                if descricao != "DESCONHECIDO":
                    registros.append({
                        "MENSALIDADES E FRANQUIAS": descricao,
                        "QUANTIDADE": quantidade,
                        "N° DIAS": dias,
                        "PERÍODO": periodo,
                        "ICMS": icms,
                        "PIS/COFINS": pis,
                        "ISS": iss,
                        "VALOR": valor
                    })
            except:
                continue

        return pd.DataFrame(registros)

    def processar_globalstar(self, pdf_path):
        registros = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                palavras = page.extract_words(use_text_flow=False, keep_blank_chars=True)
                linhas = {}
                for palavra in palavras:
                    top = round(palavra['top'], 1)
                    linhas.setdefault(top, []).append((palavra['x0'], palavra['text']))

                linhas_ordenadas = [sorted(grupo, key=lambda w: w[0]) for _, grupo in sorted(linhas.items())]

                for linha in linhas_ordenadas:
                    texto_linha = [p for _, p in linha]
                    if len(texto_linha) >= 10:
                        registros.append({
                            "ESN": texto_linha[0],
                            "Plano": texto_linha[1],
                            "Tarifa Ativação": parse_valor(texto_linha[2]),
                            "Tarifa Mensal": parse_valor(texto_linha[3]),
                            "Mensagens Usadas": parse_valor(texto_linha[4]),
                            "Mensagens Incluídas": parse_valor(texto_linha[5]),
                            "Mensagens Tarifadas": parse_valor(texto_linha[6]),
                            "Tarifa de Uso": parse_valor(texto_linha[7]),
                            "Bytes": parse_valor(texto_linha[8]),
                            "Tarifa Total": parse_valor(texto_linha[9])
                        })
        return pd.DataFrame(registros)

    def processar_diretorio(self, diretorio: str) -> pd.DataFrame:
        self.dados_por_arquivo.clear()
        arquivos_pdf = [f for ext in ["*.pdf", "*.PDF"] for f in glob.glob(os.path.join(diretorio, ext))]

        for arquivo in sorted(set(arquivos_pdf)):
            nome_base = os.path.splitext(os.path.basename(arquivo))[0]
            print(f"Processando {arquivo}...")
            try:
                with pdfplumber.open(arquivo) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages[:3]])
                if "Simplex Message" in texto or "GLOBALSTAR" in texto or "Encargos Mensais" in texto:
                    df = self.processar_globalstar(arquivo)
                elif "DETALHAMENTO TOTAL DA CONTA" in texto:
                    with pdfplumber.open(arquivo) as pdf:
                        df = self.processar_vivo(pdf)
                elif "MENSALIDADES E FRANQUIAS" in texto:
                    with pdfplumber.open(arquivo) as pdf:
                        df = self.processar_tim(pdf)
                else:
                    with pdfplumber.open(arquivo) as pdf:
                        df = self.processar_claro(pdf)
                self.dados_por_arquivo[nome_base] = df
            except Exception as e:
                print(f"Erro ao processar {arquivo}: {e}")

        if self.dados_por_arquivo:
            self.df_consolidado = pd.concat(self.dados_por_arquivo.values(), ignore_index=True)
        return self.df_consolidado

    def salvar_em_excel_multiplas_planilhas(self, caminho_saida: str) -> bool:
        if not self.dados_por_arquivo:
            print("Nenhum dado para salvar")
            return False
        try:
            with pd.ExcelWriter(caminho_saida, engine='xlsxwriter') as writer:
                for nome_aba, df in self.dados_por_arquivo.items():
                    df.to_excel(writer, sheet_name=nome_aba[:31], index=False)
            print(f"Arquivo Excel salvo em {caminho_saida}")
            return True
        except Exception as e:
            print(f"Erro ao salvar Excel: {e}")
            return False

def gerar_nome_excel():
    agora = datetime.datetime.now()
    return f"faturas_operadoras_globalstar_{agora.strftime('%Y%m%d_%H%M%S')}.xlsx"

def main():
    print("\n=== Processador de Faturas (Claro + Vivo + TIM + Globalstar) ===\n")
    diretorio = input("Informe o diretório com os PDFs:\n> ").strip().strip('"\'')
    saida_excel = os.path.join(os.getcwd(), gerar_nome_excel())
    proc = ProcessadorFaturas()
    df_total = proc.processar_diretorio(diretorio)
    if df_total is not None:
        proc.salvar_em_excel_multiplas_planilhas(saida_excel)
        print("Processamento finalizado com sucesso.")
    else:
        print("Nenhum dado extraído.")

if __name__ == '__main__':
    main()
