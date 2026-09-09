"""Visualização de métricas de benchmark com Matplotlib no estilo das imagens de referência."""

from pathlib import Path
from typing import Any, Dict, List, Optional
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    plt = None
import numpy as np

from benchmark.evaluator import EvaluationResult



def plot_confusion_matrix(
    result: EvaluationResult,
    output_path: Optional[str | Path] = None,
    figsize: tuple = (7, 6),
    title: Optional[str] = None,
) -> Optional[Any]:
    """Gera o gráfico de matriz de confusão exatamente no estilo da Imagem 1 de referência.

    Características visuais replicadas:
    - Colormap 'Blues'
    - Células separadas por linhas brancas
    - Células com 0 exibem texto em cinza claro discreto
    - Células com valores altos exibem texto em branco
    - Células com valores baixos (> 0) exibem texto escuro
    - Rótulos do eixo X rotacionados verticalmente (90 graus)
    - Rótulos do eixo Y horizontais
    - Título: "{Engine} Confusion Matrix"
    - Sem barra de cores lateral
    """
    if not HAS_MATPLOTLIB:
        return None

    cm = result.confusion_matrix
    labels = result.labels

    if cm.size == 0 or len(labels) == 0:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, "Sem dados suficientes para Matriz de Confusão", ha="center", va="center")
        if output_path:
            plt.savefig(output_path, bbox_inches="tight", dpi=300)
            plt.close(fig)
        return fig

    n = len(labels)
    fig, ax = plt.subplots(figsize=figsize, facecolor="white")

    max_val = np.max(cm) if np.max(cm) > 0 else 1
    cmap = plt.cm.Blues

    im = ax.imshow(cm, interpolation="nearest", cmap=cmap, vmin=0, vmax=max_val)

    ax.set_xticks(np.arange(n))
    ax.set_yticks(np.arange(n))
    ax.set_xticklabels(labels, rotation=90, fontsize=11, color="#262626")
    ax.set_yticklabels(labels, fontsize=11, color="#262626")

    ax.set_xticks(np.arange(n + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(n + 1) - 0.5, minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=2)
    ax.tick_params(which="minor", bottom=False, left=False)

    for spine in ax.spines.values():
        spine.set_edgecolor("#cccccc")
        spine.set_linewidth(1.5)

    thresh = max_val / 2.0
    for i in range(n):
        for j in range(n):
            val = cm[i, j]
            if val == 0:
                text_color = "#b0b0b0"
            elif val > thresh:
                text_color = "white"
            else:
                text_color = "#08306b"

            ax.text(
                j, i, str(val),
                ha="center", va="center",
                color=text_color,
                fontsize=13,
                fontweight="normal"
            )

    chart_title = title or f"{result.engine_name.capitalize()} Confusion Matrix"
    ax.set_title(chart_title, fontsize=13, pad=12, color="#262626")
    ax.set_ylabel("True Class", fontsize=12, labelpad=10, color="#262626")
    ax.set_xlabel("Predicted Class", fontsize=12, labelpad=12, color="#262626")

    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(n - 0.5, -0.5)

    plt.tight_layout()

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out, bbox_inches="tight", dpi=300)
        plt.close(fig)

    return fig


