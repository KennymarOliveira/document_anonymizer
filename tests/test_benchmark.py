"""Testes automatizados para o módulo de benchmark de avaliação de métricas."""

import json
from pathlib import Path
import numpy as np
import pytest

from benchmark.alignment import compute_span_iou, match_entities
from benchmark.config import normalize_label
from benchmark.dataset import (
    DocumentSample,
    extract_ground_truth_from_diff,
    load_annotations_json,
    load_dataset,
)
from benchmark.evaluator import EvaluationResult, evaluate_engine, evaluate_predictions
from benchmark.run_benchmark import generate_summary_text
from benchmark.visualizer import (
    plot_classification_report,
    plot_confusion_matrix,
    plot_engine_comparison,
)


# --- 1. Testes de IoU e Alinhamento ---

def test_compute_span_iou_exact_match():
    assert compute_span_iou((10, 20), (10, 20)) == 1.0


def test_compute_span_iou_partial_overlap():
    iou = compute_span_iou((10, 20), (15, 25))
    assert pytest.approx(iou, 0.01) == 1 / 3


def test_compute_span_iou_no_overlap():
    assert compute_span_iou((0, 5), (10, 15)) == 0.0
    assert compute_span_iou((5, 10), (10, 15)) == 0.0


def test_compute_span_iou_contained():
    iou = compute_span_iou((10, 30), (15, 25))
    assert pytest.approx(iou, 0.01) == 0.5


def test_match_entities_perfect_and_errors():
    preds = [
        {"start": 10, "end": 20, "text": "João Silva", "label": "PER"},
        {"start": 30, "end": 44, "text": "123.456.789-00", "label": "CPF"},
        {"start": 50, "end": 60, "text": "extra text", "label": "LOC"},
    ]
    gts = [
        {"start": 10, "end": 20, "text": "João Silva", "label": "PERSON"},
        {"start": 30, "end": 44, "text": "123.456.789-00", "label": "CPF"},
        {"start": 80, "end": 90, "text": "01/01/2020", "label": "DATA"},
    ]

    matched, fps, fns = match_entities(preds, gts, iou_threshold=0.5, normalize_labels=True)

    assert len(matched) == 2
    assert len(fps) == 1
    assert fps[0]["text"] == "extra text"
    assert len(fns) == 1
    assert fns[0]["text"] == "01/01/2020"


# --- 2. Testes de Normalização de Labels ---

def test_normalize_label():
    assert normalize_label("PER") == "PESSOA"
    assert normalize_label("PERSON") == "PESSOA"
    assert normalize_label("EMAIL_ADDRESS") == "EMAIL"
    assert normalize_label("PHONE_NUMBER") == "TELEFONE"
    assert normalize_label("CPF") == "CPF"
    assert normalize_label("AUTHORITY") == "AUTORIDADE"
    assert normalize_label("CODIGO_AUTENTICACAO") == "COD_AUTENTICACAO"
    assert normalize_label("URL") == "URL"
    assert normalize_label("DATA") == "DATA"
    assert normalize_label("DATE_TIME") == "DATA"
    assert normalize_label("SEMANTIC_SENSITIVE") == "SEMANTICO"
    assert normalize_label(None) == "DESCONHECIDO"
    assert normalize_label("outro_qualquer") == "OUTRO_QUALQUER"


# --- 3. Testes de Dataset ---

def test_load_annotations_json(tmp_path):
    json_file = tmp_path / "doc1.json"
    data = {
        "entities": [
            {"text": "123.456.789-00", "label": "CPF", "start": 10, "end": 24},
            {"text": "Maria Santos", "label": "PER"},
        ]
    }
    json_file.write_text(json.dumps(data), encoding="utf-8")

    text = "O titular 123.456.789-00 e a senhora Maria Santos estiveram presentes."
    entities = load_annotations_json(json_file, original_text=text)

    assert len(entities) == 2
    assert entities[0]["label"] == "CPF"
    assert entities[0]["start"] == 10
    assert entities[1]["label"] == "PER"
    assert entities[1]["start"] == text.find("Maria Santos")
    assert entities[1]["end"] == entities[1]["start"] + len("Maria Santos")


def test_extract_ground_truth_from_diff():
    orig = "O réu João da Silva, portador do CPF 123.456.789-00, reside em BH."
    anon = "O réu █████████████, portador do CPF ██████████████, reside em BH."

    gts = extract_ground_truth_from_diff(orig, anon)
    assert len(gts) == 2
    texts = [g["text"] for g in gts]
    assert "João da Silva" in texts
    assert "123.456.789-00" in texts


