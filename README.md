# Document Anonymizer

API para extração e anonimização de dados sensíveis em documentos jurídicos (PDF, DOCX, TXT) utilizando Regex, spaCy (NER) e Embeddings.

## Setup

```bash
poetry install
poetry run python -m spacy download pt_core_news_lg
```

## Run
```bash
poetry run uvicorn app.main:app --reload
```