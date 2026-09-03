"""Carregamento e gerenciamento do dataset de benchmark."""

import difflib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.extractors.file_extractor import extract_text


@dataclass
class DocumentSample:
    """Representa um documento de teste com suas anotações de ground truth."""
    filename: str
    original_text: str
    ground_truth_entities: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


def load_annotations_json(json_path: Path | str, original_text: Optional[str] = None) -> List[Dict[str, Any]]:
    """Carrega anotações de ground truth a partir de um arquivo JSON.

    Formatos suportados:
    1. Lista de entidades: [{"text": "...", "label": "...", "start": 0, "end": 10}, ...]
    2. Dicionário: {"entities": [...]} ou {"entities_found": [...]}
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de anotações não encontrado: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        raw_entities = data.get("entities") or data.get("entities_found") or []
    elif isinstance(data, list):
        raw_entities = data
    else:
        raw_entities = []

    normalized_entities = []
    for item in raw_entities:
        text = item.get("text", "")
        label = item.get("label", "SENSITIVE")
        start = item.get("start")
        end = item.get("end")

        # Se start e end não foram fornecidos mas temos o texto original, calcula offsets
        if (start is None or end is None) and original_text and text:
            idx = original_text.find(text)
            if idx != -1:
                start = idx
                end = idx + len(text)
            else:
                start = -1
                end = -1

        normalized_entities.append({
            "text": text,
            "label": label,
            "start": start if start is not None else -1,
            "end": end if end is not None else -1,
        })

    return normalized_entities


def extract_ground_truth_from_diff(
    original_text: str,
    anonymized_text: str,
    default_label: str = "SENSITIVE"
) -> List[Dict[str, Any]]:
    """Extrai entidades de ground truth comparando texto original e texto anonimizado.

    Útil quando os dados vêm como pares de PDFs (original vs já anonimizado).
    Detecta partes deletadas ou substituídas por blocos '█'.
    """
    matcher = difflib.SequenceMatcher(None, original_text, anonymized_text)
    entities: List[Dict[str, Any]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "delete":
            deleted_text = original_text[i1:i2]
            if deleted_text.strip():
                entities.append({
                    "text": deleted_text,
                    "label": default_label,
                    "start": i1,
                    "end": i2,
                })
        elif tag == "replace":
            original_sub = original_text[i1:i2]
            anonymized_sub = anonymized_text[j1:j2]
            # Detecta se foi substituído por caractere de tarja ou removido
            if "█" in anonymized_sub or not anonymized_sub.strip():
                if original_sub.strip():
                    entities.append({
                        "text": original_sub,
                        "label": default_label,
                        "start": i1,
                        "end": i2,
                    })

    return entities


def load_dataset(data_dir: Path | str) -> List[DocumentSample]:
    """Carrega o dataset a partir do diretório informado.

    Estrutura esperada:
    data_dir/
      ├── originals/           (arquivos originais: .pdf, .docx, .txt)
      └── ground_truth/        (arquivos .json ou arquivos .pdf comparativos)
    """
    data_path = Path(data_dir)
    originals_dir = data_path / "originals"
    ground_truth_dir = data_path / "ground_truth"

    if not originals_dir.exists():
        originals_dir = data_path

    samples: List[DocumentSample] = []

    valid_exts = {".pdf", ".docx", ".doc", ".txt"}
    original_files = [f for f in originals_dir.glob("*") if f.suffix.lower() in valid_exts]

    for orig_file in sorted(original_files):
        stem = orig_file.stem
        raw_bytes = orig_file.read_bytes()
        try:
            original_text = extract_text(orig_file.name, raw_bytes)
        except Exception:
            continue

        gt_entities: List[Dict[str, Any]] = []

        # 1. Procura anotações JSON
        json_candidates = [
            ground_truth_dir / f"{stem}.json",
            data_path / f"{stem}.json",
            originals_dir / f"{stem}.json",
        ]
        json_found = next((p for p in json_candidates if p.exists()), None)

        if json_found:
            gt_entities = load_annotations_json(json_found, original_text=original_text)
        else:
            # 2. Procura arquivo correspondente no ground_truth_dir para comparar diff
            gt_pdf_candidates = [
                ground_truth_dir / orig_file.name,
                ground_truth_dir / f"{stem}_anonymized{orig_file.suffix}",
                ground_truth_dir / f"anonimizado_{orig_file.name}",
            ]
            gt_file_found = next((p for p in gt_pdf_candidates if p.exists()), None)

            if gt_file_found:
                try:
                    gt_bytes = gt_file_found.read_bytes()
                    gt_text = extract_text(gt_file_found.name, gt_bytes)
                    gt_entities = extract_ground_truth_from_diff(original_text, gt_text)
                except Exception:
                    gt_entities = []

        samples.append(DocumentSample(
            filename=orig_file.name,
            original_text=original_text,
            ground_truth_entities=gt_entities,
        ))

    return samples
