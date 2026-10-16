# Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Instala ferramentas necessárias para compilar dependências com extensões nativas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cria ambiente virtual isolado
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instalação das dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download do modelo de língua portuguesa do spaCy
RUN python -m spacy download pt_core_news_lg

# Argumento para controle de pré-carregamento dos modelos de Deep Learning
ARG PRELOAD_MODELS=true
ENV HF_HOME=/opt/hf_cache

# Executa pré-download dos modelos Hugging Face (Sentence Transformers e LeNER-BR)
COPY scripts/download_models.py ./scripts/
RUN if [ "$PRELOAD_MODELS" = "true" ]; then \
        python ./scripts/download_models.py; \
    else \
        mkdir -p /opt/hf_cache; \
    fi


# Runner
FROM python:3.11-slim AS runner

# Criação de usuário não-privilegiado para segurança
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -d /app -s /bin/bash appuser

# Diretório da aplicação
WORKDIR /app

# Variáveis de ambiente
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME="/app/.cache/huggingface" \
    PORT=8000 \
    WORKERS=1 \
    LOG_LEVEL=INFO \
    USE_GOOGLE_DRIVE_MOCK=true

# Copia ambiente virtual construído no estágio builder
COPY --from=builder /opt/venv /opt/venv

# Cria diretórios de cache e copia modelos pré-carregados
RUN mkdir -p /app/.cache/huggingface && chown -R appuser:appuser /app
COPY --from=builder --chown=appuser:appuser /opt/hf_cache /app/.cache/huggingface

# Copia código-fonte da aplicação
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser routes.py .

# Health Check nativo usando a biblioteca padrão do Python (dispensa instalação de curl)
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request, os; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", 8000)}/health')" || exit 1

# Altera para usuário não-root
USER appuser

# Porta exposta pelo microsserviço
EXPOSE 8000

# Execução do Uvicorn com suporte a variáveis de ambiente e encerramento gracioso via exec
CMD ["sh", "-c", "exec uvicorn routes:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-1} --timeout-keep-alive 60"]

