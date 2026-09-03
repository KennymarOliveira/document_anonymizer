"""Configurações e constantes do módulo de benchmark."""

from typing import Dict, Any

# Mapeamento de normalização de labels dos diferentes motores
LABEL_NORMALIZATION: Dict[str, str] = {
    # spaCy -> Normalizado
    "PER": "PESSOA",
    "LOC": "LOCAL",
    "ORG": "ORGANIZACAO",

    # Microsoft Presidio -> Normalizado
    "PERSON": "PESSOA",
    "LOCATION": "LOCAL",
    "ORGANIZATION": "ORGANIZACAO",
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "TELEFONE",
    "CREDIT_CARD": "CARTAO_CREDITO",
    "DATE_TIME": "DATA",
    "IP_ADDRESS": "IP",
    "URL": "URL",
    "IBAN_CODE": "IBAN",
    "NRP": "NRP",

    # RegexEngine -> Normalizado
    "CPF": "CPF",
    "CNPJ": "CNPJ",
    "EMAIL": "EMAIL",
    "PROCESSO": "PROCESSO",
    "OAB": "OAB",
    "PLACA": "PLACA",
    "CEP": "CEP",
    "MANDADO": "MANDADO",
    "BOLETIM_OCORRENCIA": "BOLETIM_OCORRENCIA",
    "RG": "RG",
    "CNH": "CNH",
    "AUTHORITY": "AUTORIDADE",
    "CODIGO_AUTENTICACAO": "COD_AUTENTICACAO",
    "MEDIDA_PROVISORIA": "MEDIDA_PROVISORIA",

    # EmbeddingEngine
    "SEMANTIC_SENSITIVE": "SEMANTICO",

    # Genérico para quando a anotação vem de diferença entre PDFs
    "SENSITIVE": "SENSITIVE",
}


def normalize_label(label: str) -> str:
    """Normaliza o label de uma entidade para a taxonomia padrão."""
    if not label:
        return "DESCONHECIDO"
    normalized = LABEL_NORMALIZATION.get(label.upper(), label.upper())
    return normalized


# Lista de engines suportadas no benchmark
SUPPORTED_ENGINES = ["regex", "spacy", "embedding", "presidio", "hybrid"]

# Threshold padrão de Intersection over Union (IoU) para matching de spans
DEFAULT_IOU_THRESHOLD = 0.5

# Configurações visuais dos gráficos gerados
VISUAL_CONFIG: Dict[str, Any] = {
    "confusion_matrix": {
        "cmap": "Blues",
        "title_suffix": "Confusion Matrix",
        "figsize": (9, 8),
        "font_size_values": 13,
        "font_size_labels": 11,
        "title_font_size": 14,
    },
    "classification_report": {
        "cmap": "YlGnBu",
        "title_suffix": "Classification Report",
        "figsize": (9, 8),
        "font_size_values": 13,
        "font_size_labels": 11,
        "title_font_size": 14,
        "value_format": ".3f",
    },
    "comparison": {
        "figsize": (10, 6),
        "palette": ["#1f77b4", "#2ca02c", "#ff7f0e"],
    }
}
