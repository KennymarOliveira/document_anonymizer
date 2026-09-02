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


# --- Testes dos novos padrões do RegexEngine ---


def test_regex_engine_processo_cnj():
    """Detecta número de processo no padrão CNJ."""
    engine = RegexEngine()
    text = "Processo nº: 0001234-56.2020.8.13.0034 em tramitação"
    anonymized, entities = engine.anonymize(text)

    assert "[PROCESSO_ANONIMIZADO]" in anonymized
    assert "0001234-56.2020.8.13.0034" not in anonymized
    assert entities[0]["label"] == "PROCESSO"
    assert entities[0]["text"] == "0001234-56.2020.8.13.0034"


def test_regex_engine_oab():
    """Detecta registro da OAB."""
    engine = RegexEngine()
    text = "Advogado inscrito na OAB/MG 123456"
    anonymized, entities = engine.anonymize(text)

    assert "[OAB_ANONIMIZADO]" in anonymized
    assert len(entities) == 1
    assert entities[0]["label"] == "OAB"


def test_regex_engine_placa_veiculo():
    """Detecta placas de veículos no padrão antigo e Mercosul."""
    engine = RegexEngine()
    # Padrão antigo
    text1 = "Veículo de placa ABC1234 foi apreendido"
    _, ent1 = engine.anonymize(text1)
    assert len(ent1) == 1
    assert ent1[0]["label"] == "PLACA"

    # Padrão Mercosul
    text2 = "Placa ABC1D23 registrada"
    _, ent2 = engine.anonymize(text2)
    assert len(ent2) == 1
    assert ent2[0]["label"] == "PLACA"


def test_regex_engine_cep():
    """Detecta CEP com e sem hífen."""
    engine = RegexEngine()
    text = "Endereço no CEP 30130-000"
    anonymized, entities = engine.anonymize(text)

    assert "[CEP_ANONIMIZADO]" in anonymized
    assert entities[0]["label"] == "CEP"

    # Sem hífen
    text2 = "CEP 30130000"
    _, ent2 = engine.anonymize(text2)
    assert len(ent2) == 1
    assert ent2[0]["label"] == "CEP"


def test_regex_engine_mandado_prisao():
    """Detecta número de mandado de prisão no padrão BNMP."""
    engine = RegexEngine()
    text = "Mandado 1234567-89.2020.8.13.0000.01.0001-00 expedido"
    anonymized, entities = engine.anonymize(text)

    assert "[MANDADO_ANONIMIZADO]" in anonymized
    assert entities[0]["label"] == "MANDADO"


def test_regex_engine_boletim_ocorrencia():
    """Detecta IP, B.O. e APF."""
    engine = RegexEngine()
    # Inquérito Policial
    text_ip = "conforme IP 123/2023 da delegacia"
    _, ent_ip = engine.anonymize(text_ip)
    assert len(ent_ip) == 1
    assert ent_ip[0]["label"] == "BOLETIM_OCORRENCIA"

    # Auto de Prisão em Flagrante
    text_apf = "lavrado APF 45/2021"
    _, ent_apf = engine.anonymize(text_apf)
    assert len(ent_apf) == 1
    assert ent_apf[0]["label"] == "BOLETIM_OCORRENCIA"


def test_regex_engine_rg():
    """Detecta número de RG."""
    engine = RegexEngine()
    text = "portador do RG 12.345.678-9"
    anonymized, entities = engine.anonymize(text)

    assert "[RG_ANONIMIZADO]" in anonymized
    assert entities[0]["label"] == "RG"


def test_regex_engine_cnh():
    """Detecta número de CNH."""
    engine = RegexEngine()
    text = "habilitação CNH 12345678901"
    anonymized, entities = engine.anonymize(text)

    assert "[CNH_ANONIMIZADO]" in anonymized
    assert entities[0]["label"] == "CNH"


def test_regex_engine_authority():
    """Detecta título + nome de autoridades."""
    engine = RegexEngine()
    text = "decisão proferida pelo Juiz Carlos Eduardo da Silva"
    anonymized, entities = engine.anonymize(text)

    assert "[AUTHORITY_ANONIMIZADO]" in anonymized
    assert "Carlos" not in anonymized
    assert entities[0]["label"] == "AUTHORITY"


def test_regex_engine_authority_desembargador():
    """Detecta Desembargador como autoridade."""
    engine = RegexEngine()
    text = "Relatora Desembargador Maria Helena Souza"
    anonymized, entities = engine.anonymize(text)

    assert "[AUTHORITY_ANONIMIZADO]" in anonymized
    assert "Maria" not in anonymized


def test_regex_engine_codigo_autenticacao():
    """Detecta códigos hexadecimais de autenticação de documentos."""
    engine = RegexEngine()
    text = "sob o código C019-B4CF-AAEF-E58A e senha 961D-A3BE-207E-ED02"
    anonymized, entities = engine.anonymize(text)

    assert anonymized.count("[CODIGO_AUTENTICACAO_ANONIMIZADO]") == 2
    assert "C019-B4CF-AAEF-E58A" not in anonymized
    assert "961D-A3BE-207E-ED02" not in anonymized
    assert len(entities) == 2
    assert all(e["label"] == "CODIGO_AUTENTICACAO" for e in entities)


def test_regex_engine_medida_provisoria():
    """Detecta referência a Medida Provisória."""
    engine = RegexEngine()
    text = "Documento assinado digitalmente conforme MP n° 2.200-2/2001 de 24/08/2001"
    anonymized, entities = engine.anonymize(text)

    assert "[MEDIDA_PROVISORIA_ANONIMIZADO]" in anonymized
    assert "MP n° 2.200-2/2001" not in anonymized
    assert entities[0]["label"] == "MEDIDA_PROVISORIA"


class _FakeEngine(BaseEngine):
    """Motor de teste que troca um termo fixo, sem carregar modelos."""

    def __init__(self, alvo: str, label: str) -> None:
        self.alvo = alvo
        self.label = label

    def detect(self, text: str) -> List[Dict[str, Any]]:
        import re
        entities = []
        for match in re.finditer(re.escape(self.alvo), text):
            entities.append({
                "start": match.start(),
                "end": match.end(),
                "text": match.group(),
                "label": self.label,
                "engine": "Fake"
            })
        return entities

    def anonymize(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        if self.alvo not in text:
            return text, []

        entities = self.detect(text)
        return text.replace(self.alvo, f"[{self.label}_ANONIMIZADO]"), entities


def test_hybrid_engine_encadeia_motores_e_acumula_entidades():
    """HybridEngine deve acionar todos os motores e acumular os resultados."""
    engine = HybridEngine([_FakeEngine("João", "PER"), _FakeEngine("Recife", "LOC")])
    anonymized, entities = engine.anonymize("João mora em Recife")

    assert anonymized == "[PER_ANONIMIZADO] mora em [LOC_ANONIMIZADO]"
    assert [e["label"] for e in entities] == ["PER", "LOC"]

def test_hybrid_engine_resolve_conflitos():
    """Motores diferentes que identificam áreas sobrepostas devem ser resolvidos 
    pelo HybridEngine mantendo a maior correspondência."""
    # O primeiro motor acha 'São Paulo' e o segundo acha só 'Paulo'
    engine = HybridEngine([_FakeEngine("São Paulo", "LOC"), _FakeEngine("Paulo", "PER")])
    anonymized, entities = engine.anonymize("Viagem para São Paulo")

    # A entidade mais longa ganha
    assert anonymized == "Viagem para [LOC_ANONIMIZADO]"
    assert len(entities) == 1
    assert entities[0]["label"] == "LOC"
