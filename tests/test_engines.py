import re
from typing import Any, Dict, List

from app.core.engines.base import BaseEngine
from app.core.engines.hybrid_engine import HybridEngine
from app.core.engines.regex_engine import RegexEngine


def test_regex_engine_cpf():
    engine = RegexEngine()
    text = "O CPF do cliente é 123.456.789-00."
    anonymized, entities = engine.anonymize(text)

    assert "[CPF_ANONIMIZADO]" in anonymized
    assert len(entities) == 1
    assert entities[0]["label"] == "CPF"
    assert entities[0]["text"] == "123.456.789-00"


def test_regex_engine_cpf_sem_pontuacao():
    anonymized, entities = RegexEngine().anonymize("CPF 12345678900 do autor")

    assert anonymized == "CPF [CPF_ANONIMIZADO] do autor"
    assert [e["label"] for e in entities] == ["CPF"]


def test_regex_engine_ignora_digitos_dentro_de_numero_maior():
    """Um número de processo de 20 dígitos não deve ser confundido com CPF."""
    engine = RegexEngine()
    text = "Processo 12345678901234567890 em tramitação"
    anonymized, entities = engine.anonymize(text)

    assert anonymized == text
    assert entities == []


def test_regex_engine_cnpj_nao_casa_como_cpf():
    """Os 11 primeiros dígitos de um CNPJ não devem virar um CPF."""
    engine = RegexEngine()
    anonymized, entities = engine.anonymize("CNPJ 12345678000199 da ré")

    assert anonymized == "CNPJ [CNPJ_ANONIMIZADO] da ré"
    assert [e["label"] for e in entities] == ["CNPJ"]


def test_regex_engine_ocorrencias_repetidas_geram_entidades_separadas():
    """Cada ocorrência é substituída e contabilizada individualmente."""
    engine = RegexEngine()
    text = "CPF 111.222.333-44 e novamente 111.222.333-44"
    anonymized, entities = engine.anonymize(text)

    assert anonymized == "CPF [CPF_ANONIMIZADO] e novamente [CPF_ANONIMIZADO]"
    assert len(entities) == 2
    assert all(e["text"] == "111.222.333-44" for e in entities)


def test_regex_engine_match_contido_em_outro_mantem_o_mais_longo():
    """Regressão: com a substituição global, o CPF dentro do e-mail era trocado
    primeiro e o domínio ficava exposto — a entidade EMAIL era reportada mas
    nunca chegava a ser aplicada ao texto."""
    anonymized, entities = RegexEngine().anonymize("Contato 12345678901@exemplo.com aqui")

    assert anonymized == "Contato [EMAIL_ANONIMIZADO] aqui"
    assert "exemplo.com" not in anonymized
    assert [e["label"] for e in entities] == ["EMAIL"]


def test_regex_engine_nao_deixa_fragmento_sensivel_no_texto():
    """Nada de cada entidade pode sobrar no texto — nem a entidade inteira nem
    um fragmento dela, como o domínio de um e-mail parcialmente substituído."""
    text = "CPF 12345678901, email 98765432109@ex.com, CNPJ 12.345.678/0001-99"
    anonymized, entities = RegexEngine().anonymize(text)

    for entidade in entities:
        assert entidade["text"] not in anonymized

    assert "@" not in anonymized
    assert "ex.com" not in anonymized
    assert not re.search(r"\d{11}", anonymized)


def test_regex_engine_email():
    engine = RegexEngine()
    anonymized, entities = engine.anonymize("Contato: joao.silva+adv@exemplo.com.br")

    assert anonymized == "Contato: [EMAIL_ANONIMIZADO]"
    assert entities[0]["label"] == "EMAIL"
    assert entities[0]["text"] == "joao.silva+adv@exemplo.com.br"


def test_regex_engine_entidades_em_ordem_de_aparicao():
    engine = RegexEngine()
    text = "Email x@y.com, CNPJ 11.222.333/0001-44, CPF 555.666.777-88"
    anonymized, entities = engine.anonymize(text)

    assert [e["label"] for e in entities] == ["EMAIL", "CNPJ", "CPF"]
    assert anonymized == (
        "Email [EMAIL_ANONIMIZADO], CNPJ [CNPJ_ANONIMIZADO], CPF [CPF_ANONIMIZADO]"
    )


def test_regex_engine_marca_o_motor_de_origem():
    engine = RegexEngine()
    _, entities = engine.anonymize("CPF 123.456.789-00")

    assert entities[0]["engine"] == "Regex"


def test_regex_engine_texto_sem_dados_sensiveis():
    engine = RegexEngine()
    text = "Petição inicial sem dados pessoais."

    assert engine.anonymize(text) == (text, [])


class _FakeEngine(BaseEngine):
    """Motor de teste que troca um termo fixo, sem carregar modelos."""

    def __init__(self, alvo: str, label: str) -> None:
        self.alvo = alvo
        self.label = label

    def anonymize(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        if self.alvo not in text:
            return text, []

        entities = [{"text": self.alvo, "label": self.label, "engine": "Fake"}]
        return text.replace(self.alvo, f"[{self.label}_ANONIMIZADO]"), entities


def test_hybrid_engine_encadeia_motores_e_acumula_entidades():
    engine = HybridEngine([_FakeEngine("João", "PER"), _FakeEngine("Recife", "LOC")])
    anonymized, entities = engine.anonymize("João mora em Recife")

    assert anonymized == "[PER_ANONIMIZADO] mora em [LOC_ANONIMIZADO]"
    assert [e["label"] for e in entities] == ["PER", "LOC"]


def test_hybrid_engine_recebe_texto_ja_anonimizado_do_anterior():
    """O segundo motor opera sobre a saída do primeiro, não sobre o original."""
    engine = HybridEngine([RegexEngine(), _FakeEngine("[CPF_ANONIMIZADO]", "SEGUNDO")])
    anonymized, entities = engine.anonymize("CPF 123.456.789-00")

    assert anonymized == "CPF [SEGUNDO_ANONIMIZADO]"
    assert [e["label"] for e in entities] == ["CPF", "SEGUNDO"]
