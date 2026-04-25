
import os
import csv
import re
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(
    SCRIPT_DIR, "examples", "httploadgenerator", "load_test_results"
)
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "load_test_graphs")

CPU_LEVELS = ["100% CPU", "50% CPU"]
SERVICES = ["persistence", "auth", "image", "recommender", "webui"]
INTENSITIES = ["low", "med", "high"]
THREAD_COUNTS = [1, 5, 10, 25, 50, 100, 250]

SERVICE_COLORS = {
    "persistence": "#2196F3",
    "auth": "#4CAF50",
    "image": "#FF9800",
    "recommender": "#9C27B0",
    "webui": "#F44336",
}

INTENSITY_STYLES = {
    "low": "-",
    "med": "--",
    "high": ":",
}


def parse_csv(filepath):
    rows = []
    try:
        with open(filepath, "r") as f:
            first_line = f.readline()
        header_parts = first_line.strip().split(",")
        clean_header = header_parts[:7]
    except Exception:
        return rows

    try:
        with open(filepath, "r") as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) < 7:
                    continue
                try:
                    rows.append({
                        "target_time": float(row[0]),
                        "load_intensity": float(row[1]),
                        "success": int(row[2]),
                        "failed": int(row[3]),
                        "dropped": int(row[4]),
                        "avg_response_time": float(row[5]),
                        "dispatch_time": float(row[6]),
                    })
                except (ValueError, IndexError):
                    continue
    except Exception:
        pass
    return rows


def summarize(rows):
    active = [r for r in rows if r["load_intensity"] > 0]
    if not active:
        return None

    total_success = sum(r["success"] for r in active)
    total_failed = sum(r["failed"] for r in active)
    total_dropped = sum(r["dropped"] for r in active)
    total_requests = total_success + total_failed + total_dropped

    weighted_rt = sum(r["avg_response_time"] * r["success"] for r in active)
    avg_rt = weighted_rt / total_success if total_success > 0 else 0

    duration = active[-1]["target_time"] - active[0]["target_time"] + 1
    throughput = total_success / duration if duration > 0 else 0

    fail_rate = total_failed / total_requests * 100 if total_requests > 0 else 0

    max_intensity = max(r["load_intensity"] for r in active)

    drop_rate = total_dropped / total_requests * 100 if total_requests > 0 else 0
    total_demanded = sum(r["load_intensity"] for r in active)
    saturation = total_success / total_demanded * 100 if total_demanded > 0 else 100

    return {
        "total_success": total_success,
        "total_failed": total_failed,
        "total_dropped": total_dropped,
        "avg_response_time": avg_rt,
        "throughput": throughput,
        "fail_rate": fail_rate,
        "drop_rate": drop_rate,
        "saturation": saturation,
        "duration": duration,
        "max_intensity": max_intensity,
        "rows": active,
    }


def load_all_data():
    data = {}
    for cpu in CPU_LEVELS:
        cpu_dir = os.path.join(DATA_DIR, cpu)
        if not os.path.isdir(cpu_dir):
            print(f"  WARNING: {cpu_dir} not found, skipping")
            continue

        for service in SERVICES:
            for intensity in INTENSITIES:
                for threads in THREAD_COUNTS:
                    filename = f"rq1_{service}_{intensity}_t{threads}.csv"
                    filepath = os.path.join(cpu_dir, filename)
                    if not os.path.exists(filepath):
                        continue

                    rows = parse_csv(filepath)
                    summary = summarize(rows)
                    if summary:
                        key = (cpu, service, intensity, threads)
                        data[key] = summary

    return data


