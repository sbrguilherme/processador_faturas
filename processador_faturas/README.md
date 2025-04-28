# 📄 README - Processador de Faturas (Claro, Vivo, TIM, Globalstar)

## 📋 Descrição do Projeto
Este script Python automatiza o processamento de faturas das operadoras Claro, Vivo, TIM e Globalstar, extrai os dados relevantes e consolida todas as informações em um único arquivo Excel (.xlsx) com múltiplas planilhas.

---

## 🚀 Funcionalidades
- Detecta automaticamente o tipo de fatura.
- Extração de informações de:
  - **Claro**: Blocos de serviços, valores totais e cobrados.
  - **Vivo**: Detalhamento total da conta.
  - **TIM**: MENSALIDADES, FRANQUIAS, ICMS, PIS/COFINS, ISS.
  - **Globalstar**: Extração por coordenadas (top/x0).
- Gera arquivo Excel consolidado com abas separadas para cada fatura.
- Instala automaticamente as dependências necessárias.

---

## 🧩 Dependências Necessárias
- Python >= 3.8
- pdfplumber
- pandas
- openpyxl
- xlsxwriter

---

## 🛠 Como Utilizar

### 1. Instalar dependências
Utilize o script `instalar_dependencias.bat` para instalar automaticamente:

```bash
instalar_dependencias.bat
```

### 2. Rodar o Processador
Execute o script principal:

```bash
python seu_arquivo_principal.py
```

- Informe o diretório contendo as faturas em PDF quando solicitado.
- O script processará automaticamente e salvará o Excel de saída na mesma pasta.

---

## 📂 Estrutura de Arquivos
```
|➔ Processador_Claro_Vivo_TIM_Globalstar.py
|➔ instalar_dependencias.bat
|➔ README.md
|➔ [Pasta com PDFs]
```

---

## 🛡️ Observações Importantes
- Certifique-se de que o Python esteja no PATH do Windows.
- Os arquivos PDF devem estar no formato padrão das operadoras.
- O Excel gerado será salvo automaticamente com timestamp no nome do arquivo.

---

## 🤝 Contato
Para dúvidas ou suporte: financeiro2@sillion.com.br

---

# Boa utilização! 🚀