import re
from typing import List, Dict, Any
from app.core.engines.base import BaseEngine

class RegexEngine(BaseEngine):
    def __init__(self) -> None:
        self.patterns = {
            "CPF": r"(?<!\d)(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})(?!\d)",
            "CNPJ": r"(?<!\d)(?:\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}(?![a-zA-Z]))(?!\d)",
            "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "PROCESSO": (
                r"(?i)\b(?:"
                r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}"
                r"|\d{4}\.\d{2}\.\d\.\d{6}-\d"
                r"|\d{14}ADI"
                r"|(?:Reclamação|Rcl|RE|ADI|ADPF|ADC|ADO|ACO|ARE|MS|HC|RMS|RO|AI|CC|Pet|AC)\s+(?:n[º°]\.?\s*)?[\d\.]+(?:\/[A-Z]{2})?"
                r")\b"
            ),
            "OAB": (
                r"(?i)(?:"
                r"\bOAB[^\w]*(?:[A-Z]{2}[^\w]*)?\d+([\.\-]\d+)*(?:\/[A-Z]{2})?\b"
                r"|(?<![\.\d])\b\d{1,7}\/(?:AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\b"
                r")"
            ),
            "PLACA": (
                r"\b(?!(?:ADI|STF|STJ|TST|TRF|TRT|TRE|OAB|CPF|CEP|CNJ|MPF|PGR)\b)"
                r"[A-Z]{3}[- \n]*[\*0-9][A-Z0-9\*]{2,4}\b"
            ),
            "CEP": r"\b\d{5}-?\d{3}\b",
            "MANDADO": r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\.\d{2}\.\d{4}-\d{2}\b",
            "BOLETIM_OCORRENCIA": r"(?i)\b(IP|B\.?O\.?|APF)[^\d]*\d{1,5}\/\d{4}\b",
            "RG": r"(?i)\b(RG|Identidade)[^\d]*\d{1,2}\.?\d{3}\.?\d{3}-?[A-Z0-9]{0,2}\b",
            "CNH": r"(?i)\bCNH[^\d]*\d{9,11}\b",
            "AUTHORITY": r"(?i)\b(Juiz|Desembargador|Ministro|Promotor|Delegado|Excelentíssimo)\s+([A-ZÀ-Ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ]+)*)\b",
            "CODIGO_AUTENTICACAO": r"\b[A-Fa-f0-9]{4}(?:-[A-Fa-f0-9]{4}){3,}\b",
            "MEDIDA_PROVISORIA": r"(?i)\bMP\s+n[°º]\s*\d[\d\.\-/]+\b",
            "URL": r"https?://[a-zA-Z0-9_.-]+(?:\.[a-zA-Z]{2,})+(?:/[^\s\)\"\'>]*)?",
            "DATA": (
                r"(?i)\b(?:"
                r"\d{1,3}/\d{1,2}/\d{2,4}"
                r"|\d{1,2}\s+de\s+(?:janeiro|fevereiro|março|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)(?:\s+de\s+\d{4})?"
                r")\b"
            ),
        }

    def detect(self, text: str) -> List[Dict[str, Any]]:
        candidates = []
        for label, pattern in self.patterns.items():
            for match in re.finditer(pattern, text):
                candidates.append({
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group(),
                    "label": label,
                    "engine": "Regex"
                })

        candidates.sort(key=lambda c: (c["start"], -(c["end"] - c["start"])))

        selected: List[Dict[str, Any]] = []
        last_end = -1
        for ent in candidates:
            if ent["start"] < last_end:
                continue
            selected.append(ent)
            last_end = ent["end"]

        return selected

    def anonymize(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        matches = self.detect(text)

        anonymized_text = text
        for ent in reversed(matches):
            anonymized_text = (
                anonymized_text[:ent["start"]]
                + f"[{ent['label']}_ANONIMIZADO]"
                + anonymized_text[ent["end"]:]
            )

        clean_entities = [
            {"text": e["text"], "label": e["label"], "engine": e["engine"]}
            for e in matches
        ]

        return anonymized_text, clean_entities