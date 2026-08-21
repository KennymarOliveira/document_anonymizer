from app.core.engines.regex_engine import RegexEngine

def test_regex_engine_cpf():
    engine = RegexEngine()
    text = "O CPF do cliente é 123.456.789-00."
    anonymized, entities = engine.anonymize(text)
    
    assert "[CPF_ANONIMIZADO]" in anonymized
    assert len(entities) == 1
    assert entities[0]["label"] == "CPF"
    assert entities[0]["text"] == "123.456.789-00"