def plot_classification_report(
    result: EvaluationResult,
    output_path: Optional[str | Path] = None,
    figsize: tuple = (7, 6),
    title: Optional[str] = None,
) -> Optional[Any]:
    """Gera o relatório de classificação em heatmap exatamente no estilo da Imagem 2 de referência.

    Características visuais replicadas:
    - Colormap 'YlGnBu' (Yellow-Green-Blue)
    - Colunas: precision, recall, f1, support
    - Rótulos das colunas rotacionados em ~45 graus
    - Valores de métricas formatados com 3 casas decimais (.3f)
    - Valores de support formatados como inteiros
    - Linhas de grade brancas nítidas
    - Barra de cores lateral com escala de 0.0 a 1.0
    - Título: "{Engine} Classification Report"
    """
    if not HAS_MATPLOTLIB:
        return None

    labels = result.labels
    if not labels:
        labels = ["SENSITIVE"]

    n_rows = len(labels)
    n_cols = 4

    data_metrics = np.zeros((n_rows, 3))
    data_support = np.zeros((n_rows, 1))

    for i, lbl in enumerate(labels):
        data_metrics[i, 0] = result.precision_per_class.get(lbl, 0.0)
        data_metrics[i, 1] = result.recall_per_class.get(lbl, 0.0)
        data_metrics[i, 2] = result.f1_per_class.get(lbl, 0.0)
        data_support[i, 0] = result.support_per_class.get(lbl, 0)

    fig, ax = plt.subplots(figsize=figsize, facecolor="white")

    cmap = plt.cm.YlGnBu

    im_metrics = ax.imshow(
        data_metrics,
        extent=[-0.5, 2.5, n_rows - 0.5, -0.5],
        cmap=cmap,
        vmin=0.0,
        vmax=1.0,
        aspect="auto"
    )

    support_color = cmap(0.12)
    for i in range(n_rows):
        rect = plt.Rectangle(
            (2.5, i - 0.5), 1.0, 1.0,
            facecolor=support_color,
            edgecolor="none"
        )
        ax.add_patch(rect)

    ax.set_xticks([0, 1, 2, 3])
    ax.set_xticklabels(["precision", "recall", "f1", "support"], rotation=45, ha="right", fontsize=11, color="#262626")
    ax.set_yticks(np.arange(n_rows))
    ax.set_yticklabels(labels, fontsize=11, color="#262626")

    ax.set_xticks(np.arange(5) - 0.5, minor=True)
    ax.set_yticks(np.arange(n_rows + 1) - 0.5, minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=2.5)
    ax.tick_params(which="minor", bottom=False, left=False)

    for spine in ax.spines.values():
        spine.set_edgecolor("#cccccc")
        spine.set_linewidth(1.5)

    for i in range(n_rows):
        for j in range(3):
            val = data_metrics[i, j]
            text_color = "white" if val >= 0.45 else "#1a1a1a"
            ax.text(
                j, i, f"{val:.3f}",
                ha="center", va="center",
                color=text_color,
                fontsize=12,
                fontweight="normal"
            )
        sup_val = int(data_support[i, 0])
        ax.text(
            3, i, str(sup_val),
            ha="center", va="center",
            color="#1a1a1a",
            fontsize=12,
            fontweight="normal"
        )

    cbar = fig.colorbar(im_metrics, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_ticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    cbar.ax.tick_params(labelsize=10, colors="#262626")
    cbar.outline.set_edgecolor("#cccccc")

    chart_title = title or f"{result.engine_name.capitalize()} Classification Report"
    ax.set_title(chart_title, fontsize=13, pad=12, color="#262626")

    ax.set_xlim(-0.5, 3.5)
    ax.set_ylim(n_rows - 0.5, -0.5)

    plt.tight_layout()

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out, bbox_inches="tight", dpi=300)
        plt.close(fig)

    return fig


def plot_engine_comparison(
    results: Dict[str, EvaluationResult],
    output_path: Optional[str | Path] = None,
    figsize: tuple = (10, 6),
) -> Optional[Any]:
    """Gera um gráfico comparativo de barras de Precision, Recall e F1 entre os motores."""
    if not HAS_MATPLOTLIB:
        return None

    engines = list(results.keys())
    if not engines:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, "Nenhum resultado para comparar", ha="center", va="center")
        if output_path:
            plt.savefig(output_path, bbox_inches="tight", dpi=300)
            plt.close(fig)
        return fig

    precisions = [results[e].overall_precision for e in engines]
    recalls = [results[e].overall_recall for e in engines]
    f1s = [results[e].overall_f1 for e in engines]

    x = np.arange(len(engines))
    width = 0.25

    fig, ax = plt.subplots(figsize=figsize, facecolor="white")

    rects1 = ax.bar(x - width, precisions, width, label="Precision", color="#1f77b4", edgecolor="white")
    rects2 = ax.bar(x, recalls, width, label="Recall", color="#2ca02c", edgecolor="white")
    rects3 = ax.bar(x + width, f1s, width, label="F1-Score", color="#17becf", edgecolor="white")

    ax.set_ylabel("Score", fontsize=12, color="#262626")
    ax.set_title("Comparação Geral de Performance dos Motores", fontsize=14, pad=14, color="#262626")
    ax.set_xticks(x)
    ax.set_xticklabels([e.capitalize() for e in engines], fontsize=11, color="#262626")
    ax.set_ylim(0, 1.15)
    ax.legend(loc="upper right", frameon=True, edgecolor="#cccccc")

    ax.yaxis.grid(True, linestyle="--", alpha=0.5, color="#d9d9d9")
    ax.set_axisbelow(True)

    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(
                f"{height:.2f}",
                xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center", va="bottom",
                fontsize=9, color="#333333"
            )

    autolabel(rects1)
    autolabel(rects2)
    autolabel(rects3)

    for spine in ax.spines.values():
        spine.set_edgecolor("#cccccc")

    plt.tight_layout()

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out, bbox_inches="tight", dpi=300)
        plt.close(fig)

    return fig
