
from __future__ import annotations

import csv
import os
import re
from collections import defaultdict
from typing import Dict, List, Optional


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.path.join(SCRIPT_DIR, "examples", "httploadgenerator")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "load_test_catalog")

LIMBO_PREFIX = "Target Time,Load Intensity,Successful Transactions"
SERVICES = {"persistence", "auth", "image", "recommender", "webui"}


def parse_filename_metadata(rel_path: str) -> Dict[str, Optional[str]]:
    normalized = rel_path.replace("\\", "/")
    filename = os.path.basename(normalized)
    parent = os.path.dirname(normalized)

    metadata: Dict[str, Optional[str]] = {
        "category": "uncategorized",
        "test_family": None,
        "cpu_level": None,
        "service": None,
        "intensity": None,
        "threads": None,
        "target_rps": None,
        "is_run_log": "no",
    }

    if "load_test_results/100% CPU" in normalized:
        metadata["cpu_level"] = "100% CPU"
    elif "load_test_results/50% CPU" in normalized:
        metadata["cpu_level"] = "50% CPU"

    if filename == "_run_log.csv":
        metadata["category"] = "run_log"
        metadata["test_family"] = os.path.basename(parent) if parent else "unknown"
        metadata["is_run_log"] = "yes"
        return metadata

    if filename.startswith("increasing") and filename.endswith("Intensity.csv"):
        metadata["category"] = "intensity_profile"
        metadata["test_family"] = "profile"
        return metadata

    match = re.match(r"rq1_([a-z]+)_(low|med|high)_t(\d+)\.csv$", filename)
    if match:
        service, intensity, threads = match.groups()
        metadata["category"] = "rq1_service"
        metadata["test_family"] = "rq1"
        metadata["service"] = service
        metadata["intensity"] = intensity
        metadata["threads"] = threads
        return metadata

    match = re.match(r"combined_(low|med|high)_t(\d+)\.csv$", filename)
    if match:
        intensity, threads = match.groups()
        metadata["category"] = "rq1_combined"
        metadata["test_family"] = "rq1"
        metadata["service"] = "all_services"
        metadata["intensity"] = intensity
        metadata["threads"] = threads
        return metadata

    match = re.match(r"rq1_([a-z]+)_isolated(\d+)?\.csv$", filename)
    if match:
        service, threads = match.groups()
        metadata["category"] = "rq1_isolated"
        metadata["test_family"] = "rq1"
        metadata["service"] = service if service in SERVICES else "unknown"
        metadata["threads"] = threads
        return metadata

    match = re.match(r"stress_(?:([a-z]+)_)?(\d+)rps(?:_t(\d+))?\.csv$", filename)
    if match:
        service, rps, threads = match.groups()
        metadata["category"] = "stress"
        metadata["test_family"] = "stress"
        metadata["service"] = service if service else "all_services"
        metadata["target_rps"] = rps
        metadata["threads"] = threads
        return metadata

    match = re.match(r"hunt_(\d+)rps(?:_t(\d+))?\.csv$", filename)
    if match:
        rps, threads = match.groups()
        metadata["category"] = "thread_hunt"
        metadata["test_family"] = "thread_hunt"
        metadata["target_rps"] = rps
        metadata["threads"] = threads
        return metadata

    return metadata


