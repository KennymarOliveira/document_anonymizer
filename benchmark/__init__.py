"""Módulo de benchmark e avaliação de métricas dos motores de anonimização."""

from benchmark.evaluator import EvaluationResult, evaluate_engine, evaluate_all_engines
from benchmark.dataset import DocumentSample, load_dataset

__all__ = [
    "EvaluationResult",
    "evaluate_engine",
    "evaluate_all_engines",
    "DocumentSample",
    "load_dataset",
]
