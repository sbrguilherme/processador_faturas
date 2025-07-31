import streamlit as st
import pandas as pd
import tempfile
import os
import pdfplumber
from processador_main import ProcessadorFaturas, gerar_nome_excel

st.set_page_config(page_title="Processador de Faturas", layout="wide")
st.title("📑 Processador de Faturas - Claro, Vivo, TIM, Globalstar")

st.markdown("""
Este aplicativo permite fazer o upload de faturas em PDF das operadoras **Claro**, **Vivo**, **TIM** e **Globalstar**,
e extrair os dados consolidados em um arquivo Excel (.xlsx).
""")

uploaded_files = st.file_uploader(
    label="📂 Selecione os arquivos PDF das faturas",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files:
    with st.spinner("Processando faturas..."):
        # Cria pasta temporária para salvar arquivos
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = []
            for file in uploaded_files:
                file_path = os.path.join(temp_dir, file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
                paths.append(file_path)

            # Processa faturas
            proc = ProcessadorFaturas()
            for caminho in paths:
                nome = os.path.splitext(os.path.basename(caminho))[0]
                try:
                    with open(caminho, "rb") as f:
                        texto = "\n".join([p.extract_text() or "" for p in pdfplumber.open(f).pages[:3]])
                    if "Simplex Message" in texto or "GLOBALSTAR" in texto or "Encargos Mensais" in texto:
                        df = proc.processar_globalstar(caminho)
                    elif "DETALHAMENTO TOTAL DA CONTA" in texto:
                        df = proc.processar_vivo(pdfplumber.open(caminho))
                    elif "MENSALIDADES E FRANQUIAS" in texto:
                        df = proc.processar_tim(pdfplumber.open(caminho))
                    else:
                        df = proc.processar_claro(pdfplumber.open(caminho))
                    proc.dados_por_arquivo[nome] = df
                except Exception as e:
                    st.warning(f"Erro ao processar {nome}: {e}")

            if proc.dados_por_arquivo:
                st.success("Faturas processadas com sucesso!")
                for nome, df in proc.dados_por_arquivo.items():
                    st.subheader(f"📄 {nome}")
                    st.dataframe(df, use_container_width=True)

                # Gera Excel
                output_excel = os.path.join(temp_dir, gerar_nome_excel())
                proc.salvar_em_excel_multiplas_planilhas(output_excel)
                with open(output_excel, "rb") as f:
                    bytes_data = f.read()

                st.download_button(
                    label="📥 Baixar Excel Consolidado",
                    data=bytes_data,
                    file_name=os.path.basename(output_excel),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            else:
                st.error("Nenhum dado extraído de nenhum arquivo.")