# --- 4. Testes do Avaliador e Métricas ---

def test_evaluate_predictions_calculation():
    sample = DocumentSample(
        filename="test.txt",
        original_text="João tem CPF 123.456.789-00 e mora em BH.",
        ground_truth_entities=[
            {"start": 0, "end": 4, "text": "João", "label": "PER"},
            {"start": 13, "end": 27, "text": "123.456.789-00", "label": "CPF"},
            {"start": 38, "end": 40, "text": "BH", "label": "LOC"},
        ]
    )

    preds = [
        {"start": 0, "end": 4, "text": "João", "label": "PER"},
        {"start": 13, "end": 27, "text": "123.456.789-00", "label": "CPF"},
        {"start": 30, "end": 34, "text": "mora", "label": "PER"},
    ]

    res = evaluate_predictions(
        engine_name="test_engine",
        predictions_per_doc=[preds],
        dataset=[sample],
        normalize_labels=True,
    )

    assert isinstance(res, EvaluationResult)
    assert res.total_documents == 1
    assert res.total_gt_entities == 3
    assert res.total_predicted_entities == 3
    assert res.true_positives_count == 2
    assert res.false_positives_count == 1
    assert res.false_negatives_count == 1

    assert res.precision_per_class["CPF"] == 1.0
    assert res.recall_per_class["CPF"] == 1.0
    assert res.f1_per_class["CPF"] == 1.0

    assert res.precision_per_class["PESSOA"] == 0.5
    assert res.recall_per_class["PESSOA"] == 1.0

    assert res.precision_per_class["LOCAL"] == 0.0
    assert res.recall_per_class["LOCAL"] == 0.0

    assert res.confusion_matrix.shape == (len(res.labels), len(res.labels))


# --- 5. Testes de Visualização (Matplotlib) ---

def test_visualizer_generates_and_saves_plots(tmp_path):
    pytest.importorskip("matplotlib")
    labels = ["PESSOA", "CPF", "LOCAL", "ORGANIZACAO"]
    cm = np.array([
        [25, 0, 1, 0],
        [0, 30, 0, 0],
        [1, 0, 20, 2],
        [0, 0, 1, 15],
    ])

    res = EvaluationResult(
        engine_name="mock_svc",
        confusion_matrix=cm,
        labels=labels,
        precision_per_class={"PESSOA": 0.92, "CPF": 1.00, "LOCAL": 0.90, "ORGANIZACAO": 0.88},
        recall_per_class={"PESSOA": 0.96, "CPF": 1.00, "LOCAL": 0.86, "ORGANIZACAO": 0.93},
        f1_per_class={"PESSOA": 0.94, "CPF": 1.00, "LOCAL": 0.88, "ORGANIZACAO": 0.90},
        support_per_class={"PESSOA": 26, "CPF": 30, "LOCAL": 23, "ORGANIZACAO": 16},
        overall_precision=0.95,
        overall_recall=0.94,
        overall_f1=0.945,
        total_documents=10,
        total_gt_entities=95,
        total_predicted_entities=94,
        true_positives_count=90,
        false_positives_count=4,
        false_negatives_count=5,
    )

    cm_path = tmp_path / "mock_cm.png"
    plot_confusion_matrix(res, output_path=cm_path)
    assert cm_path.exists()
    assert cm_path.stat().st_size > 5000

    cr_path = tmp_path / "mock_cr.png"
    plot_classification_report(res, output_path=cr_path)
    assert cr_path.exists()
    assert cr_path.stat().st_size > 5000

    comp_path = tmp_path / "comp.png"
    fig = plot_engine_comparison({"Engine A": res, "Engine B": res}, output_path=comp_path)
    assert comp_path.exists()
    assert comp_path.stat().st_size > 5000
    if fig is not None:
        assert fig.axes[0].get_title() == "General Engine Metrics"


def test_plot_engine_comparison_custom_title_and_empty():
    pytest.importorskip("matplotlib")
    res = EvaluationResult(
        engine_name="mock",
        confusion_matrix=np.array([[1]]),
        labels=["PESSOA"],
        precision_per_class={"PESSOA": 1.0},
        recall_per_class={"PESSOA": 1.0},
        f1_per_class={"PESSOA": 1.0},
        support_per_class={"PESSOA": 1},
        overall_precision=1.0,
        overall_recall=1.0,
        overall_f1=1.0,
        total_documents=1,
        total_gt_entities=1,
        total_predicted_entities=1,
        true_positives_count=1,
        false_positives_count=0,
        false_negatives_count=0,
    )

    fig_custom = plot_engine_comparison({"Mock": res}, title="Meu Titulo Customizado")
    assert fig_custom.axes[0].get_title() == "Meu Titulo Customizado"

    fig_empty = plot_engine_comparison({})
    assert "Nenhum resultado para comparar" in fig_empty.axes[0].texts[0].get_text()


