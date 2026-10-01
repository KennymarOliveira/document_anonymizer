from collections import defaultdict
import io
from typing import Any, Dict, List, Literal

import docx
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import RGBColor
import pymupdf

REDACTION_MODE_BLACKOUT = "blackout"
REDACTION_MODE_BLACK_WHITE_TEXT = "black_white_text"

RedactionMode = Literal[
    "blackout",
    "black_white_text",
    "tarja_preta",
    "tarja_texto_branco",
]


def normalize_redaction_mode(mode: str | None) -> str:
    """Normaliza o modo de tarja para os tipos canônicos."""
    if not mode:
        return REDACTION_MODE_BLACKOUT
    m = mode.strip().lower()
    blackout_aliases = [
        "blackout",
        "tarja_preta",
        "solid",
        "black",
        "preto",
        "padrao",
        "default",
    ]
    if m in blackout_aliases:
        return REDACTION_MODE_BLACKOUT
    white_text_aliases = [
        "black_white_text",
        "texto_branco",
        "tarja_texto_branco",
        "black_bg_white_text",
        "white_on_black",
        "white_text",
        "tarja_com_texto",
    ]
    if m in white_text_aliases:
        return REDACTION_MODE_BLACK_WHITE_TEXT
    raise ValueError(
        f"Modo de tarja '{mode}' não suportado. Opções válidas: "
        "'blackout' (tarja preta sólida) ou "
        "'black_white_text' (tarja preta de fundo com texto branco)."
    )


def _style_run_black_white_text(run: Any) -> None:
    """Aplica formatação de texto branco com fundo preto em um run."""
    run.font.color.rgb = RGBColor(255, 255, 255)
    ns = nsdecls("w")
    shd = parse_xml(f'<w:shd {ns} w:fill="000000"/>')
    run._r.get_or_add_rPr().append(shd)


def _is_run_styled_white_on_black(run: Any) -> bool:
    """Verifica se o run já está com a cor branca configurada."""
    return (
        run.font.color is not None
        and getattr(run.font.color, "rgb", None) == RGBColor(255, 255, 255)
    )


def _apply_black_white_to_paragraph(paragraph: Any, targets: List[str]) -> None:
    """Divide os runs do parágrafo aplicando fundo preto e texto branco."""
    for target in targets:
        if not target or target not in paragraph.text:
            continue

        # Consolida runs se o termo estiver quebrado entre runs sem estilo
        has_unstyled = any(
            target in r.text
            for r in paragraph.runs
            if not _is_run_styled_white_on_black(r)
        )
        if not has_unstyled:
            styled_runs = [
                r for r in paragraph.runs if _is_run_styled_white_on_black(r)
            ]
            if not styled_runs:
                paragraph.text = paragraph.text

        runs = list(paragraph.runs)
        for r in runs:
            if _is_run_styled_white_on_black(r):
                continue
            if target in r.text:
                parts = r.text.split(target)
                r.text = parts[0]
                cur_r = r
                for i in range(1, len(parts)):
                    new_run = paragraph.add_run(target)
                    _style_run_black_white_text(new_run)
                    cur_r._r.addnext(new_run._r)
                    cur_r = new_run
                    if parts[i]:
                        after_run = paragraph.add_run(parts[i])
                        cur_r._r.addnext(after_run._r)
                        cur_r = after_run

                if not r.text and r._r.getparent() is not None:
                    r._r.getparent().remove(r._r)


def anonymize_docx_in_place(
    content: bytes,
    entities: List[Dict[str, Any]],
    redaction_mode: str = "blackout",
) -> io.BytesIO:
    """Anonimiza um DOCX com tarjas sólidas ou texto em contraste."""
    mode = normalize_redaction_mode(redaction_mode)
    doc = docx.Document(io.BytesIO(content))

    if mode == REDACTION_MODE_BLACKOUT:
        replacements = {
            e["text"]: "█" * len(e["text"])
            for e in entities
            if e.get("text")
        }

        def _replace_in_paragraph(paragraph):
            for old_text, new_text in replacements.items():
                if old_text in paragraph.text:
                    replaced = False
                    for run in paragraph.runs:
                        if old_text in run.text:
                            run.text = run.text.replace(old_text, new_text)
                            replaced = True

                    if not replaced:
                        paragraph.text = paragraph.text.replace(
                            old_text, new_text
                        )

        process_p = _replace_in_paragraph
    else:
        targets = sorted(
            {
                e["text"]
                for e in entities
                if e.get("text") and e["text"].strip()
            },
            key=len,
            reverse=True,
        )

        def _replace_in_paragraph(paragraph):
            _apply_black_white_to_paragraph(paragraph, targets)

        process_p = _replace_in_paragraph

    for p in doc.paragraphs:
        process_p(p)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    process_p(p)

    for section in doc.sections:
        for p in section.header.paragraphs:
            process_p(p)
        for p in section.footer.paragraphs:
            process_p(p)

    out_stream = io.BytesIO()
    doc.save(out_stream)
    out_stream.seek(0)
    return out_stream