def plot_throughput_vs_threads(data):
    for cpu in CPU_LEVELS:
        fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
        fig.suptitle(f"Throughput vs Threads — {cpu}", fontsize=14, fontweight="bold")

        for ax, intensity in zip(axes, INTENSITIES):
            for service in SERVICES:
                x_vals, y_vals = [], []
                for threads in THREAD_COUNTS:
                    key = (cpu, service, intensity, threads)
                    if key in data:
                        x_vals.append(threads)
                        y_vals.append(data[key]["throughput"])

                if x_vals:
                    ax.plot(
                        x_vals, y_vals,
                        marker="o", markersize=4,
                        color=SERVICE_COLORS[service],
                        label=service,
                    )

            ax.set_title(f"{intensity.upper()} intensity")
            ax.set_xlabel("Threads")
            ax.set_xscale("log")
            ax.set_xticks(THREAD_COUNTS)
            ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
            ax.grid(True, alpha=0.3)
            if ax == axes[0]:
                ax.set_ylabel("Throughput (successful req/s)")

        axes[-1].legend(loc="upper left", fontsize=8)
        plt.tight_layout()
        safe_cpu = cpu.replace("%", "pct").replace(" ", "_")
        plt.savefig(os.path.join(OUTPUT_DIR, f"throughput_vs_threads_{safe_cpu}.png"), dpi=150)
        plt.close()


def plot_response_time_vs_threads(data):
    for cpu in CPU_LEVELS:
        fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
        fig.suptitle(f"Avg Response Time vs Threads — {cpu}", fontsize=14, fontweight="bold")

        for ax, intensity in zip(axes, INTENSITIES):
            for service in SERVICES:
                x_vals, y_vals = [], []
                for threads in THREAD_COUNTS:
                    key = (cpu, service, intensity, threads)
                    if key in data:
                        x_vals.append(threads)
                        y_vals.append(data[key]["avg_response_time"])

                if x_vals:
                    ax.plot(
                        x_vals, y_vals,
                        marker="o", markersize=4,
                        color=SERVICE_COLORS[service],
                        label=service,
                    )

            ax.set_title(f"{intensity.upper()} intensity")
            ax.set_xlabel("Threads")
            ax.set_xscale("log")
            ax.set_xticks(THREAD_COUNTS)
            ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
            ax.grid(True, alpha=0.3)
            if ax == axes[0]:
                ax.set_ylabel("Avg Response Time (s)")

        axes[-1].legend(loc="upper left", fontsize=8)
        plt.tight_layout()
        safe_cpu = cpu.replace("%", "pct").replace(" ", "_")
        plt.savefig(os.path.join(OUTPUT_DIR, f"response_time_vs_threads_{safe_cpu}.png"), dpi=150)
        plt.close()


def plot_failure_rate_vs_threads(data):
    for cpu in CPU_LEVELS:
        fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
        fig.suptitle(f"Failure Rate vs Threads — {cpu}", fontsize=14, fontweight="bold")

        for ax, intensity in zip(axes, INTENSITIES):
            for service in SERVICES:
                x_vals, y_vals = [], []
                for threads in THREAD_COUNTS:
                    key = (cpu, service, intensity, threads)
                    if key in data:
                        x_vals.append(threads)
                        y_vals.append(data[key]["fail_rate"])

                if x_vals:
                    ax.plot(
                        x_vals, y_vals,
                        marker="o", markersize=4,
                        color=SERVICE_COLORS[service],
                        label=service,
                    )

            ax.set_title(f"{intensity.upper()} intensity")
            ax.set_xlabel("Threads")
            ax.set_xscale("log")
            ax.set_xticks(THREAD_COUNTS)
            ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
            ax.set_ylabel("Failure Rate (%)" if ax == axes[0] else "")
            ax.grid(True, alpha=0.3)

        axes[-1].legend(loc="upper left", fontsize=8)
        plt.tight_layout()
        safe_cpu = cpu.replace("%", "pct").replace(" ", "_")
        plt.savefig(os.path.join(OUTPUT_DIR, f"failure_rate_vs_threads_{safe_cpu}.png"), dpi=150)
        plt.close()


