import pytest

from app.core.builders.file_builder import build_docx, build_file, build_pdf, build_txt
from app.core.extractors.file_extractor import extract_text

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def texto_do_pdf(texto: str) -> str:
    """Monta um PDF e devolve o texto extraído de volta."""
    return extract_text("saida.pdf", build_pdf(texto).getvalue())


def test_build_txt():
    assert build_txt("ação").getvalue() == "ação".encode("utf-8")


def test_build_docx_preserva_linhas_e_acentos():
    conteudo = build_docx("Primeira ação\nSegunda linha").getvalue()
    assert extract_text("saida.docx", conteudo) == "Primeira ação\nSegunda linha"


def test_build_pdf_com_multiplas_linhas():
    """Regressão: o multi_cell deixava o cursor na margem direita, e a segunda
    linha falhava com FPDFException por falta de espaço horizontal."""
    resultado = texto_do_pdf("Linha um\nLinha dois\nLinha tres")

    for linha in ("Linha um", "Linha dois", "Linha tres"):
        assert linha in resultado


def test_build_pdf_preserva_acentos_do_portugues():
    resultado = texto_do_pdf("José da Conceição, ação, coração, Água, Índio")

    for palavra in ("José", "Conceição", "ação", "coração", "Água", "Índio"):
        assert palavra in resultado


def test_build_pdf_preserva_simbolos_juridicos():
    resultado = texto_do_pdf("art. 5º, § 1°, 2ª Vara, «citado», © 2026")

    for simbolo in ("5º", "§", "1°", "2ª", "«citado»", "©"):
        assert simbolo in resultado


def test_build_pdf_palavra_longa_nao_recebe_espacos_injetados():
    """Regressão: o workaround antigo inseria um espaço a cada 60 caracteres,
    corrompendo números e palavras longas. A quebra é do multi_cell agora."""
    resultado = texto_do_pdf("inicio\n" + "X" * 300 + "\nfim")

    assert resultado.count("X") == 300
    assert "X X" not in resultado
    assert "inicio" in resultado and "fim" in resultado


def test_build_pdf_numero_longo_permanece_contiguo():
    resultado = texto_do_pdf("Processo 12345678901234567890")
    assert "12345678901234567890" in resultado


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("“contrato”", '"contrato"'),
        ("‘clausula’", "'clausula'"),
        ("travessao — aqui", "travessao - aqui"),
        ("meia-risca – aqui", "meia-risca - aqui"),
        ("reticencias…", "reticencias..."),
        ("marcador • item", "marcador - item"),
        ("marca™", "marca(TM)"),
        ("№ 42", "No. 42"),
        ("€ 100", "EUR 100"),
        ("1⁄2", "1/2"),
        ("‹citado›", "<citado>"),
    ],
)
def test_build_pdf_mapeia_pontuacao_tipografica(entrada, esperado):
    resultado = texto_do_pdf(entrada)

    assert esperado in resultado
    assert "?" not in resultado


def test_build_pdf_remove_caracteres_de_largura_zero():
    resultado = texto_do_pdf("aqui​e‍ali﻿")

    assert "aquieali" in resultado
    assert "?" not in resultado


def test_build_pdf_normaliza_espacos_especiais():
    resultado = texto_do_pdf("nbsp aqui e ali")

    assert "nbsp aqui e ali" in resultado
    assert "?" not in resultado


def test_build_pdf_linhas_vazias_nao_quebram():
    resultado = texto_do_pdf("antes\n\n\ndepois")

    assert "antes" in resultado
    assert "depois" in resultado


def test_build_pdf_texto_vazio():
    assert build_pdf("").getvalue().startswith(b"%PDF")


def test_build_pdf_converte_tabulacao():
    assert "coluna    valor" in texto_do_pdf("coluna\tvalor")


@pytest.mark.parametrize(
    "filename, media_type",
    [
        ("doc.txt", "text/plain"),
        ("doc.docx", DOCX_MEDIA_TYPE),
        ("doc.doc", DOCX_MEDIA_TYPE),
        ("doc.pdf", "application/pdf"),
        ("DOC.PDF", "application/pdf"),
    ],
)
def test_build_file_media_types(filename, media_type):
    stream, resultado = build_file(filename, "conteúdo")

    assert resultado == media_type
    assert stream.getvalue()


def test_build_file_extensao_nao_suportada():
    with pytest.raises(ValueError, match="Extensão não suportada"):
        build_file("doc.csv", "1,2,3")