def test_visualizer_fallback_sem_matplotlib(monkeypatch):
    """Garante que funções do visualizer retornem None de forma segura quando matplotlib não estiver disponível."""
    import benchmark.visualizer as vis
    monkeypatch.setattr(vis, "HAS_MATPLOTLIB", False)

    dummy_res = EvaluationResult(
        engine_name="dummy",
        confusion_matrix=np.array([]),
        labels=[],
        precision_per_class={},
        recall_per_class={},
        f1_per_class={},
        support_per_class={},
        overall_precision=0.0,
        overall_recall=0.0,
        overall_f1=0.0,
        total_documents=0,
        total_gt_entities=0,
        total_predicted_entities=0,
        true_positives_count=0,
        false_positives_count=0,
        false_negatives_count=0,
    )

    assert vis.plot_confusion_matrix(dummy_res) is None
    assert vis.plot_classification_report(dummy_res) is None
    assert vis.plot_engine_comparison({"dummy": dummy_res}) is None


def test_load_dataset_com_json(tmp_path):
    """Valida o carregamento integrado do dataset a partir da estrutura originals/ e ground_truth/."""
    orig_dir = tmp_path / "originals"
    gt_dir = tmp_path / "ground_truth"
    orig_dir.mkdir()
    gt_dir.mkdir()

    # Cria documento original em TXT
    doc_txt = orig_dir / "peticao.txt"
    doc_txt.write_text("Cliente com CPF 123.456.789-00 em Brasilia.", encoding="utf-8")

    # Cria anotações correspondentes no ground_truth
    anotacoes = {
        "entities": [
            {"text": "123.456.789-00", "label": "CPF", "start": 16, "end": 30},
            {"text": "Brasilia", "label": "LOC", "start": 34, "end": 42},
        ]
    }
    (gt_dir / "peticao.json").write_text(json.dumps(anotacoes), encoding="utf-8")

    samples = load_dataset(tmp_path)
    assert len(samples) == 1
    sample = samples[0]
    assert sample.filename == "peticao.txt"
    assert "CPF 123.456.789-00" in sample.original_text
    assert len(sample.ground_truth_entities) == 2
    assert sample.ground_truth_entities[0]["label"] == "CPF"


def test_evaluate_engine_com_instancia_mock():
    """Valida a orquestração de evaluate_engine com injeção de motor mock."""
    sample = DocumentSample(
        filename="doc.txt",
        original_text="Texto com CPF 111.222.333-44",
        ground_truth_entities=[{"text": "111.222.333-44", "label": "CPF", "start": 14, "end": 28}],
    )

    class MockEngine:
        def detect(self, text: str):
            return [{"text": "111.222.333-44", "label": "CPF", "start": 14, "end": 28}]

    res = evaluate_engine("mock_engine", [sample], engine_instance=MockEngine())
    assert res.engine_name == "mock_engine"
    assert res.true_positives_count == 1
    assert res.false_positives_count == 0
    assert res.false_negatives_count == 0
    assert res.overall_precision == 1.0
    assert res.overall_recall == 1.0
    assert res.overall_f1 == 1.0


def test_generate_summary_text(tmp_path):
    """Valida a formatação e geração do relatório textual de benchmark."""
    res = EvaluationResult(
        engine_name="regex",
        confusion_matrix=np.array([[5]]),
        labels=["CPF"],
        precision_per_class={"CPF": 1.0},
        recall_per_class={"CPF": 1.0},
        f1_per_class={"CPF": 1.0},
        support_per_class={"CPF": 5},
        overall_precision=1.0,
        overall_recall=1.0,
        overall_f1=1.0,
        total_documents=1,
        total_gt_entities=5,
        total_predicted_entities=5,
        true_positives_count=5,
        false_positives_count=0,
        false_negatives_count=0,
    )

    output_txt = tmp_path / "summary_test.txt"
    generate_summary_text({"regex": res}, output_txt)

    assert output_txt.exists()
    conteudo = output_txt.read_text(encoding="utf-8")
    assert "RELATÓRIO CONSOLIDADO DO BENCHMARK DE ANONIMIZAÇÃO" in conteudo
    assert "Motor: REGEX" in conteudo
    assert "Documentos avaliados:       1" in conteudo
    assert "Overall Precision:          1.0000" in conteudo
    assert "CPF" in conteudo