def plot_cpu_comparison(data):
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("100% CPU vs 50% CPU Comparison — HIGH Intensity", fontsize=14, fontweight="bold")

    metrics = [
        ("throughput", "Throughput (req/s)"),
        ("avg_response_time", "Avg Response Time (s)"),
        ("fail_rate", "Failure Rate (%)"),
    ]

    for col, (metric, label) in enumerate(metrics):
        for row, (cpu, linestyle) in enumerate(
            [("100% CPU", "-"), ("50% CPU", "--")]
        ):
            ax = axes[row][col]
            for service in SERVICES:
                x_vals, y_vals = [], []
                for threads in THREAD_COUNTS:
                    key = (cpu, service, "high", threads)
                    if key in data:
                        x_vals.append(threads)
                        y_vals.append(data[key][metric])

                if x_vals:
                    ax.plot(
                        x_vals, y_vals,
                        marker="o", markersize=4,
                        linestyle=linestyle,
                        color=SERVICE_COLORS[service],
                        label=service,
                    )

            ax.set_title(f"{cpu} — {label}")
            ax.set_xlabel("Threads")
            ax.set_xscale("log")
            ax.set_xticks(THREAD_COUNTS)
            ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
            ax.set_ylabel(label)
            ax.grid(True, alpha=0.3)
            if col == 2:
                ax.legend(fontsize=7)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "cpu_comparison_high_intensity.png"), dpi=150)
    plt.close()


def plot_bottleneck_heatmap(data):
    for cpu in CPU_LEVELS:
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        fig.suptitle(
            f"Bottleneck Heatmap (Highest Avg Response Time) — {cpu}",
            fontsize=14, fontweight="bold",
        )

        for ax, intensity in zip(axes, INTENSITIES):
            matrix = np.zeros((len(SERVICES), len(THREAD_COUNTS)))

            for j, threads in enumerate(THREAD_COUNTS):
                for i, service in enumerate(SERVICES):
                    key = (cpu, service, intensity, threads)
                    if key in data:
                        matrix[i][j] = data[key]["avg_response_time"]

            im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd")
            ax.set_xticks(range(len(THREAD_COUNTS)))
            ax.set_xticklabels(THREAD_COUNTS, fontsize=8)
            ax.set_yticks(range(len(SERVICES)))
            ax.set_yticklabels(SERVICES, fontsize=9)
            ax.set_xlabel("Threads")
            ax.set_title(f"{intensity.upper()} intensity")

            for i in range(len(SERVICES)):
                for j in range(len(THREAD_COUNTS)):
                    val = matrix[i][j]
                    if val > 0:
                        ax.text(
                            j, i, f"{val:.2f}",
                            ha="center", va="center",
                            fontsize=6,
                            color="white" if val > matrix.max() * 0.6 else "black",
                        )

            plt.colorbar(im, ax=ax, label="Avg Response Time (s)", shrink=0.8)

        plt.tight_layout()
        safe_cpu = cpu.replace("%", "pct").replace(" ", "_")
        plt.savefig(os.path.join(OUTPUT_DIR, f"bottleneck_heatmap_{safe_cpu}.png"), dpi=150)
        plt.close()


def plot_drop_rate_vs_threads(data):
    for cpu in CPU_LEVELS:
        fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
        fig.suptitle(
            f"Drop Rate vs Threads (service saturation) — {cpu}",
            fontsize=14, fontweight="bold",
        )

        for ax, intensity in zip(axes, INTENSITIES):
            for service in SERVICES:
                x_vals, y_vals = [], []
                for threads in THREAD_COUNTS:
                    key = (cpu, service, intensity, threads)
                    if key in data:
                        x_vals.append(threads)
                        y_vals.append(data[key]["drop_rate"])

                if x_vals:
                    ax.plot(
                        x_vals, y_vals,
                        marker="o", markersize=4,
                        color=SERVICE_COLORS[service],
                        label=service,
                    )

            ax.set_title(f"{intensity.upper()} intensity")
            ax.set_xlabel("Threads")
            ax.set_xscale("log")
            ax.set_xticks(THREAD_COUNTS)
            ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
            ax.set_ylabel("Drop Rate (%)" if ax == axes[0] else "")
            ax.grid(True, alpha=0.3)

        axes[-1].legend(loc="upper right", fontsize=8)
        plt.tight_layout()
        safe_cpu = cpu.replace("%", "pct").replace(" ", "_")
        plt.savefig(os.path.join(OUTPUT_DIR, f"drop_rate_vs_threads_{safe_cpu}.png"), dpi=150)
        plt.close()


