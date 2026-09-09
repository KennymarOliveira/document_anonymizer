# Document Anonymizer

API REST para **extração e anonimização automática de dados sensíveis** em documentos jurídicos brasileiros (PDF, DOCX, DOC e TXT).

A aplicação utiliza múltiplos motores de detecção — Regex, spaCy (NER), Embeddings semânticos e Microsoft Presidio — que podem ser combinados em um **Motor Híbrido** para máxima cobertura.

---

## Índice

- [Funcionalidades](#-funcionalidades)
- [Arquitetura](#-arquitetura)
- [Tecnologias](#-tecnologias)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
- [Como Executar](#-como-executar)
- [Como Usar a API](#-como-usar-a-api)
  - [Health Check](#health-check)
  - [Anonimizar Documento (JSON)](#anonimizar-documento-resposta-json)
  - [Anonimizar Documento (Arquivo)](#anonimizar-documento-resposta-arquivo)
- [Motores de Detecção](#-motores-de-detecção)
  - [RegexEngine](#1-regexengine)
  - [SpacyNerEngine](#2-spacynerengine)
  - [EmbeddingEngine](#3-embeddingengine)
  - [PresidioEngine](#4-presidioengine)
  - [HybridEngine](#5-hybridengine-padrão)
- [Como Funciona a Anonimização](#-como-funciona-a-anonimização)
- [Testes](#-testes)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Licença](#-licença)

---

## Funcionalidades

- **Extração de texto** de arquivos PDF, DOCX, DOC e TXT.
- **Detecção de dados sensíveis** usando 5 motores diferentes (individuais ou combinados).
- **Anonimização in-place**: os dados são removidos diretamente do documento original.
  - **PDF**: tarjas pretas vetoriais desenhadas sobre o texto sensível (redação irreversível).
  - **DOCX/DOC**: substituição do texto por blocos `█████`.
  - **TXT**: substituição do texto por blocos `█████`.
- **14 categorias de dados** detectadas automaticamente pelo motor de Regex.
- **20 termos semânticos** rastreados pelo motor de Embeddings via similaridade vetorial.
- **Resposta em JSON** (com texto anonimizado e lista de entidades) ou **download do arquivo anonimizado**.
- **Documentação interativa** via Swagger UI (`/docs`) e ReDoc (`/redoc`).

---

## Arquitetura

```
Cliente (upload) ──► FastAPI Endpoint (/api/v1/anonymize/)
                          │
                          ▼
                    file_extractor.py ──► Extrai texto bruto do arquivo
                          │
                          ▼
                 anonymization_service.py ──► Seleciona e executa o motor
                          │
                ┌─────────┼─────────────┐
                ▼         ▼             ▼
           RegexEngine  SpacyNER   PresidioEngine  ...
                │         │             │
                └─────────┼─────────────┘
                          ▼
                   HybridEngine (detect em paralelo + resolução de conflitos)
                          │
                          ▼
                   file_builder.py ──► Reconstrói o arquivo com tarjas pretas
                          │
                          ▼
               Resposta JSON ou Download do arquivo
```

---

## Tecnologias

| Componente | Tecnologia |
|---|---|
| Framework Web | [FastAPI](https://fastapi.tiangolo.com/) |
| Servidor ASGI | [Uvicorn](https://www.uvicorn.org/) |
| NLP (Entidades Nomeadas) | [spaCy](https://spacy.io/) + modelo `pt_core_news_lg` |
| NLP (Semântico) | [sentence-transformers](https://www.sbert.net/) + `paraphrase-multilingual-MiniLM-L12-v2` |
| NLP (PII) | [Microsoft Presidio](https://microsoft.github.io/presidio/) |
| Leitura de PDF | [pypdf](https://pypdf.readthedocs.io/) |
| Redação de PDF | [PyMuPDF](https://pymupdf.readthedocs.io/) |
| Leitura/Escrita DOCX | [python-docx](https://python-docx.readthedocs.io/) |
| Validação de dados | [Pydantic](https://docs.pydantic.dev/) |
| Gerenciador de pacotes | [Poetry](https://python-poetry.org/) |
| Testes | [pytest](https://docs.pytest.org/) |

---

## Pré-requisitos

- **Python** 3.11 ou superior
- **Poetry** instalado ([guia de instalação](https://python-poetry.org/docs/#installation))
- (Opcional) GPU NVIDIA com driver compatível para aceleração do `EmbeddingEngine`

---

## Instalação

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd document_anonymizer

# 2. Instale as dependências
poetry install

# 3. Baixe o modelo de NLP do spaCy para Português
poetry run python -m spacy download pt_core_news_lg
```

---

## Como Executar

### Modo desenvolvimento (com hot-reload)

```bash
poetry run uvicorn app.main:app --reload
```

A API estará disponível em `http://127.0.0.1:8000`.

### Documentação interativa

| Interface | URL |
|---|---|
| Swagger UI | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) |
| ReDoc | [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) |

---

## Como Usar a API

### Health Check

Verifica se a API está no ar.

```bash
curl http://127.0.0.1:8000/health
```

**Resposta:**
```json
{"status": "ok"}
```

---

### Anonimizar Documento (Resposta JSON)

Envia um arquivo e recebe o texto anonimizado + lista de entidades encontradas em formato JSON.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/anonymize/ \
  -F "file=@documento.pdf" \
  -F "engine=hybrid" \
  -F "return_format=json"
```

**Parâmetros do formulário:**

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `file` | Upload | *(obrigatório)* | Arquivo `.txt`, `.doc`, `.docx` ou `.pdf` |
| `engine` | String | `hybrid` | Motor de detecção: `regex`, `spacy`, `embedding`, `presidio` ou `hybrid` |
| `return_format` | String | `json` | Formato da resposta: `json` ou `file` |

**Resposta JSON (200):**

```json
{
  "original_filename": "peticao.pdf",
  "anonymized_text": "O autor [PER_ANONIMIZADO], portador do [CPF_ANONIMIZADO], residente em [LOC_ANONIMIZADO]...",
  "entities_found": [
    {"text": "João da Silva", "label": "PER", "engine": "Spacy"},
    {"text": "123.456.789-00", "label": "CPF", "engine": "Regex"},
    {"text": "Belo Horizonte", "label": "LOC", "engine": "Spacy"}
  ]
}
```

---

### Anonimizar Documento (Resposta Arquivo)

Envia um arquivo e recebe de volta o **próprio arquivo anonimizado** para download, com os dados sensíveis tarjados.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/anonymize/ \
  -F "file=@documento.pdf" \
  -F "engine=hybrid" \
  -F "return_format=file" \
  -o anonimizado_documento.pdf
```

- **PDF**: Os dados sensíveis são cobertos com tarjas pretas vetoriais (redação irreversível).
- **DOCX/DOC**: Os dados sensíveis são substituídos por blocos `█████`.
- **TXT**: Os dados sensíveis são substituídos por blocos `█████`.

O arquivo retornado terá o nome `anonimizado_<nome_original>`.

---

## Motores de Detecção

### 1. `RegexEngine`

Motor baseado em **expressões regulares** para detectar padrões exatos de dados estruturados brasileiros.

| Label | O que detecta | Exemplo |
|---|---|---|
| `CPF` | CPF com ou sem pontuação | `123.456.789-00`, `12345678900` |
| `CNPJ` | CNPJ com ou sem pontuação | `12.345.678/0001-99`, `12345678000199` |
| `EMAIL` | Endereços de e-mail | `joao@exemplo.com.br` |
| `PROCESSO` | Número de processo judicial (padrão CNJ) | `0001234-56.2020.8.13.0034` |
| `OAB` | Registro da OAB | `OAB/MG 123456` |
| `PLACA` | Placa de veículo (antigo e Mercosul) | `ABC1234`, `ABC1D23` |
| `CEP` | Código de Endereçamento Postal | `30130-000`, `30130000` |
| `MANDADO` | Número de mandado de prisão (BNMP) | `1234567-89.2020.8.13.0000.01.0001-00` |
| `BOLETIM_OCORRENCIA` | Inquérito Policial, B.O. ou APF | `IP 123/2023`, `APF 45/2021` |
| `RG` | Registro Geral (identidade) | `RG 12.345.678-9` |
| `CNH` | Carteira Nacional de Habilitação | `CNH 12345678901` |
| `AUTHORITY` | Título + nome de autoridade | `Juiz Carlos Eduardo da Silva` |
| `CODIGO_AUTENTICACAO` | Códigos hexadecimais de autenticação | `C019-B4CF-AAEF-E58A` |
| `MEDIDA_PROVISORIA` | Referência a Medida Provisória | `MP n° 2.200-2/2001` |

**Uso:** `engine=regex`

---

### 2. `SpacyNerEngine`

Motor de **Reconhecimento de Entidades Nomeadas (NER)** usando o modelo `pt_core_news_lg` do spaCy, treinado em português.

| Label | O que detecta | Exemplo |
|---|---|---|
| `PER` | Nomes de pessoas | `João da Silva` |
| `LOC` | Locais, cidades, estados, países | `São Paulo`, `Brasil` |
| `ORG` | Organizações, empresas, órgãos | `Tribunal de Justiça` |

**Uso:** `engine=spacy`

---

### 3. `EmbeddingEngine`

Motor de **similaridade semântica** usando o modelo `paraphrase-multilingual-MiniLM-L12-v2`. Compara cada palavra do texto com uma lista de 20 termos sensíveis usando similaridade de cosseno. Palavras com similaridade acima de 80% são anonimizadas.

**Termos sensíveis monitorados:**

| Categoria | Termos |
|---|---|
| Dados financeiros | `senha`, `conta`, `cartão`, `confidencial` |
| Figuras processuais | `testemunha`, `vítima`, `menor`, `filho`, `paciente`, `impetrante` |
| Sistema prisional | `presídio`, `penitenciária`, `CDP`, `filiação`, `genitora` |
| Dados de saúde (LGPD sensíveis) | `doença`, `comorbidade`, `tratamento` |
| Bens e veículos | `veículo`, `placa` |

> **Nota:** Por funcionar via similaridade semântica, este motor também detecta **sinônimos e termos relacionados** que não estão explicitamente na lista (ex: "ofendido" pode ser capturado por similaridade com "vítima").

**Uso:** `engine=embedding`

---

### 4. `PresidioEngine`

Motor da **Microsoft Presidio** configurado para português, que traz dezenas de reconhecedores pré-treinados para PII (Personally Identifiable Information).

Detecta automaticamente: `CREDIT_CARD`, `PHONE_NUMBER`, `IBAN_CODE`, `IP_ADDRESS`, `URL`, `DATE_TIME`, `PERSON`, `LOCATION`, `EMAIL_ADDRESS`, entre outros.

**Uso:** `engine=presidio`

---

### 5. `HybridEngine` (Padrão)

O motor **recomendado**. Combina `RegexEngine` + `SpacyNerEngine` + `PresidioEngine` em uma execução **paralela**:

1. Todos os motores executam `.detect()` simultaneamente sobre o texto **original**.
2. Os candidatos são ordenados por posição e tamanho.
3. **Conflitos de sobreposição** são resolvidos automaticamente: a entidade mais longa prevalece.
4. O texto é anonimizado uma única vez com todas as entidades selecionadas.

**Uso:** `engine=hybrid` *(padrão, não precisa especificar)*

---

## Como Funciona a Anonimização

### Fluxo completo

```
1. Upload do arquivo (PDF/DOCX/TXT)
          │
2. Extração do texto bruto (file_extractor)
          │
3. Detecção de entidades sensíveis (engine selecionada)
          │
4. Geração da resposta:
   ├── JSON: texto com tags [LABEL_ANONIMIZADO] + lista de entidades
   └── FILE: arquivo reconstruído com tarjas pretas / blocos █
```

### Formato das tags no JSON

Cada dado sensível é substituído por uma tag no formato `[LABEL_ANONIMIZADO]`:

| Dado original | Tag de substituição |
|---|---|
| `123.456.789-00` | `[CPF_ANONIMIZADO]` |
| `João da Silva` | `[PER_ANONIMIZADO]` |
| `São Paulo` | `[LOC_ANONIMIZADO]` |
| `Tribunal de Justiça` | `[ORG_ANONIMIZADO]` |
| `joao@email.com` | `[EMAIL_ANONIMIZADO]` |

---

## Testes

Este projeto possui até o momento **59 testes automatizados** cobrindo todas as camadas:

```bash
# Executar todos os testes
poetry run pytest -v

# Executar apenas testes de uma camada específica
poetry run pytest tests/test_engines.py -v      # Motores de detecção
poetry run pytest tests/test_api.py -v           # Endpoints da API
poetry run pytest tests/test_builders.py -v      # Construtores de arquivo
poetry run pytest tests/test_extractors.py -v    # Extratores de texto
```

### Cobertura dos testes

| Arquivo | O que testa | Qtd |
|---|---|---|
| `test_engines.py` | Todos os 14 padrões do Regex, HybridEngine, resolução de conflitos | 25 |
| `test_api.py` | Rotas HTTP, erros 400/422/500, formatos de resposta | 18 |
| `test_builders.py` | Anonimização in-place (DOCX, PDF, TXT), roteamento por extensão | 5 |
| `test_extractors.py` | Extração de texto de cada formato, tratamento de arquivos corrompidos | 11 |

---

## Estrutura do Projeto

```
document_anonymizer/
├── app/
│   ├── main.py                          # Ponto de entrada FastAPI
│   ├── api/
│   │   └── endpoints/v1/
│   │       └── anonymize.py             # Endpoint POST /api/v1/anonymize/
│   ├── core/
│   │   ├── builders/
│   │   │   └── file_builder.py          # Reconstrói arquivos com tarjas/blocos
│   │   ├── engines/
│   │   │   ├── base.py                  # Classe abstrata BaseEngine
│   │   │   ├── regex_engine.py          # Motor de Regex (14 padrões)
│   │   │   ├── spacy_engine.py          # Motor spaCy NER (PER, LOC, ORG)
│   │   │   ├── embedding_engine.py      # Motor de Embeddings (20 termos)
│   │   │   ├── presidio_engine.py       # Motor Microsoft Presidio
│   │   │   └── hybrid_engine.py         # Motor Híbrido (combinação paralela)
│   │   └── extractors/
│   │       └── file_extractor.py        # Extrai texto de PDF, DOCX, TXT
│   ├── schemas/
│   │   └── anonymizer.py               # Schemas Pydantic de resposta
│   └── services/
│       └── anonymization_service.py     # Orquestra extração + anonimização
├── tests/
│   ├── utils.py                         # Helpers para gerar DOCX/PDF de teste
│   ├── test_api.py                      # Testes da API
│   ├── test_engines.py                  # Testes dos motores
│   ├── test_builders.py                 # Testes dos construtores
│   └── test_extractors.py              # Testes dos extratores
├── pyproject.toml                       # Configuração Poetry + dependências
└── README.md                            # Este arquivo
```

---

## Licença

Este projeto é de uso interno. Consulte o autor para informações sobre licenciamento.