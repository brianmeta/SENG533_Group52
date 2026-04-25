
from __future__ import annotations

import csv
import os
from collections import defaultdict
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CATALOG_PATH = os.path.join(SCRIPT_DIR, "load_test_catalog", "all_csv_inventory.csv")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "load_test_graphs")

SERVICES = ["persistence", "auth", "image", "recommender", "webui", "all_services"]
INTENSITIES = ["low", "med", "high"]
THREAD_COUNTS = [1, 5, 10, 25, 50, 100, 250]
CPU_ORDER = ["100% CPU", "50% CPU", ""]

SERVICE_COLORS = {
    "persistence": "#1f77b4",
    "auth": "#2ca02c",
    "image": "#ff7f0e",
    "recommender": "#9467bd",
    "webui": "#d62728",
    "all_services": "#111111",
}


def _float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_inventory() -> List[Dict[str, str]]:
    if not os.path.exists(CATALOG_PATH):
        raise FileNotFoundError(
            f"Missing catalog: {CATALOG_PATH}. "
            "Run `python categorize_load_test_data.py` first."
        )

    with open(CATALOG_PATH, "r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def plot_category_counts(rows: List[Dict[str, str]]) -> None:
    category_counts = defaultdict(int)
    for row in rows:
        category_counts[row["category"] or "uncategorized"] += 1

    categories = sorted(category_counts.keys())
    values = [category_counts[category] for category in categories]

    plt.figure(figsize=(10, 5))
    bars = plt.bar(categories, values, color="#4C78A8")
    plt.title("CSV File Count by Category")
    plt.ylabel("Number of CSV files")
    plt.xticks(rotation=25, ha="right")
    plt.grid(axis="y", alpha=0.3)

    for bar, value in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(value), ha="center", va="bottom")

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "category_file_counts.png"), dpi=180)
    plt.close()


def _collect_rq1_metric(
    rows: List[Dict[str, str]],
    metric_name: str,
    allowed_categories: set[str],
) -> Dict[tuple, float]:
    mapping: Dict[tuple, float] = {}
    for row in rows:
        if row["category"] not in allowed_categories:
            continue
        if row["has_limbo_columns"] != "yes":
            continue
        cpu = row["cpu_level"]
        intensity = row["intensity"]
        service = row["service"]
        threads = _int(row["threads"], -1)
        metric = _float(row[metric_name], -1.0)
        if threads <= 0 or metric < 0:
            continue
        mapping[(cpu, intensity, service, threads)] = metric
    return mapping


def plot_rq1_metric_grid(
    rows: List[Dict[str, str]],
    metric_name: str,
    ylabel: str,
    title: str,
    output_name: str,
) -> None:
    categories = {"rq1_service", "rq1_combined"}
    metric_map = _collect_rq1_metric(rows, metric_name, categories)

    cpus_present = [cpu for cpu in CPU_ORDER if any(key[0] == cpu for key in metric_map)]
    if not cpus_present:
        return

    fig, axes = plt.subplots(len(cpus_present), len(INTENSITIES), figsize=(16, 4 * len(cpus_present)), squeeze=False)
    fig.suptitle(title, fontsize=14, fontweight="bold")

    for row_idx, cpu in enumerate(cpus_present):
        for col_idx, intensity in enumerate(INTENSITIES):
            ax = axes[row_idx][col_idx]
            for service in SERVICES:
                x_vals = []
                y_vals = []
                for threads in THREAD_COUNTS:
                    key = (cpu, intensity, service, threads)
                    if key in metric_map:
                        x_vals.append(threads)
                        y_vals.append(metric_map[key])
                if x_vals:
                    ax.plot(
                        x_vals,
                        y_vals,
                        marker="o",
                        markersize=4,
                        color=SERVICE_COLORS.get(service, "#333333"),
                        label=service,
                    )

            cpu_label = cpu if cpu else "no CPU tag"
            ax.set_title(f"{cpu_label} | {intensity.upper()} intensity")
            ax.set_xlabel("Threads")
            ax.set_ylabel(ylabel)
            ax.set_xscale("log")
            ax.set_xticks(THREAD_COUNTS)
            ax.xaxis.set_major_formatter(ScalarFormatter())
            ax.grid(True, alpha=0.3)
            if col_idx == len(INTENSITIES) - 1:
                ax.legend(loc="best", fontsize=8)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, output_name), dpi=180)
    plt.close()


def plot_stress_throughput(rows: List[Dict[str, str]]) -> None:
    stress_rows = [
        row
        for row in rows
        if row["category"] == "stress"
        and row["has_limbo_columns"] == "yes"
        and row["target_rps"]
        and row["throughput_req_s"]
    ]
    if not stress_rows:
        return

    grouped: Dict[str, List[tuple]] = defaultdict(list)
    for row in stress_rows:
        service = row["service"] or "all_services"
        target_rps = _float(row["target_rps"], 0.0)
        throughput = _float(row["throughput_req_s"], 0.0)
        grouped[service].append((target_rps, throughput))

    plt.figure(figsize=(10, 6))
    for service, points in sorted(grouped.items()):
        points.sort(key=lambda p: p[0])
        x_vals = [p[0] for p in points]
        y_vals = [p[1] for p in points]
        plt.plot(
            x_vals,
            y_vals,
            marker="o",
            linewidth=1.5,
            color=SERVICE_COLORS.get(service, "#333333"),
            label=service,
        )

    plt.title("Stress Tests: Achieved Throughput vs Target RPS")
    plt.xlabel("Target RPS")
    plt.ylabel("Measured Throughput (successful req/s)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "stress_throughput_vs_target_rps.png"), dpi=180)
    plt.close()


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    rows = load_inventory()

    print(f"Loaded {len(rows)} catalog rows from {CATALOG_PATH}")
    print("Generating graphs...")

    plot_category_counts(rows)
    plot_rq1_metric_grid(
        rows,
        metric_name="throughput_req_s",
        ylabel="Throughput (successful req/s)",
        title="RQ1 Throughput vs Threads (Service + Combined)",
        output_name="rq1_throughput_vs_threads.png",
    )
    plot_rq1_metric_grid(
        rows,
        metric_name="avg_response_time_sec",
        ylabel="Average response time (s)",
        title="RQ1 Average Response Time vs Threads (Service + Combined)",
        output_name="rq1_response_time_vs_threads.png",
    )
    plot_rq1_metric_grid(
        rows,
        metric_name="drop_rate_pct",
        ylabel="Drop rate (%)",
        title="RQ1 Drop Rate vs Threads (Service + Combined)",
        output_name="rq1_drop_rate_vs_threads.png",
    )
    plot_stress_throughput(rows)

    print(f"Done. Graphs are in: {OUTPUT_DIR}")
    for name in sorted(os.listdir(OUTPUT_DIR)):
        if name.endswith(".png"):
            print(f"  {name}")


if __name__ == "__main__":
    main()