def plot_saturation_vs_threads(data):
    for cpu in CPU_LEVELS:
        fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
        fig.suptitle(
            f"Saturation (% of demanded load served) — {cpu}",
            fontsize=14, fontweight="bold",
        )

        for ax, intensity in zip(axes, INTENSITIES):
            for service in SERVICES:
                x_vals, y_vals = [], []
                for threads in THREAD_COUNTS:
                    key = (cpu, service, intensity, threads)
                    if key in data:
                        x_vals.append(threads)
                        y_vals.append(data[key]["saturation"])

                if x_vals:
                    ax.plot(
                        x_vals, y_vals,
                        marker="o", markersize=4,
                        color=SERVICE_COLORS[service],
                        label=service,
                    )

            ax.set_title(f"{intensity.upper()} intensity")
            ax.set_xlabel("Threads")
            ax.axhline(y=100, color="gray", linestyle=":", alpha=0.5, label="100% served")
            ax.set_xscale("log")
            ax.set_xticks(THREAD_COUNTS)
            ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
            ax.set_ylabel("Saturation (%)" if ax == axes[0] else "")
            ax.grid(True, alpha=0.3)

        axes[-1].legend(loc="lower right", fontsize=8)
        plt.tight_layout()
        safe_cpu = cpu.replace("%", "pct").replace(" ", "_")
        plt.savefig(os.path.join(OUTPUT_DIR, f"saturation_vs_threads_{safe_cpu}.png"), dpi=150)
        plt.close()


def plot_timeseries(data):
    for cpu in CPU_LEVELS:
        for intensity in INTENSITIES:
            fig, axes = plt.subplots(1, len(SERVICES), figsize=(25, 5), sharey=True)
            fig.suptitle(
                f"Throughput Over Time — {cpu} — {intensity.upper()} Intensity (t=50)",
                fontsize=14, fontweight="bold",
            )

            threads = 50
            for ax, service in zip(axes, SERVICES):
                key = (cpu, service, intensity, threads)
                if key not in data:
                    ax.set_title(f"{service}\n(no data)")
                    continue

                rows = data[key]["rows"]
                times = [r["target_time"] for r in rows]
                successes = [r["success"] for r in rows]
                intensities = [r["load_intensity"] for r in rows]

                ax.plot(times, successes, color=SERVICE_COLORS[service], label="Success", linewidth=1)
                ax2 = ax.twinx()
                ax2.plot(times, intensities, color="gray", alpha=0.3, linestyle="--", label="Load")
                ax2.set_ylabel("Load Intensity" if service == SERVICES[-1] else "")

                ax.set_title(service)
                ax.set_xlabel("Time (s)")
                if ax == axes[0]:
                    ax.set_ylabel("Successful Transactions")
                ax.grid(True, alpha=0.2)

            plt.tight_layout()
            safe_cpu = cpu.replace("%", "pct").replace(" ", "_")
            plt.savefig(
                os.path.join(OUTPUT_DIR, f"timeseries_{safe_cpu}_{intensity}.png"),
                dpi=150,
            )
            plt.close()


