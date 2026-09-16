from collections import defaultdict
import io
from typing import Any, Dict, List
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
    """Anonimiza um PDF desenhando faixas pretas sólidas sobre as coordenadas do texto sensível de forma otimizada."""
    pdf_doc = pymupdf.open(stream=content, filetype="pdf")

    # Mapeamento de termos sensíveis por página e termos globais
    page_terms_map: Dict[int, set[str]] = defaultdict(set)
    global_terms: set[str] = set()

    for e in entities:
        text = e.get("text", "").strip()
        if not text:
            continue
        page_num = e.get("page")
        if page_num is not None:
            page_terms_map[page_num].add(text)
        else:
            global_terms.add(text)

    def _redact_page(page_idx: int) -> None:
        page = pdf_doc[page_idx]
        page_num = page_idx + 1
        terms_for_page = page_terms_map.get(page_num, set()) | global_terms
        if not terms_for_page:
            return

        single_word_terms = {t for t in terms_for_page if " " not in t}
        multi_word_terms = sorted([t for t in terms_for_page if " " in t], key=len, reverse=True)

        unmatched_single = set(single_word_terms)

        # Otimização 2: Extração em passada única nas palavras da página
        if single_word_terms:
            single_terms_lower = {t.lower(): t for t in single_word_terms}
            matched_single = set()

            for w in page.get_text("words"):
                raw_l = w[4].lower()
                clean_l = raw_l.strip(".,;:()[]{}\\'\"")
                if raw_l in single_terms_lower:
                    page.add_redact_annot(pymupdf.Rect(w[:4]), fill=(0, 0, 0))
                    matched_single.add(single_terms_lower[raw_l])
                elif clean_l in single_terms_lower:
                    page.add_redact_annot(pymupdf.Rect(w[:4]), fill=(0, 0, 0))
                    matched_single.add(single_terms_lower[clean_l])

            unmatched_single = set(single_word_terms) - matched_single
        else:
            unmatched_single = set()

        # Expressões compostas ou termos isolados com formatação especial
        terms_to_search = multi_word_terms + list(unmatched_single)
        for term in terms_to_search:
            for rect in page.search_for(term):
                page.add_redact_annot(rect, fill=(0, 0, 0))

        page.apply_redactions()

    num_pages = len(pdf_doc)
    # Processamento sequencial por página (PyMuPDF muta xref/fontes em C de forma thread-unsafe)
    for idx in range(num_pages):
        _redact_page(idx)

    out_stream = io.BytesIO()
    # Otimização 4: Salvamento com garbage=1 e deflate=True (muito mais rápido que garbage=4)
    pdf_doc.save(out_stream, garbage=1, deflate=True)
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