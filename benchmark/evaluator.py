"""Avaliação e cálculo de métricas de performance dos motores."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence
import numpy as np

from benchmark.alignment import match_entities
from benchmark.config import DEFAULT_IOU_THRESHOLD, normalize_label
from benchmark.dataset import DocumentSample


@dataclass
class EvaluationResult:
    """Armazena os resultados consolidados da avaliação de um motor."""
    engine_name: str
    confusion_matrix: np.ndarray
    labels: List[str]
    precision_per_class: Dict[str, float]
    recall_per_class: Dict[str, float]
    f1_per_class: Dict[str, float]
    support_per_class: Dict[str, int]
    overall_precision: float
    overall_recall: float
    overall_f1: float
    total_documents: int
    total_gt_entities: int
    total_predicted_entities: int
    true_positives_count: int
    false_positives_count: int
    false_negatives_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


def evaluate_predictions(
    engine_name: str,
    predictions_per_doc: List[List[Dict[str, Any]]],
    dataset: Sequence[DocumentSample],
    iou_threshold: float = DEFAULT_IOU_THRESHOLD,
    normalize_labels: bool = True,
) -> EvaluationResult:
    """Calcula as métricas de performance a partir das predições e do ground truth."""
    all_matched_pairs: List[tuple[Dict[str, Any], Dict[str, Any]]] = []
    all_false_positives: List[Dict[str, Any]] = []
    all_false_negatives: List[Dict[str, Any]] = []
    all_gt_entities: List[Dict[str, Any]] = []
    all_pred_entities: List[Dict[str, Any]] = []

    for sample, preds in zip(dataset, predictions_per_doc):
        gts = sample.ground_truth_entities
        all_gt_entities.extend(gts)
        all_pred_entities.extend(preds)

        matched, fp, fn = match_entities(
            predicted_entities=preds,
            ground_truth_entities=gts,
            iou_threshold=iou_threshold,
            normalize_labels=normalize_labels,
        )
        all_matched_pairs.extend(matched)
        all_false_positives.extend(fp)
        all_false_negatives.extend(fn)

    # Coleta todas as classes presentes
    label_set = set()
    for g in all_gt_entities:
        label_set.add(normalize_label(g.get("label", "")) if normalize_labels else g.get("label", ""))
    for p in all_pred_entities:
        label_set.add(normalize_label(p.get("label", "")) if normalize_labels else p.get("label", ""))

    labels = sorted(list(label_set)) if label_set else ["SENSITIVE"]
    label_to_idx = {lbl: i for i, lbl in enumerate(labels)}
    num_labels = len(labels)

    # Matriz de confusão (dimensão N x N onde N = número de labels)
    cm = np.zeros((num_labels, num_labels), dtype=int)

    for pred, gt in all_matched_pairs:
        p_lbl = pred["normalized_label"] if normalize_labels else pred.get("label", "")
        g_lbl = gt["normalized_label"] if normalize_labels else gt.get("label", "")
        if g_lbl in label_to_idx and p_lbl in label_to_idx:
            cm[label_to_idx[g_lbl], label_to_idx[p_lbl]] += 1

    # Cálculo de métricas por classe
    precision_per_class: Dict[str, float] = {}
    recall_per_class: Dict[str, float] = {}
    f1_per_class: Dict[str, float] = {}
    support_per_class: Dict[str, int] = {}

    total_tp = 0
    total_fp = len(all_false_positives)
    total_fn = len(all_false_negatives)

    for lbl in labels:
        tp_c = sum(
            1 for p, g in all_matched_pairs
            if (p["normalized_label"] if normalize_labels else p.get("label", "")) == lbl
            and (g["normalized_label"] if normalize_labels else g.get("label", "")) == lbl
        )
        fp_unmatched = sum(
            1 for p in all_false_positives
            if (p["normalized_label"] if normalize_labels else p.get("label", "")) == lbl
        )
        fp_wrong_class = sum(
            1 for p, g in all_matched_pairs
            if (p["normalized_label"] if normalize_labels else p.get("label", "")) == lbl
            and (g["normalized_label"] if normalize_labels else g.get("label", "")) != lbl
        )
        fp_c = fp_unmatched + fp_wrong_class

        fn_unmatched = sum(
            1 for g in all_false_negatives
            if (g["normalized_label"] if normalize_labels else g.get("label", "")) == lbl
        )
        fn_wrong_class = sum(
            1 for p, g in all_matched_pairs
            if (g["normalized_label"] if normalize_labels else g.get("label", "")) == lbl
            and (p["normalized_label"] if normalize_labels else p.get("label", "")) != lbl
        )
        fn_c = fn_unmatched + fn_wrong_class

        support_c = sum(
            1 for g in all_gt_entities
            if (normalize_label(g.get("label", "")) if normalize_labels else g.get("label", "")) == lbl
        )

        prec_c = tp_c / (tp_c + fp_c) if (tp_c + fp_c) > 0 else 0.0
        rec_c = tp_c / (tp_c + fn_c) if (tp_c + fn_c) > 0 else 0.0
        f1_c = (2 * prec_c * rec_c / (prec_c + rec_c)) if (prec_c + rec_c) > 0 else 0.0

        precision_per_class[lbl] = prec_c
        recall_per_class[lbl] = rec_c
        f1_per_class[lbl] = f1_c
        support_per_class[lbl] = support_c
        total_tp += tp_c

    overall_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    overall_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    overall_f1 = (
        (2 * overall_prec * overall_rec / (overall_prec + overall_rec))
        if (overall_prec + overall_rec) > 0
        else 0.0
    )

    return EvaluationResult(
        engine_name=engine_name,
        confusion_matrix=cm,
        labels=labels,
        precision_per_class=precision_per_class,
        recall_per_class=recall_per_class,
        f1_per_class=f1_per_class,
        support_per_class=support_per_class,
        overall_precision=overall_prec,
        overall_recall=overall_rec,
        overall_f1=overall_f1,
        total_documents=len(dataset),
        total_gt_entities=len(all_gt_entities),
        total_predicted_entities=len(all_pred_entities),
        true_positives_count=total_tp,
        false_positives_count=total_fp,
        false_negatives_count=total_fn,
    )


def evaluate_engine(
    engine_name: str,
    dataset: Sequence[DocumentSample],
    iou_threshold: float = DEFAULT_IOU_THRESHOLD,
    engine_instance: Optional[Any] = None,
) -> EvaluationResult:
    """Executa a detecção do motor sobre cada documento do dataset e calcula as métricas."""
    if engine_instance is not None:
        engine = engine_instance
    else:
        from app.services.anonymization_service import get_engine
        engine = get_engine(engine_name)

    predictions_per_doc: List[List[Dict[str, Any]]] = []

    for sample in dataset:
        preds = engine.detect(sample.original_text)
        predictions_per_doc.append(preds)

    return evaluate_predictions(
        engine_name=engine_name,
        predictions_per_doc=predictions_per_doc,
        dataset=dataset,
        iou_threshold=iou_threshold,
    )


def evaluate_all_engines(
    dataset: Sequence[DocumentSample],
    engine_names: Optional[Sequence[str]] = None,
    iou_threshold: float = DEFAULT_IOU_THRESHOLD,
) -> Dict[str, EvaluationResult]:
    """Avalia múltiplos motores sobre o dataset."""
    from benchmark.config import SUPPORTED_ENGINES

    targets = engine_names or SUPPORTED_ENGINES
    results: Dict[str, EvaluationResult] = {}

    for name in targets:
        try:
            results[name] = evaluate_engine(name, dataset, iou_threshold=iou_threshold)
        except Exception as e:
            print(f"Aviso: Não foi possível avaliar motor '{name}': {e}")

    return results
