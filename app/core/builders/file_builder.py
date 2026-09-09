import io
from typing import List, Dict, Any
import docx
import pymupdf


def anonymize_docx_in_place(content: bytes, entities: List[Dict[str, Any]]) -> io.BytesIO:
    """Anonimiza um arquivo DOCX substituindo os termos por tarjas pretas (█)."""
    doc = docx.Document(io.BytesIO(content))

    # Substitui cada termo sensível por blocos pretos com a mesma quantidade de caracteres
    replacements = {e["text"]: "█" * len(e["text"]) for e in entities if e.get("text")}

    def _replace_in_paragraph(paragraph):
        for old_text, new_text in replacements.items():
            if old_text in paragraph.text:
                replaced = False
                for run in paragraph.runs:
                    if old_text in run.text:
                        run.text = run.text.replace(old_text, new_text)
                        replaced = True
                
                if not replaced:
                    paragraph.text = paragraph.text.replace(old_text, new_text)

    # 1. Parágrafos principais
    for p in doc.paragraphs:
        _replace_in_paragraph(p)

    # 2. Tabelas
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _replace_in_paragraph(p)

    # 3. Cabeçalhos e rodapés
    for section in doc.sections:
        for p in section.header.paragraphs:
            _replace_in_paragraph(p)
        for p in section.footer.paragraphs:
            _replace_in_paragraph(p)

    out_stream = io.BytesIO()
    doc.save(out_stream)
    out_stream.seek(0)
    return out_stream


def anonymize_pdf_in_place(content: bytes, entities: List[Dict[str, Any]]) -> io.BytesIO:
    """Anonimiza um PDF desenhando faixas pretas sólidas sobre as coordenadas do texto sensível."""
    pdf_doc = pymupdf.open(stream=content, filetype="pdf")

    sensitive_terms = {e["text"] for e in entities if e.get("text") and e["text"].strip()}
    sorted_terms = sorted(sensitive_terms, key=len, reverse=True)

    for page in pdf_doc:
        for term in sorted_terms:
            rects = page.search_for(term)
            for rect in rects:
                # Desenha a tarja preta vetorial (RGB 0,0,0) e remove o texto original
                page.add_redact_annot(
                    rect,
                    fill=(0, 0, 0)
                )
        page.apply_redactions()

    out_stream = io.BytesIO()
    pdf_doc.save(out_stream, garbage=4, deflate=True)
    out_stream.seek(0)
    return out_stream


def build_anonymized_file(filename: str, original_content: bytes, entities: List[Dict[str, Any]]) -> tuple[io.BytesIO, str]:
    """Direciona o arquivo para o construtor correto aplicando tarjas pretas."""
    ext = filename.split(".")[-1].lower()

    if ext == "txt":
        text = original_content.decode("utf-8")
        for e in sorted(entities, key=lambda x: len(x.get("text", "")), reverse=True):
            if e.get("text"):
                text = text.replace(e["text"], "█" * len(e["text"]))
        return io.BytesIO(text.encode("utf-8")), "text/plain"

    if ext in ["doc", "docx"]:
        return (
            anonymize_docx_in_place(original_content, entities),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    if ext == "pdf":
        return anonymize_pdf_in_place(original_content, entities), "application/pdf"

    raise ValueError(f"Extensão não suportada para reconstrução: {ext}")