def _float_or_none(value: str) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_limbo_metrics(abs_path: str) -> Dict[str, Optional[float]]:
    metrics: Dict[str, Optional[float]] = {
        "has_limbo_columns": "no",
        "row_count": 0,
        "active_rows": 0,
        "total_success": None,
        "total_failed": None,
        "total_dropped": None,
        "avg_response_time_sec": None,
        "throughput_req_s": None,
        "fail_rate_pct": None,
        "drop_rate_pct": None,
        "max_load_intensity": None,
        "duration_sec": None,
    }

    try:
        with open(abs_path, "r", newline="", encoding="utf-8") as handle:
            first_line = handle.readline().strip()
            if not first_line.startswith(LIMBO_PREFIX):
                return metrics
    except OSError:
        return metrics

    rows: List[Dict[str, float]] = []
    try:
        with open(abs_path, "r", newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            for row in reader:
                if len(row) < 7:
                    continue
                target_time = _float_or_none(row[0])
                load_intensity = _float_or_none(row[1])
                success = _float_or_none(row[2])
                failed = _float_or_none(row[3])
                dropped = _float_or_none(row[4])
                avg_rt = _float_or_none(row[5])
                if None in (target_time, load_intensity, success, failed, dropped, avg_rt):
                    continue
                rows.append(
                    {
                        "target_time": target_time,
                        "load_intensity": load_intensity,
                        "success": success,
                        "failed": failed,
                        "dropped": dropped,
                        "avg_response_time": avg_rt,
                    }
                )
    except OSError:
        return metrics

    metrics["has_limbo_columns"] = "yes"
    metrics["row_count"] = len(rows)
    active = [row for row in rows if row["load_intensity"] > 0]
    metrics["active_rows"] = len(active)
    if not active:
        return metrics

    total_success = sum(row["success"] for row in active)
    total_failed = sum(row["failed"] for row in active)
    total_dropped = sum(row["dropped"] for row in active)
    total_requests = total_success + total_failed + total_dropped

    weighted_rt_sum = sum(row["avg_response_time"] * row["success"] for row in active)
    avg_rt = weighted_rt_sum / total_success if total_success > 0 else 0.0

    duration = active[-1]["target_time"] - active[0]["target_time"] + 1.0
    throughput = total_success / duration if duration > 0 else 0.0
    fail_rate = (total_failed / total_requests * 100.0) if total_requests > 0 else 0.0
    drop_rate = (total_dropped / total_requests * 100.0) if total_requests > 0 else 0.0
    max_load = max(row["load_intensity"] for row in active)

    metrics["total_success"] = round(total_success, 3)
    metrics["total_failed"] = round(total_failed, 3)
    metrics["total_dropped"] = round(total_dropped, 3)
    metrics["avg_response_time_sec"] = round(avg_rt, 6)
    metrics["throughput_req_s"] = round(throughput, 6)
    metrics["fail_rate_pct"] = round(fail_rate, 6)
    metrics["drop_rate_pct"] = round(drop_rate, 6)
    metrics["max_load_intensity"] = round(max_load, 3)
    metrics["duration_sec"] = round(duration, 3)
    return metrics


def to_csv_value(value: Optional[float]) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def build_inventory() -> List[Dict[str, str]]:
    inventory: List[Dict[str, str]] = []

    for root, _, files in os.walk(DATA_ROOT):
        for file_name in files:
            if not file_name.lower().endswith(".csv"):
                continue

            abs_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(abs_path, DATA_ROOT)

            metadata = parse_filename_metadata(rel_path)
            metrics = parse_limbo_metrics(abs_path)

            row: Dict[str, str] = {
                "relative_path": rel_path.replace("\\", "/"),
                "category": metadata["category"] or "",
                "test_family": metadata["test_family"] or "",
                "cpu_level": metadata["cpu_level"] or "",
                "service": metadata["service"] or "",
                "intensity": metadata["intensity"] or "",
                "threads": metadata["threads"] or "",
                "target_rps": metadata["target_rps"] or "",
                "is_run_log": metadata["is_run_log"] or "no",
                "has_limbo_columns": metrics["has_limbo_columns"] or "no",
            }

            for metric_key in (
                "row_count",
                "active_rows",
                "total_success",
                "total_failed",
                "total_dropped",
                "avg_response_time_sec",
                "throughput_req_s",
                "fail_rate_pct",
                "drop_rate_pct",
                "max_load_intensity",
                "duration_sec",
            ):
                row[metric_key] = to_csv_value(metrics[metric_key])

            inventory.append(row)

    inventory.sort(key=lambda row: row["relative_path"])
    return inventory


def write_inventory_csv(inventory: List[Dict[str, str]]) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "all_csv_inventory.csv")
    if not inventory:
        with open(out_path, "w", newline="", encoding="utf-8") as handle:
            handle.write("")
        return out_path

    fieldnames = list(inventory[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(inventory)
    return out_path


def write_category_summary(inventory: List[Dict[str, str]]) -> str:
    out_path = os.path.join(OUTPUT_DIR, "category_summary.csv")
    grouped: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {
            "file_count": 0,
            "limbo_file_count": 0,
            "total_success": 0.0,
            "total_failed": 0.0,
            "total_dropped": 0.0,
            "avg_throughput_req_s": 0.0,
            "throughput_count": 0,
        }
    )

    for row in inventory:
        category = row["category"] or "uncategorized"
        bucket = grouped[category]
        bucket["file_count"] += 1
        if row["has_limbo_columns"] == "yes":
            bucket["limbo_file_count"] += 1

        for key in ("total_success", "total_failed", "total_dropped"):
            try:
                bucket[key] += float(row[key]) if row[key] else 0.0
            except ValueError:
                pass

        if row["throughput_req_s"]:
            try:
                bucket["avg_throughput_req_s"] += float(row["throughput_req_s"])
                bucket["throughput_count"] += 1
            except ValueError:
                pass

    fieldnames = [
        "category",
        "file_count",
        "limbo_file_count",
        "total_success",
        "total_failed",
        "total_dropped",
        "avg_throughput_req_s",
    ]
    rows_out: List[Dict[str, str]] = []
    for category in sorted(grouped):
        bucket = grouped[category]
        avg_tp = (
            bucket["avg_throughput_req_s"] / bucket["throughput_count"]
            if bucket["throughput_count"] > 0
            else 0.0
        )
        rows_out.append(
            {
                "category": category,
                "file_count": str(int(bucket["file_count"])),
                "limbo_file_count": str(int(bucket["limbo_file_count"])),
                "total_success": to_csv_value(bucket["total_success"]),
                "total_failed": to_csv_value(bucket["total_failed"]),
                "total_dropped": to_csv_value(bucket["total_dropped"]),
                "avg_throughput_req_s": to_csv_value(avg_tp),
            }
        )

    with open(out_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    return out_path


def write_rq1_summary(inventory: List[Dict[str, str]]) -> str:
    out_path = os.path.join(OUTPUT_DIR, "rq1_summary.csv")
    fieldnames = [
        "category",
        "cpu_level",
        "service",
        "intensity",
        "threads",
        "throughput_req_s",
        "avg_response_time_sec",
        "fail_rate_pct",
        "drop_rate_pct",
        "max_load_intensity",
        "relative_path",
    ]

    rows_out = []
    for row in inventory:
        if row["category"] not in {"rq1_service", "rq1_combined", "rq1_isolated"}:
            continue
        if row["has_limbo_columns"] != "yes":
            continue
        rows_out.append(
            {
                "category": row["category"],
                "cpu_level": row["cpu_level"],
                "service": row["service"],
                "intensity": row["intensity"],
                "threads": row["threads"],
                "throughput_req_s": row["throughput_req_s"],
                "avg_response_time_sec": row["avg_response_time_sec"],
                "fail_rate_pct": row["fail_rate_pct"],
                "drop_rate_pct": row["drop_rate_pct"],
                "max_load_intensity": row["max_load_intensity"],
                "relative_path": row["relative_path"],
            }
        )

    rows_out.sort(
        key=lambda r: (
            r["category"],
            r["cpu_level"],
            r["service"],
            r["intensity"],
            int(r["threads"]) if r["threads"].isdigit() else 0,
        )
    )

    with open(out_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    return out_path


def main() -> None:
    print(f"Scanning CSV files under: {DATA_ROOT}")
    inventory = build_inventory()
    print(f"Found {len(inventory)} CSV files")

    inventory_csv = write_inventory_csv(inventory)
    category_csv = write_category_summary(inventory)
    rq1_csv = write_rq1_summary(inventory)

    print("Wrote:")
    print(f"  {inventory_csv}")
    print(f"  {category_csv}")
    print(f"  {rq1_csv}")

    categories = defaultdict(int)
    for row in inventory:
        categories[row["category"]] += 1

    print("\nCategory counts:")
    for category, count in sorted(categories.items()):
        print(f"  {category:<18} {count}")


if __name__ == "__main__":
    main()