def print_bottleneck_summary(data):
    print()
    print("=" * 90)
    print("  BOTTLENECK ANALYSIS (by worst composite: response time + drop rate + fail rate)")
    print("=" * 90)

    for cpu in CPU_LEVELS:
        print(f"\n  {cpu}:")
        print(
            f"  {'Intensity':<10} {'Threads':<8} {'Bottleneck':<14} "
            f"{'Avg RT':>8} {'Drop%':>8} {'Fail%':>8} {'Saturation%':>12}"
        )
        print(f"  {'-'*70}")

        for intensity in INTENSITIES:
            for threads in THREAD_COUNTS:
                worst_service = None
                worst_score = -1
                for service in SERVICES:
                    key = (cpu, service, intensity, threads)
                    if key not in data:
                        continue
                    d = data[key]
                    score = (
                        d["avg_response_time"] * 10
                        + d["drop_rate"]
                        + d["fail_rate"]
                    )
                    if score > worst_score:
                        worst_score = score
                        worst_service = service

                if worst_service:
                    key = (cpu, worst_service, intensity, threads)
                    d = data[key]
                    print(
                        f"  {intensity:<10} {threads:<8} {worst_service:<14} "
                        f"{d['avg_response_time']:>8.4f} {d['drop_rate']:>8.1f} "
                        f"{d['fail_rate']:>8.2f} {d['saturation']:>12.1f}"
                    )

    print()
    print("=" * 90)
    print("  SATURATION POINT (thread count where service stops keeping up with demand)")
    print("=" * 90)

    for cpu in CPU_LEVELS:
        print(f"\n  {cpu}:")
        print(
            f"  {'Service':<14} {'Intensity':<10} "
            f"{'Max Threads at ~100%':>22} {'Throughput There':>18} {'Peak Throughput':>16}"
        )
        print(f"  {'-'*82}")

        for service in SERVICES:
            for intensity in INTENSITIES:
                max_saturated_threads = None
                max_saturated_tp = 0
                peak_tp = 0

                for threads in THREAD_COUNTS:
                    key = (cpu, service, intensity, threads)
                    if key not in data:
                        continue
                    d = data[key]
                    if d["throughput"] > peak_tp:
                        peak_tp = d["throughput"]
                    if d["drop_rate"] < 5:
                        max_saturated_threads = threads
                        max_saturated_tp = d["throughput"]

                sat_str = str(max_saturated_threads) if max_saturated_threads else "NONE (always dropping)"
                print(
                    f"  {service:<14} {intensity:<10} "
                    f"{sat_str:>22} {max_saturated_tp:>18.1f} {peak_tp:>16.1f}"
                )


def print_summary_table(data):
    print()
    print("=" * 100)
    print("  FULL SUMMARY TABLE")
    print("=" * 100)

    header = (
        f"{'CPU':<10} {'Service':<14} {'Intensity':<10} {'Threads':<8} "
        f"{'Success':>8} {'Failed':>8} {'Dropped':>8} {'Avg RT':>10} "
        f"{'Throughput':>12} {'Fail%':>8} {'Drop%':>8} {'Sat%':>8}"
    )
    print(header)
    print("-" * 116)

    for cpu in CPU_LEVELS:
        for service in SERVICES:
            for intensity in INTENSITIES:
                for threads in THREAD_COUNTS:
                    key = (cpu, service, intensity, threads)
                    if key not in data:
                        continue
                    d = data[key]
                    print(
                        f"{cpu:<10} {service:<14} {intensity:<10} {threads:<8} "
                        f"{d['total_success']:>8} {d['total_failed']:>8} "
                        f"{d['total_dropped']:>8} {d['avg_response_time']:>10.4f} "
                        f"{d['throughput']:>12.2f} {d['fail_rate']:>8.2f} "
                        f"{d['drop_rate']:>8.1f} {d['saturation']:>8.1f}"
                    )


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Loading data...")
    data = load_all_data()
    print(f"  Loaded {len(data)} test results")

    if not data:
        print("ERROR: No data found. Check that the results directories exist.")
        return

    print("\nGenerating graphs...")

    print("  Throughput vs Threads...")
    plot_throughput_vs_threads(data)

    print("  Response Time vs Threads...")
    plot_response_time_vs_threads(data)

    print("  Failure Rate vs Threads...")
    plot_failure_rate_vs_threads(data)

    print("  Drop Rate vs Threads...")
    plot_drop_rate_vs_threads(data)

    print("  Saturation vs Threads...")
    plot_saturation_vs_threads(data)

    print("  CPU Comparison (100% vs 50%)...")
    plot_cpu_comparison(data)

    print("  Bottleneck Heatmaps...")
    plot_bottleneck_heatmap(data)

    print("  Time Series...")
    plot_timeseries(data)

    print(f"\nAll graphs saved to: {OUTPUT_DIR}")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.endswith(".png"):
            print(f"  {f}")

    print_summary_table(data)
    print_bottleneck_summary(data)


if __name__ == "__main__":
    main()
