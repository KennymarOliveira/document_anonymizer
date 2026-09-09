"""Script CLI principal para execução do benchmark e geração de métricas visuais."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import List

from benchmark.config import DEFAULT_IOU_THRESHOLD, SUPPORTED_ENGINES
from benchmark.dataset import load_dataset
from benchmark.evaluator import evaluate_engine
from benchmark.visualizer import (
    HAS_MATPLOTLIB,
    plot_classification_report,
    plot_confusion_matrix,
    plot_engine_comparison,
)


def print_banner():
    print("=" * 70)
    print("      DOCUMENT ANONYMIZER - BENCHMARK & EVALUATION ENGINE      ")
    print("=" * 70)


def generate_summary_text(results: dict, output_path: Path):
    """Gera um relatório descritivo em texto plano com todas as métricas."""
    lines = [
        "=" * 70,
        "RELATÓRIO CONSOLIDADO DO BENCHMARK DE ANONIMIZAÇÃO",
        "=" * 70,
        "",
    ]

    for name, res in results.items():
        lines.append(f"Motor: {name.upper()}")
        lines.append("-" * 50)
        lines.append(f"  Documentos avaliados:       {res.total_documents}")
        lines.append(f"  Entidades no Ground Truth:  {res.total_gt_entities}")
        lines.append(f"  Entidades detectadas:       {res.total_predicted_entities}")
        lines.append(f"  True Positives:             {res.true_positives_count}")
        lines.append(f"  False Positives:            {res.false_positives_count}")
        lines.append(f"  False Negatives:            {res.false_negatives_count}")
        lines.append(f"  Overall Precision:          {res.overall_precision:.4f}")
        lines.append(f"  Overall Recall:             {res.overall_recall:.4f}")
        lines.append(f"  Overall F1-Score:           {res.overall_f1:.4f}")
        lines.append("")
        lines.append("  Métricas por Categoria:")
        lines.append(f"    {'Categoria':<20} {'Precision':<12} {'Recall':<12} {'F1':<12} {'Support':<8}")
        for lbl in res.labels:
            p = res.precision_per_class.get(lbl, 0.0)
            r = res.recall_per_class.get(lbl, 0.0)
            f1 = res.f1_per_class.get(lbl, 0.0)
            sup = res.support_per_class.get(lbl, 0)
            lines.append(f"    {lbl:<20} {p:<12.3f} {r:<12.3f} {f1:<12.3f} {sup:<8}")
        lines.append("")
        lines.append("=" * 70)

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Executa avaliação de métricas dos motores de anonimização contra um dataset de comparação."
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="benchmark/data",
        help="Caminho do diretório contendo 'originals' e 'ground_truth' (padrão: benchmark/data)",
    )
    parser.add_argument(
        "--engines",
        type=str,
        default=",".join(SUPPORTED_ENGINES),
        help=f"Motores a avaliar separados por vírgula (padrão: {','.join(SUPPORTED_ENGINES)})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmark/data/results",
        help="Diretório para salvar os gráficos e relatórios (padrão: benchmark/data/results)",
    )
    parser.add_argument(
        "--iou-threshold",
        type=float,
        default=DEFAULT_IOU_THRESHOLD,
        help=f"Threshold mínimo de IoU para considerar match de entidade (padrão: {DEFAULT_IOU_THRESHOLD})",
    )

    args = parser.parse_args()
    print_banner()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    base_output_dir = Path(args.output_dir)
    timestamp_folder = datetime.now().strftime("%d_%m_%Y_TIME_%H_%M_%S")
    output_dir = base_output_dir / timestamp_folder
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_engines = [e.strip().lower() for e in args.engines.split(",") if e.strip()]

    print(f"Diretório de dados: {data_dir.resolve()}")
    print(f"Diretório de saída: {output_dir.resolve()}")
    print(f"Motores selecionados: {', '.join(selected_engines)}")
    print(f"IoU Threshold: {args.iou_threshold}")
    print("-" * 70)

    print("Carregando dataset...")
    dataset = load_dataset(data_dir)

    if not dataset:
        print("\n[AVISO] Nenhum documento válido encontrado no diretório especificado.")
        print("Para popular o dataset, adicione seus arquivos:")
        print(f"  - PDFs/DOCXs originais em:    {data_dir / 'originals'}")
        print(f"  - PDFs anonimizados ou JSONs em: {data_dir / 'ground_truth'}")
        sys.exit(0)

    total_gt = sum(len(d.ground_truth_entities) for d in dataset)
    print(f"Sucesso: {len(dataset)} documento(s) carregado(s), com {total_gt} entidade(s) de ground truth.\n")

    results = {}
    for engine_name in selected_engines:
        print(f"==> Avaliando motor '{engine_name}'...")
        try:
            res = evaluate_engine(engine_name, dataset, iou_threshold=args.iou_threshold)
            results[engine_name] = res

            if HAS_MATPLOTLIB:
                cm_path = output_dir / f"{engine_name}_confusion_matrix.png"
                cm_path = output_dir / f"confusion_matrix_{engine_name}.png"
                plot_confusion_matrix(res, output_path=cm_path)
                print(f"    - Confusion Matrix salva em: {cm_path.name}")

                cr_path = output_dir / f"{engine_name}_classification_report.png"
                cr_path = output_dir / f"classification_report_{engine_name}.png"
                plot_classification_report(res, output_path=cr_path)
                print(f"    - Classification Report salvo em: {cr_path.name}")
            else:
                print("    - [INFO] Matplotlib não instalado. Gráficos PNG ignorados.")

            print(f"    Score -> Precision: {res.overall_precision:.3f} | Recall: {res.overall_recall:.3f} | F1: {res.overall_f1:.3f}\n")
        except Exception as exc:
            print(f"    [ERRO] Falha ao avaliar '{engine_name}': {exc}\n")

    if results:
        engine_tag = "_".join(results.keys())

        if HAS_MATPLOTLIB:
            comp_path = output_dir / f"general_engine_metrics_{engine_tag}.png"
            plot_engine_comparison(results, output_path=comp_path)
            print(f"==> Gráfico comparativo geral salvo em: {comp_path.name}")
        else:
            print("[INFO] Para gerar gráficos visuais (PNG), instale o matplotlib:")
            print("       poetry install  (ou poetry add matplotlib)\n")

        summary_txt_path = output_dir / "summary.txt"
        summary_txt_path = output_dir / f"summary_{engine_tag}.txt"
        generate_summary_text(results, summary_txt_path)
        print(f"==> Resumo textual salvo em: {summary_txt_path.name}")

        if len(results) > 1:
            for name, res in results.items():
                indiv_txt_path = output_dir / f"summary_{name}.txt"
                generate_summary_text({name: res}, indiv_txt_path)

        summary_json = {
            name: {
                "overall_precision": res.overall_precision,
                "overall_recall": res.overall_recall,
                "overall_f1": res.overall_f1,
                "total_documents": res.total_documents,
                "total_gt_entities": res.total_gt_entities,
                "total_predicted_entities": res.total_predicted_entities,
                "true_positives": res.true_positives_count,
                "false_positives": res.false_positives_count,
                "false_negatives": res.false_negatives_count,
                "precision_per_class": res.precision_per_class,
                "recall_per_class": res.recall_per_class,
                "f1_per_class": res.f1_per_class,
                "support_per_class": res.support_per_class,
            }
            for name, res in results.items()
        }
        summary_json_path = output_dir / "summary.json"
        summary_json_path = output_dir / f"summary_{engine_tag}.json"
        summary_json_path.write_text(json.dumps(summary_json, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"==> Resumo JSON salvo em: {summary_json_path.name}")

        if len(results) > 1:
            for name, res in results.items():
                indiv_json = {name: summary_json[name]}
                indiv_json_path = output_dir / f"summary_{name}.json"
                indiv_json_path.write_text(json.dumps(indiv_json, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 70)
    print("Benchmark concluído com sucesso!")
    print("=" * 70)


if __name__ == "__main__":
    main()
