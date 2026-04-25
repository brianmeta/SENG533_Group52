
from __future__ import annotations

import csv
import os
import shutil
from datetime import datetime
from typing import Dict, List

import categorize_load_test_data
import plot_load_test_graphs


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CATALOG_DIR = os.path.join(SCRIPT_DIR, "load_test_catalog")
GRAPHS_DIR = os.path.join(SCRIPT_DIR, "load_test_graphs")
REPORTS_DIR = os.path.join(SCRIPT_DIR, "load_test_reports")

INVENTORY_CSV = os.path.join(CATALOG_DIR, "all_csv_inventory.csv")
CATEGORY_SUMMARY_CSV = os.path.join(CATALOG_DIR, "category_summary.csv")
RQ1_SUMMARY_CSV = os.path.join(CATALOG_DIR, "rq1_summary.csv")


def ensure_parent(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def read_csv(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def copy_if_exists(src: str, dst: str) -> bool:
    if not os.path.exists(src):
        return False
    ensure_parent(os.path.dirname(dst))
    shutil.copy2(src, dst)
    return True


def format_number(value: str, fallback: str = "0") -> str:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return fallback
    return f"{num:,.2f}"


def write_markdown_summary(
    report_dir: str,
    generated_at: str,
    inventory_rows: List[Dict[str, str]],
    category_rows: List[Dict[str, str]],
    rq1_rows: List[Dict[str, str]],
) -> str:
    total_files = len(inventory_rows)
    limbo_files = sum(1 for row in inventory_rows if row.get("has_limbo_columns") == "yes")

    total_success = 0.0
    total_failed = 0.0
    total_dropped = 0.0
    for row in inventory_rows:
        try:
            total_success += float(row.get("total_success") or 0.0)
            total_failed += float(row.get("total_failed") or 0.0)
            total_dropped += float(row.get("total_dropped") or 0.0)
        except ValueError:
            pass

                                                              
    top_throughput = sorted(
        (
            row
            for row in rq1_rows
            if row.get("throughput_req_s")
            and row.get("service")
            and row.get("intensity")
            and row.get("threads")
        ),
        key=lambda row: float(row["throughput_req_s"]),
        reverse=True,
    )[:5]

    lines: List[str] = [
        "# TeaStore Load-Test Report",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Total CSV files cataloged: **{total_files}**",
        f"- LIMBO metric CSV files: **{limbo_files}**",
        f"- Aggregate successful transactions: **{format_number(str(total_success))}**",
        f"- Aggregate failed transactions: **{format_number(str(total_failed))}**",
        f"- Aggregate dropped transactions: **{format_number(str(total_dropped))}**",
        "",
        "## Included Artifacts",
        "",
        "- `catalog/all_csv_inventory.csv`: full per-file metadata + metrics",
        "- `catalog/category_summary.csv`: category-level counts and aggregate stats",
        "- `catalog/rq1_summary.csv`: flattened RQ1-oriented metrics for analysis",
        "- `graphs/*.png`: generated visualizations",
        "",
        "## Category Breakdown",
        "",
        "| Category | File Count | LIMBO Files | Avg Throughput (req/s) |",
        "|---|---:|---:|---:|",
    ]

    for row in sorted(category_rows, key=lambda r: r.get("category", "")):
        lines.append(
            "| {category} | {file_count} | {limbo_file_count} | {avg_tp} |".format(
                category=row.get("category", ""),
                file_count=row.get("file_count", "0"),
                limbo_file_count=row.get("limbo_file_count", "0"),
                avg_tp=format_number(row.get("avg_throughput_req_s", "0")),
            )
        )

    lines.extend(
        [
            "",
            "## Top 5 RQ1 Throughput Results",
            "",
            "| Service | Intensity | Threads | Throughput (req/s) | Avg RT (s) | Fail % | Drop % |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )

    if top_throughput:
        for row in top_throughput:
            lines.append(
                "| {service} | {intensity} | {threads} | {tp} | {rt} | {fail} | {drop} |".format(
                    service=row.get("service", ""),
                    intensity=row.get("intensity", ""),
                    threads=row.get("threads", ""),
                    tp=format_number(row.get("throughput_req_s", "0")),
                    rt=format_number(row.get("avg_response_time_sec", "0")),
                    fail=format_number(row.get("fail_rate_pct", "0")),
                    drop=format_number(row.get("drop_rate_pct", "0")),
                )
            )
    else:
        lines.append("| _(no RQ1 rows found)_ | - | - | - | - | - | - |")

    lines.extend(
        [
            "",
            "## Reproduction",
            "",
            "```bash",
            "python categorize_load_test_data.py",
            "python plot_load_test_graphs.py",
            "python build_load_test_report.py",
            "```",
            "",
        ]
    )

    summary_path = os.path.join(report_dir, "REPORT.md")
    with open(summary_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
    return summary_path


def main() -> None:
    print("Running data categorization...")
    categorize_load_test_data.main()

    print("\nGenerating graphs...")
    plot_load_test_graphs.main()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = os.path.join(REPORTS_DIR, f"report_{timestamp}")
    catalog_out = os.path.join(report_dir, "catalog")
    graphs_out = os.path.join(report_dir, "graphs")

    print("\nAssembling single report folder...")
    ensure_parent(catalog_out)
    ensure_parent(graphs_out)

    copied_catalog = [
        copy_if_exists(INVENTORY_CSV, os.path.join(catalog_out, "all_csv_inventory.csv")),
        copy_if_exists(CATEGORY_SUMMARY_CSV, os.path.join(catalog_out, "category_summary.csv")),
        copy_if_exists(RQ1_SUMMARY_CSV, os.path.join(catalog_out, "rq1_summary.csv")),
    ]

    copied_graph_count = 0
    if os.path.isdir(GRAPHS_DIR):
        for name in sorted(os.listdir(GRAPHS_DIR)):
            if not name.lower().endswith(".png"):
                continue
            src = os.path.join(GRAPHS_DIR, name)
            dst = os.path.join(graphs_out, name)
            if copy_if_exists(src, dst):
                copied_graph_count += 1

    inventory_rows = read_csv(INVENTORY_CSV)
    category_rows = read_csv(CATEGORY_SUMMARY_CSV)
    rq1_rows = read_csv(RQ1_SUMMARY_CSV)
    summary_path = write_markdown_summary(
        report_dir=report_dir,
        generated_at=datetime.now().isoformat(timespec="seconds"),
        inventory_rows=inventory_rows,
        category_rows=category_rows,
        rq1_rows=rq1_rows,
    )

    copied_catalog_count = sum(1 for ok in copied_catalog if ok)
    print("\nReport complete.")
    print(f"  Report folder: {report_dir}")
    print(f"  Catalog files copied: {copied_catalog_count}")
    print(f"  Graph files copied:   {copied_graph_count}")
    print(f"  Summary:              {summary_path}")


if __name__ == "__main__":
    main()
