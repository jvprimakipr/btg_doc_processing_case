# BTG Processamento de Documentos de Eventos Corporativos

Agente para extração e validação de informações de eventos corporativos a partir de documentos PDF.

O pipeline processa documentos heterogêneos, utiliza extração de texto direta ou por OCR, classifica o evento corporativo, extrai os dados relevantes e realiza validações contra os registros de referência e contra regras de coerência.

## Requisitos

- Python 3.10+
- Tesseract OCR
- Uma API key da Groq

---

## 1. Instalação do Tesseract OCR

O projeto utiliza o [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) como fallback para documentos PDF que não possuem texto extraível diretamente.

Baixe e instale o Tesseract para Windows:

https://github.com/UB-Mannheim/tesseract/wiki

Durante a instalação, certifique-se de que o executável do Tesseract esteja disponível no `PATH` do sistema. Caso tenha dificuldades com o `PATH`, você pode [adicionar manualmente o diretório de instalação do Tesseract às variáveis de ambiente do Windows](https://docs.coro.net/featured/agent/install-tesseract-windows).

Após a instalação, é possível verificar se ele está disponível executando no terminal:

```bash
tesseract --version
```

O comando deve retornar a versão instalada do Tesseract.

---

## 2. Criar o ambiente virtual

Na raiz do projeto, crie um ambiente virtual utilizando o terminal:

```bash
python -m venv .venv
```

Ative o ambiente virtual.

### Windows — PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

### Windows — CMD

```cmd
.venv\Scripts\activate
```

Depois de ativado, instale as dependências:

```bash
pip install -r requirements.txt
```

---

## 3. Configurar a API

O projeto utiliza variáveis de ambiente para configurar o provedor de LLM.

Copie o arquivo `.env.example` para `.env`:

Abra o arquivo `.env` e informe sua API key da Groq:

```env
DEFAULT_LLM_PROVIDER="groq"

...

GROQ_API_KEY="sua_api_key_aqui"
GROQ_MODEL="openai/gpt-oss-20b"
```

A API key pode ser obtida no console da Groq:

https://console.groq.com/keys

> **Importante:** devido à disponibilidade limitada de APIs durante o desenvolvimento, o funcionamento com os demais provedores/modelos configurados no projeto ainda não foi verificado. Portanto, no estado atual, o projeto deve ser testado utilizando **exclusivamente a Groq**. Essa IA foi escolhida principalmente por oferecer uma boa quantidade de chamadas pela API no plano gratuito.

---

## 4. Executar o agente

O agente pode ser executado diretamente pelo terminal.

Com o ambiente virtual ativado, utilize:

```bash
python -m .\src\main.py
```

O agente irá processar os documentos da pasta `documents` e gerar os resultados na pasta `output`.

Caso queira executar para alguma pasta específica, utilize o argumento `--docs`:

```bash
python -m .\src\main.py --docs caminho/para/sua/pasta
```

E se o objetivo for para só um arquivo específico:

```bash
python -m .\src\main.py --docs caminho/para/seu/documento.pdf
```

---

## Fluxo do processamento

De forma simplificada, o pipeline funciona da seguinte maneira:

```text
PDF
 │
 ├── PyMuPDF
 │     └── texto extraído com sucesso
 │
 └── Tesseract OCR
       └── utilizado como fallback quando necessário
              │
              ▼
        Extração pelo LLM
              │
              ▼
       Validação do schema
              │
              ▼
    Validação com golden records
              │
              ▼
      Validação de coerência
              │
              ▼
       Resultado estruturado
```

O LLM é responsável principalmente pela interpretação do conteúdo e classificação do evento, enquanto as etapas determinísticas de extração, validação e comparação com os registros de referência são controladas pelo código Python. Essas decisões foram tomadas para reduzir o custo do processamento de arquivos diretamente com a IA escolhida.