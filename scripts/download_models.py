"""Script para pré-download dos modelos de NLP durante o build do Docker."""
import os
import sys

def download_models():
    print(">>> Iniciando download prévio dos modelos de NLP...")

    # 1. Sentence Transformers
    print("-> Baixando modelo SentenceTransformer ('paraphrase-multilingual-MiniLM-L12-v2')...")
    from sentence_transformers import SentenceTransformer
    SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    # 2. Hugging Face Transformers (LeNER-BR)
    print("-> Baixando modelo LeNER-BR ('pierreguillou/ner-bert-base-cased-pt-lenerbr')...")
    from transformers import AutoModelForTokenClassification, AutoTokenizer
    model_id = "pierreguillou/ner-bert-base-cased-pt-lenerbr"
    AutoTokenizer.from_pretrained(model_id, model_max_length=512)
    AutoModelForTokenClassification.from_pretrained(model_id)

    print(">>> Todos os modelos foram baixados e cacheados com sucesso!")

if __name__ == "__main__":
    download_models()

