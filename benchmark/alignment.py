"""Alinhamento e matching de entidades preditas contra o ground truth."""

from typing import Any, Dict, List, Optional, Tuple
from benchmark.config import normalize_label


def compute_span_iou(span_a: Tuple[int, int], span_b: Tuple[int, int]) -> float:
    """Calcula a Intersection over Union (IoU) entre dois intervalos de caracteres (start, end)."""
    start_a, end_a = span_a
    start_b, end_b = span_b

    inter_start = max(start_a, start_b)
    inter_end = min(end_a, end_b)
    intersection = max(0, inter_end - inter_start)

    if intersection == 0:
        return 0.0

    len_a = max(0, end_a - start_a)
    len_b = max(0, end_b - start_b)
    union = len_a + len_b - intersection

    if union <= 0:
        return 0.0

    return intersection / union


def match_entities(
    predicted_entities: List[Dict[str, Any]],
    ground_truth_entities: List[Dict[str, Any]],
    iou_threshold: float = 0.5,
    normalize_labels: bool = True,
) -> Tuple[List[Tuple[Dict[str, Any], Dict[str, Any]]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Emparelha entidades preditas com o ground truth baseado em sobreposição de span (IoU).

    Retorna:
        - matched_pairs: lista de tuplas (pred_entity, gt_entity)
        - false_positives: entidades preditas que não coincidiram com nenhum ground truth
        - false_negatives: entidades de ground truth que não foram detectadas
    """
    preds = [dict(p) for p in predicted_entities]
    gts = [dict(g) for g in ground_truth_entities]

    if normalize_labels:
        for p in preds:
            p["normalized_label"] = normalize_label(p.get("label", ""))
        for g in gts:
            g["normalized_label"] = normalize_label(g.get("label", ""))
    else:
        for p in preds:
            p["normalized_label"] = p.get("label", "")
        for g in gts:
            g["normalized_label"] = g.get("label", "")

    candidates = []
    for p_idx, pred in enumerate(preds):
        p_span = (pred.get("start", -1), pred.get("end", -1))
        if p_span[0] < 0 or p_span[1] <= p_span[0]:
            continue

        for g_idx, gt in enumerate(gts):
            g_span = (gt.get("start", -1), gt.get("end", -1))
            if g_span[0] < 0 or g_span[1] <= g_span[0]:
                continue

            iou = compute_span_iou(p_span, g_span)
            if iou >= iou_threshold:
                same_label = 1 if pred["normalized_label"] == gt["normalized_label"] else 0
                candidates.append((iou, same_label, p_idx, g_idx))

    candidates.sort(key=lambda x: (x[1], x[0]), reverse=True)

    matched_p_indices = set()
    matched_g_indices = set()
    matched_pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []

    for iou, _, p_idx, g_idx in candidates:
        if p_idx not in matched_p_indices and g_idx not in matched_g_indices:
            matched_p_indices.add(p_idx)
            matched_g_indices.add(g_idx)
            matched_pairs.append((preds[p_idx], gts[g_idx]))

    false_positives = [preds[i] for i in range(len(preds)) if i not in matched_p_indices]
    false_negatives = [gts[i] for i in range(len(gts)) if i not in matched_g_indices]

    return matched_pairs, false_positives, false_negatives
