# Document Anonymizer (Anonimizador de Documentos)

API REST para **extração e anonimização automática de dados sensíveis** em documentos jurídicos brasileiros (PDF, DOCX, DOC e TXT), com suporte a upload direto de arquivos e integração com **Google Drive**.

A aplicação utiliza múltiplos motores de detecção — Regex, spaCy (NER), Embeddings semânticos, Microsoft Presidio e Legal NER (LeNER-BR) — que podem ser executados individualmente ou combinados em um **Motor Híbrido** para máxima cobertura.

---

## Índice

- [Funcionalidades](#funcionalidades)
- [Arquitetura e Fluxo de Chamadas](#arquitetura-e-fluxo-de-chamadas)
- [Tecnologias](#tecnologias)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
  - [Opção 1: Usando Poetry (Recomendado)](#opção-1-usando-poetry-recomendado)
  - [Opção 2: Usando Pip e Virtualenv Tradicional (Sem Poetry)](#opção-2-usando-pip-e-virtualenv-tradicional-sem-poetry)
  - [Download dos Modelos de NLP](#download-dos-modelos-de-nlp)
- [Configurações e Variáveis de Ambiente](#configurações-e-variáveis-de-ambiente)
- [Como Executar](#como-executar)
- [Como Usar a API](#como-usar-a-api)
  - [Health Check](#health-check)
  - [Anonimizar Documento via Upload (JSON)](#anonimizar-documento-via-upload-resposta-json)
  - [Anonimizar Documento via Upload (Arquivo)](#anonimizar-documento-via-upload-resposta-arquivo)
  - [Anonimizar Documento do Google Drive](#anonimizar-documento-do-google-drive)
- [Motores de Detecção](#motores-de-detecção)
  - [1. RegexEngine](#1-regexengine)
  - [2. SpacyNerEngine](#2-spacynerengine)
  - [3. EmbeddingEngine](#3-embeddingengine)
  - [4. PresidioEngine](#4-presidioengine)
  - [5. LegalNerEngine](#5-legalnerengine)
  - [6. HybridEngine (Padrão)](#6-hybridengine-padrão)
- [Modos de Redação (Tarjas)](#modos-de-redação-tarjas)
- [Como Funciona a Anonimização](#como-funciona-a-anonimização)
- [Benchmark e Avaliação de Desempenho](#benchmark-e-avaliação-de-desempenho)
- [Testes](#testes)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Licença](#licença)

---

## Funcionalidades

- **Extração de texto** de arquivos PDF, DOCX, DOC e TXT (com paginação e tratamento de acentuação).
- **Integração com Google Drive**: busca documentos remotos por ID com suporte a fallback Mock e autenticação real via Service Account.
- **Detecção de dados sensíveis** usando 6 motores diferentes (individuais ou combinados).
- **Anonimização in-place**: os dados são removidos diretamente do documento original.
  - **PDF**: tarjas vetoriais desenhadas diretamente sobre as coordenadas exatas do texto (redação irreversível).
  - **DOCX/DOC**: substituição do texto sensível por blocos tarjados preservando estilos e formatação.
  - **TXT**: substituição textual in-place.
- **Dois estilos de tarja (`redaction_mode`)**:
  - `blackout` (tarja preta sólida tradicional).
  - `black_white_text` (tarja preta com o texto da classificação em branco sobreposto, ex: `[CPF]`).
- **16 categorias de dados** detectadas automaticamente por Regex especializado no padrão brasileiro.
- **20 termos semânticos** monitorados pelo motor de Embeddings via similaridade vetorial.
- **Resposta em JSON** (com texto anonimizado e lista de entidades) ou **download via streaming** do arquivo tarjado.
- **Tratamento robusto de erros**: handlers de segurança centralizados que evitam vazamento de mensagens internas sensíveis.
- **Módulo de Benchmark e Avaliação**: avaliação quantitativa com Matriz de Confusão, Precision, Recall, F1-Score e gráficos exportados.
- **Documentação interativa** via Swagger UI (`/docs`) e ReDoc (`/redoc`).

---

## Arquitetura e Fluxo de Chamadas

A aplicação segue uma estrutura modular com separação clara de responsabilidades:

```
Cliente HTTP (Upload ou JSON)
          │
          ▼
      routes.py (FastAPI App & Rotas Centrais)
          │
          ▼
   app/services/views.py (Controllers & Validação)
          │
          ├───────────────────────────────┐
          │ (Google Drive ID)             │ (Upload direto)
          ▼                               │
app/core/integrations/google_drive.py     │
          │                               │
          └───────────────┬───────────────┘
                          ▼
            app/services/anonymization_service.py
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
app/core/extractors/file_extractor.py   app/core/engines/
(Extração página a página)             (Regex, Spacy, Presidio, LegalNER, Hybrid)
                          │
                          ▼
             Entidades & Texto Anonimizado
                          │
             ┌────────────┴────────────┐
             │ return_format == "file" │ return_format == "json"
             ▼                         ▼
app/core/builders/file_builder.py    app/schemas/anonymizer.py
(Geração de PDF/DOCX tarjado)        (Serialização JSON)
             │                         │
             └────────────┬────────────┘
                          ▼
                  Resposta ao Cliente
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
| NLP Jurídico | [BERT / HuggingFace Transformers](https://huggingface.co/) + `pierreguillou/ner-bert-base-cased-pt-lenerbr` |
| Integração Nuvem | [Google API Python Client](https://github.com/googleapis/google-api-python-client) |
| Leitura de PDF | [pypdf](https://pypdf.readthedocs.io/) |
| Redação de PDF | [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) |
| Leitura/Escrita DOCX | [python-docx](https://python-docx.readthedocs.io/) |
| Validação de dados | [Pydantic v2](https://docs.pydantic.dev/) |
| Gerenciador de pacotes | [Poetry](https://python-poetry.org/) |
| Testes | [pytest](https://docs.pytest.org/) |

---

## Pré-requisitos

- **Python** 3.11 ou superior
- **Poetry** (recomendado) ou **pip** + **venv**
- (Opcional) GPU NVIDIA com driver compatível para aceleração do `EmbeddingEngine` e `LegalNerEngine`

---

## Instalação

O projeto utiliza o **Poetry** para gerenciar dependências e ambientes virtuais, mas também oferece compatibilidade com `pip` via `requirements.txt`.

### Opção 1: Usando Poetry (Recomendado)

O Poetry gerencia automaticamente o ambiente virtual e instala as versões exatas travadas em `poetry.lock`.

#### 1. Instalar o Poetry (se ainda não tiver)

```bash
# Via pipx (recomendado):
pipx install poetry

# Ou via instalador oficial:
curl -sSL https://install.python-poetry.org | python3 -

# Ou via pip:
pip install poetry
```

#### 2. Clonar o repositório e entrar no diretório

```bash
git clone <url-do-repositorio>
cd document_anonymizer
```

#### 3. Instalar as dependências do projeto

```bash
# Instala todas as dependências (produção + desenvolvimento/testes/benchmark):
poetry install

# Caso deseje instalar apenas dependências de produção:
poetry install --without dev
```

#### 4. Baixar o modelo de NLP do spaCy para Português

O motor spaCy necessita do modelo pré-treinado `pt_core_news_lg`:

```bash
poetry run python -m spacy download pt_core_news_lg
```

---

### Opção 2: Usando Pip e Virtualenv Tradicional (Sem Poetry)

Se preferir não usar o Poetry, você pode utilizar o ambiente virtual padrão do Python:

#### 1. Clonar o repositório e entrar na pasta

```bash
git clone <url-do-repositorio>
cd document_anonymizer
```

#### 2. Criar e ativar um ambiente virtual

```bash
# Cria o ambiente virtual
python3 -m venv .venv

# Ativa o ambiente virtual (Linux/macOS):
source .venv/bin/activate

# Ativa o ambiente virtual (Windows PowerShell):
.venv\Scripts\Activate.ps1
```

#### 3. Instalar as dependências via Pip

```bash
# Atualiza o pip
pip install --upgrade pip

# Instala as dependências da aplicação:
pip install -r requirements.txt

# (Opcional) Instala dependências de testes e benchmarks:
pip install -r requirements-dev.txt
```

#### 4. Baixar o modelo de NLP do spaCy para Português

```bash
python -m spacy download pt_core_news_lg
```

---

### Download dos Modelos de NLP

- **spaCy (`pt_core_news_lg`)**: Precisa ser baixado manualmente uma única vez conforme o passo 4 acima.
- **Hugging Face / Transformers**:
  - `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (usado pelo `EmbeddingEngine`)
  - `pierreguillou/ner-bert-base-cased-pt-lenerbr` (usado pelo `LegalNerEngine`)

  Esses modelos são **baixados e cacheados automaticamente** pelo Hugging Face na primeira vez em que os respectivos motores forem executados (armazenados em `~/.cache/huggingface/hub/`).

---

## Configurações e Variáveis de Ambiente

As configurações são gerenciadas centralizadamente por `app/core/configuration/settings.py` e podem ser definidas em um arquivo `.env` na raiz do projeto:

| Variável | Padrão | Descrição |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Nível de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `USE_GOOGLE_DRIVE_MOCK` | `true` | Se `true`, utiliza o cliente mock embutido para testes locais sem credenciais reais |
| `GOOGLE_APPLICATION_CREDENTIALS` | `None` | Caminho para o arquivo `.json` de credenciais de Service Account do Google Cloud |

Exemplo de `.env`:

```ini
LOG_LEVEL=INFO
USE_GOOGLE_DRIVE_MOCK=true
# GOOGLE_APPLICATION_CREDENTIALS=/caminho/para/service-account.json
```

---

## Como Executar

> **Atenção:** Antes de executar a aplicação pela primeira vez, certifique-se de ter concluído o processo de [Instalação](#instalação) (especialmente a instalação de dependências e o download do modelo spaCy).

### Modo desenvolvimento (com hot-reload)

**Se estiver utilizando Poetry:**

```bash
# Execução direta pelo Poetry:
poetry run uvicorn routes:app --reload

# Ou ativando o ambiente virtual do Poetry previamente:
poetry shell
uvicorn routes:app --reload
```

**Se estiver utilizando Virtualenv tradicional (`venv` / `pip`):**

```bash
# Com o ambiente virtual ativado (source .venv/bin/activate):
uvicorn routes:app --reload
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

Verifica se a API está operacional.

```bash
curl http://127.0.0.1:8000/health
```

**Resposta:**
```json
{"status": "ok"}
```

---

### Anonimizar Documento via Upload (Resposta JSON)

Envia um arquivo e recebe o texto anonimizado e a lista de entidades encontradas em JSON:

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
| `engine` | String | `hybrid` | Motor: `regex`, `spacy`, `embedding`, `presidio`, `legal_ner` ou `hybrid` |
| `return_format` | String | `json` | Formato: `json` ou `file` |
| `redaction_mode` | String | `blackout` | Modo da tarja: `blackout` ou `black_white_text` |

**Resposta JSON (200):**

```json
{
  "original_filename": "peticao.pdf",
  "anonymized_text": "O autor [PER_ANONIMIZADO], portador do [CPF_ANONIMIZADO], residente em [LOC_ANONIMIZADO]...",
  "entities_found": [
    {"text": "João da Silva", "label": "PER", "engine": "Spacy", "page": 1},
    {"text": "123.456.789-00", "label": "CPF", "engine": "Regex", "page": 1},
    {"text": "Belo Horizonte", "label": "LOC", "engine": "Spacy", "page": 1}
  ]
}
```

---

### Anonimizar Documento via Upload (Resposta Arquivo)

Envia um arquivo e recebe de volta o **próprio arquivo anonimizado** para download, com os dados sensíveis tarjados:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/anonymize/ \
  -F "file=@documento.pdf" \
  -F "engine=hybrid" \
  -F "return_format=file" \
  -F "redaction_mode=blackout" \
  -o anonimizado_documento.pdf
```

O arquivo retornado terá o nome `anonimizado_<nome_original>`.

---

### Anonimizar Documento do Google Drive

Anonimiza um arquivo hospedado no Google Drive diretamente por seu `file_id`:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/anonymize/google-doc \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "1A2B3C4D5E6F7G8H9I0J",
    "engine": "hybrid",
    "return_format": "json",
    "redaction_mode": "blackout"
  }'
```

- Para receber o arquivo tarjado diretamente para download, informe `"return_format": "file"`.
- Em ambiente de testes sem credenciais, arquivos com IDs de mock (ex: `doc-corporativo-123`) são resolvidos pelo `MockGoogleDriveClient`.

---

## Motores de Detecção

### 1. `RegexEngine`

Motor baseado em **expressões regulares** para padrões exatos de dados estruturados brasileiros:

| Label | O que detecta | Exemplo |
|---|---|---|
| `CPF` | CPF com ou sem pontuação | `123.456.789-00`, `12345678900` |
| `CNPJ` | CNPJ com ou sem pontuação | `12.345.678/0001-99`, `12345678000199` |
| `EMAIL` | Endereços de e-mail | `joao@exemplo.com.br` |
| `PROCESSO` | Processo CNJ, tribunais superiores e estaduais | `0001234-56.2020.8.13.0034`, `RE 851.421`, `ADI 2549` |
| `OAB` | Registro da OAB com ou sem prefixo | `OAB/MG 123456`, `8290/DF` |
| `PLACA` | Placa de veículo (antigo e Mercosul) | `ABC1234`, `ABC1D23` |
| `CEP` | Código de Endereçamento Postal | `30130-000`, `30130000` |
| `MANDADO` | Número de mandado de prisão (BNMP) | `1234567-89.2020.8.13.0000.01.0001-00` |
| `BOLETIM_OCORRENCIA` | Inquérito Policial, B.O. ou APF | `IP 123/2023`, `APF 45/2021` |
| `RG` | Registro Geral (identidade) | `RG 12.345.678-9` |
| `CNH` | Carteira Nacional de Habilitação | `CNH 12345678901` |
| `AUTHORITY` | Título + nome de autoridade | `Juiz Carlos Eduardo da Silva`, `Ministro Roberto Barroso` |
| `CODIGO_AUTENTICACAO` | Códigos hexadecimais de autenticação | `C019-B4CF-AAEF-E58A` |
| `MEDIDA_PROVISORIA` | Referência a Medida Provisória | `MP n° 2.200-2/2001` |
| `URL` | Endereços web e links | `http://www.stf.jus.br/portal` |
| `DATA` | Datas numéricas e por extenso | `18/12/2021`, `22 de outubro de 2020` |

**Uso:** `engine=regex`

---

### 2. `SpacyNerEngine`

Motor de **Reconhecimento de Entidades Nomeadas (NER)** usando o modelo `pt_core_news_lg` do spaCy, treinado em português:

| Label | O que detecta | Exemplo |
|---|---|---|
| `PER` | Nomes de pessoas | `João da Silva` |
| `LOC` | Locais, cidades, estados, países | `São Paulo`, `Brasil` |
| `ORG` | Organizações, empresas, órgãos | `Tribunal de Justiça` |

**Uso:** `engine=spacy`

---

### 3. `EmbeddingEngine`

Motor de **similaridade semântica** usando o modelo `paraphrase-multilingual-MiniLM-L12-v2`. Compara sentenças ou termos do texto contra categorias sensíveis via similaridade de cosseno:

| Categoria | Exemplos de Termos Monitorados |
|---|---|
| Dados financeiros | `senha`, `conta`, `cartão`, `confidencial` |
| Figuras processuais | `testemunha`, `vítima`, `menor`, `filho`, `paciente`, `impetrante` |
| Sistema prisional | `presídio`, `penitenciária`, `CDP`, `filiação`, `genitora` |
| Dados de saúde (LGPD) | `doença`, `comorbidade`, `tratamento` |
| Bens e veículos | `veículo`, `placa` |

**Uso:** `engine=embedding`

---

### 4. `PresidioEngine`

Motor da **Microsoft Presidio** configurado para português, com reconhecedores pré-treinados para PII (*Personally Identifiable Information*):
- Detecta: `CREDIT_CARD`, `PHONE_NUMBER`, `IBAN_CODE`, `IP_ADDRESS`, `URL`, `DATE_TIME`, `PERSON`, `LOCATION`, `EMAIL_ADDRESS`, etc.

**Uso:** `engine=presidio`

---

### 5. `LegalNerEngine`

Motor especializado em documentos jurídicos brasileiros baseado no modelo BERT fine-tuned no dataset **LeNER-BR** (`pierreguillou/ner-bert-base-cased-pt-lenerbr`).
- Detecta com alta precisão entidades jurídicas (`PESSOA`, `TEMPO`, `LOCAL`, `ORGANIZACAO`, `LEGISLACAO`, `JURISPRUDENCIA`).
- Inclui denylist jurídica que evita falsos positivos em vocativos, papéis processuais e expressões de praxe judiciária (ex: *vossa excelência*, *apelante*, *douto parquet*).

**Uso:** `engine=legal_ner` (aliases: `legal`, `lener`, `lenerbr`)

---

### 6. `HybridEngine` (Padrão)

O motor **recomendado**. Combina `RegexEngine` + `SpacyNerEngine` + `PresidioEngine` com execução simultânea e resolução de conflitos:
1. Todos os motores executam a detecção sobre o texto original.
2. Conflitos de sobreposição são resolvidos priorizando a entidade mais longa e respeitando a hierarquia de precisão.
3. O texto é anonimizado em uma única passagem.

**Uso:** `engine=hybrid` *(padrão)*

---

## Modos de Redação (Tarjas)

Ao solicitar a resposta em arquivo (`return_format=file`), o parâmetro `redaction_mode` controla a aparência visual da tarja:

- **`blackout`** (ou `tarja_preta`): tarja sólida preta desenhada sobre as coordenadas exatas da entidade.
- **`black_white_text`** (ou `tarja_texto_branco`): tarja preta com texto branco indicando o tipo de entidade suprimida (ex: `[CPF]`, `[PER]`).

---

## Como Funciona a Anonimização

### Fluxo de processamento

```
1. Requisição (Upload de arquivo ou busca no Google Drive)
          │
2. Extração de texto por páginas (app/core/extractors/)
          │
3. Detecção de dados sensíveis pelo motor selecionado
          │
4. Geração do resultado:
   ├── JSON: texto substituído por [LABEL_ANONIMIZADO] + lista de entidades com página
   └── FILE: documento reconstruído in-place com tarjas (PDF vetorial, DOCX ou TXT)
```

---

## Benchmark e Avaliação de Desempenho

O projeto inclui um módulo de benchmark automatizado para avaliar a acurácia, precisão e qualidade dos motores de detecção contra gabaritos anotados (*ground truth*):

```bash
# Avaliar todos os motores com dataset padrão (benchmark/data)
poetry run python -m benchmark.run_benchmark

# Avaliar apenas motores específicos
poetry run python -m benchmark.run_benchmark --engines regex,spacy,hybrid

# Especificar diretório de dados e threshold de IoU
poetry run python -m benchmark.run_benchmark --data-dir benchmark/data --iou-threshold 0.5
```

Os artefatos gerados incluem Matriz de Confusão (`confusion_matrix_{engine}.png`), Classification Report em heatmap (`classification_report_{engine}.png`) e relatórios consolidados em JSON/TXT.

---

## Testes

O projeto possui **111 testes automatizados** cobrindo todas as camadas da aplicação:

```bash
# Executar toda a suíte de testes
poetry run pytest -v

# Executar testes de um módulo específico
poetry run pytest tests/test_engines.py -v         # Motores de detecção (33 testes)
poetry run pytest tests/test_api.py -v             # Endpoints HTTP da API (21 testes)
poetry run pytest tests/test_extractors.py -v      # Extratores de texto (16 testes)
poetry run pytest tests/test_benchmark.py -v       # Módulo de benchmark (15 testes)
poetry run pytest tests/test_builders.py -v        # Construtores de arquivo (11 testes)
poetry run pytest tests/test_google_drive.py -v    # Integração Google Drive (8 testes)
poetry run pytest tests/test_new_structure.py -v   # Configurações, Segurança e Rotas (7 testes)
```

### Cobertura da suíte

| Arquivo de Teste | Camada Coberta | Testes |
|---|---|---|
| `test_engines.py` | Padrões de Regex, SpacyNER, Presidio, Embedding e LegalNER | 33 |
| `test_api.py` | Rotas de upload, retorno JSON e download de arquivo, validação e erros | 21 |
| `test_extractors.py` | Extração página a página (PDF, DOCX, TXT) e tratamento de arquivos corrompidos | 16 |
| `test_benchmark.py` | IoU, alinhamento de spans, métricas de classificação e visualização | 15 |
| `test_builders.py` | Reconstrução in-place com tarjas (PDF, DOCX, TXT), paginação e estilos de tarja | 11 |
| `test_google_drive.py` | Clientes Google Drive (Mock e Real), exportação e tratamento de erros 404/502 | 8 |
| `test_new_structure.py` | Settings centrais, logger padronizado, models e handler global de exceções | 7 |
| **Total** | **Cobertura completa de ponta a ponta** | **111** |

---

## Estrutura do Projeto

```text
document_anonymizer/
├── app/
│   ├── core/
│   │   ├── builders/
│   │   │   └── file_builder.py          # Montagem de documentos tarjados (PDF, DOCX, TXT)
│   │   ├── configuration/
│   │   │   ├── __init__.py
│   │   │   ├── local_settings.py        # Configurações locais para desenvolvimento
│   │   │   └── settings.py              # Centralização de configs e leitura de .env
│   │   ├── engines/
│   │   │   ├── base.py                  # Interface base BaseEngine
│   │   │   ├── embedding_engine.py      # Motor semântico por embeddings
│   │   │   ├── hybrid_engine.py         # Motor híbrido com resolução de conflitos
│   │   │   ├── legal_ner_engine.py      # Motor de NER jurídico (LeNER-BR)
│   │   │   ├── presidio_engine.py       # Motor Microsoft Presidio
│   │   │   ├── regex_engine.py          # Motor de expressões regulares
│   │   │   └── spacy_engine.py          # Motor spaCy pt_core_news_lg
│   │   ├── extractors/
│   │   │   └── file_extractor.py        # Extração de texto bruto e por páginas
│   │   ├── integrations/
│   │   │   └── google_drive.py          # Cliente e Mock de integração com Google Drive
│   │   └── security/
│   │       ├── exceptions.py            # Exceções de domínio e handlers HTTP globais
│   │       ├── logger.py                # Setup e formatação padronizada de logs
│   │       └── __init__.py
│   ├── models/
│   │   ├── document.py                  # Entidades de domínio (EntityMatch, DocumentMetadata)
│   │   └── __init__.py
│   ├── schemas/
│   │   ├── anonymizer.py                # Schemas Pydantic de resposta da anonimização
│   │   ├── google_drive.py              # Schemas Pydantic para requisições do Google Drive
│   │   └── __init__.py
│   └── services/
│       ├── anonymization_service.py     # Orquestração do processo de anonimização
│       ├── utils.py                     # Funções utilitárias e headers de download
│       ├── views.py                     # Handlers / Controllers HTTP da API
│       └── __init__.py
├── benchmark/
│   ├── alignment.py                     # Cálculo de IoU e alinhamento de spans
│   ├── config.py                        # Configurações e mapeamento de categorias
│   ├── dataset.py                       # Carregamento de gabaritos e ground truth
│   ├── evaluator.py                     # Cálculo de métricas (Precision, Recall, F1)
│   ├── run_benchmark.py                 # Script CLI de execução do benchmark
│   └── visualizer.py                    # Geração de heatmaps e matrizes de confusão
├── tests/
│   ├── test_api.py                      # Testes dos endpoints HTTP da API
│   ├── test_benchmark.py                # Testes do módulo de benchmark
│   ├── test_builders.py                 # Testes dos construtores de arquivo
│   ├── test_engines.py                  # Testes dos motores de anonimização
│   ├── test_extractors.py               # Testes dos extratores de texto
│   ├── test_google_drive.py             # Testes da integração com Google Drive
│   ├── test_new_structure.py            # Testes da nova arquitetura e handlers
│   └── utils.py                         # Geradores de arquivos mock para testes
├── .env                                 # Variáveis de ambiente locais
├── .gitignore
├── conftest.py
├── poetry.lock
├── pyproject.toml
├── README.md
└── routes.py                            # Ponto de entrada oficial da aplicação FastAPI
```

---

## Licença

Este projeto é de uso interno. Consulte o autor para informações sobre licenciamento.