def anonymize_pdf_in_place(
    content: bytes,
    entities: List[Dict[str, Any]],
    redaction_mode: str = "blackout",
) -> io.BytesIO:
    """Anonimiza um PDF com faixas pretas ou fundo preto + texto branco."""
    mode = normalize_redaction_mode(redaction_mode)
    pdf_doc = pymupdf.open(stream=content, filetype="pdf")

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
        multi_word_terms = sorted(
            [t for t in terms_for_page if " " in t], key=len, reverse=True
        )

        unmatched_single = set(single_word_terms)

        if single_word_terms:
            single_terms_lower = {t.lower(): t for t in single_word_terms}
            matched_single = set()

            for w in page.get_text("words"):
                raw_l = w[4].lower()
                clean_l = raw_l.strip(".,;:()[]{}\\'\"")
                matched_term = None
                if raw_l in single_terms_lower:
                    matched_term = single_terms_lower[raw_l]
                elif clean_l in single_terms_lower:
                    matched_term = single_terms_lower[clean_l]

                if matched_term:
                    rect = pymupdf.Rect(w[:4])
                    if mode == REDACTION_MODE_BLACK_WHITE_TEXT:
                        page.add_redact_annot(
                            rect,
                            text=w[4],
                            fill=(0, 0, 0),
                            text_color=(1, 1, 1),
                            align=pymupdf.TEXT_ALIGN_CENTER,
                        )
                    else:
                        page.add_redact_annot(rect, fill=(0, 0, 0))
                    matched_single.add(matched_term)

            unmatched_single = set(single_word_terms) - matched_single
        else:
            unmatched_single = set()

        terms_to_search = multi_word_terms + list(unmatched_single)
        for term in terms_to_search:
            for rect in page.search_for(term):
                if mode == REDACTION_MODE_BLACK_WHITE_TEXT:
                    clip_txt = (
                        page.get_text("text", clip=rect).strip() or term
                    )
                    page.add_redact_annot(
                        rect,
                        text=clip_txt,
                        fill=(0, 0, 0),
                        text_color=(1, 1, 1),
                        align=pymupdf.TEXT_ALIGN_CENTER,
                    )
                else:
                    page.add_redact_annot(rect, fill=(0, 0, 0))

        page.apply_redactions()

    num_pages = len(pdf_doc)
    for idx in range(num_pages):
        _redact_page(idx)

    out_stream = io.BytesIO()
    pdf_doc.save(out_stream, garbage=1, deflate=True)
    out_stream.seek(0)
    return out_stream


def build_anonymized_file(
    filename: str,
    original_content: bytes,
    entities: List[Dict[str, Any]],
    redaction_mode: str = "blackout",
) -> tuple[io.BytesIO, str]:
    """Direciona o arquivo para o construtor aplicando o modo de tarja."""
    mode = normalize_redaction_mode(redaction_mode)
    ext = filename.split(".")[-1].lower()

    if ext == "txt":
        text = original_content.decode("utf-8")
        entities_sorted = sorted(
            entities, key=lambda x: len(x.get("text", "")), reverse=True
        )
        for e in entities_sorted:
            val = e.get("text")
            if val:
                if mode == REDACTION_MODE_BLACK_WHITE_TEXT:
                    replacement = f"\033[40;97m{val}\033[0m"
                else:
                    replacement = "█" * len(val)
                text = text.replace(val, replacement)
        return io.BytesIO(text.encode("utf-8")), "text/plain"

    if ext in ["doc", "docx"]:
        mime_type = (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )
        return (
            anonymize_docx_in_place(
                original_content, entities, redaction_mode=mode
            ),
            mime_type,
        )

    if ext == "pdf":
        return (
            anonymize_pdf_in_place(
                original_content, entities, redaction_mode=mode
            ),
            "application/pdf",
        )

    raise ValueError(f"Extensão não suportada para reconstrução: {ext}")
    raise ValueError(f"Extensão não suportada para reconstrução: {ext}")