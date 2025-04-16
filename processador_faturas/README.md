
# 📄 Processador de Faturas Claro

Este projeto tem como objetivo **processar automaticamente faturas da operadora Claro em formato PDF**, extraindo informações relevantes como número de telefone, plano contratado, consumo de serviços e valores faturados.

## 🚀 Funcionalidades

- Processamento de múltiplas faturas PDF simultaneamente
- Extração de:
  - Número de telefone
  - Tipo de plano ou pacote
  - Serviços cobrados por período
  - Valores totais e por item
- Geração de planilha `.xlsx` consolidada
- Compatível com formatos de fatura variados (com e sem identificadores fixos)
- Totalmente automatizado, com foco em faturas de planos empresariais

## 🧾 Estrutura de Arquivos

- `processador_main.py`: Script principal de execução
- `extrator_fatura.py`: Módulo de extração e análise das faturas PDF
- `faturas_claro_YYYYMMDD_HHMMSS.xlsx`: Saída gerada automaticamente contendo os dados extraídos

## 🛠️ Requisitos e Instalação

### 📦 Dependências

As seguintes bibliotecas são necessárias para rodar o projeto:

```bash
pip install pandas pdfplumber xlsxwriter
```

### ✅ Versões testadas

- Python 3.10+
- `pandas` 1.5+
- `pdfplumber` 0.10+
- `xlsxwriter` 3.0+

## 🖥️ Como Usar

1. Coloque os arquivos PDF das faturas da Claro em uma pasta acessível
2. Execute o script principal com:

```bash
python processador_main.py
```

3. O script irá:
   - Procurar por arquivos PDF no diretório atual ou designado
   - Processar cada fatura
   - Salvar uma planilha `.xlsx` com os dados extraídos, nomeada conforme a data de execução

## 🧠 Lógica de Processamento

- A leitura dos arquivos PDF é feita com `pdfplumber`
- Os padrões de layout são detectados automaticamente
- Os dados são estruturados por linha telefônica e organizados em colunas padronizadas
- Em casos de múltiplos blocos de serviços (como "Mensalidades", "Pacotes", "Cobranças e Descontos"), os valores são associados à linha correspondente

## 🐞 Validação de Resultados

O arquivo gerado contém colunas organizadas para facilitar conferência e auditoria. Recomenda-se:

- Verificar se todos os telefones esperados foram extraídos
- Validar eventuais valores zerados ou campos incompletos

## 🖼️ Observações Adicionais

- O projeto foi desenvolvido para lidar com diferentes versões de layout de faturas Claro
- Em caso de erro de leitura ou falha no reconhecimento do layout, revise o conteúdo visual do PDF ou atualize os padrões no script `extrator_fatura.py`
