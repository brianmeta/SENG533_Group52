
import csv
import os
import subprocess
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.path.join(SCRIPT_DIR, "examples", "httploadgenerator")
JAR = "httploadgenerator.jar"
OUTPUT_SUBDIR = "thread_hunt_results"

SERVICES = [
    {"name": "persistence", "lua": "teastore_persistence.lua"},
    {"name": "image", "lua": "teastore_image.lua"},
]

TARGET_RPS = 2000
THREAD_START = 250
THREAD_STEP = 10
THREAD_MAX = 520

RAMP_SECONDS = 4
SEGMENT_HOLD_SECONDS = 18

LOADGEN_STARTUP_WAIT = 3
COOLDOWN_BETWEEN_SEGMENTS = 3
REQUEST_TIMEOUT_MS = 10000
SEGMENT_TIMEOUT = RAMP_SECONDS + SEGMENT_HOLD_SECONDS + 90

JVM_FLAGS = ["-Xss256k", "-Xmx512m"]

STOP_DROP_PCT = 10.0
STOP_FAIL_PCT = 2.0


def generate_stress_csv(target_rate, filepath, ramp_seconds, hold_seconds):
    rows = []
    t = 0.5
    while t <= ramp_seconds:
        rate = (target_rate / ramp_seconds) * t
        rows.append((t, min(rate, target_rate)))
        t += 1.0
    end_t = ramp_seconds + hold_seconds
    while t <= end_t:
        rows.append((t, target_rate))
        t += 1.0
    with open(filepath, "w", newline="") as f:
        w = csv.writer(f)
        for row in rows:
            w.writerow(row)


def parse_limbo_csv(filepath):
    rows = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            next(reader, None)
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
                    })
                except (ValueError, IndexError):
                    continue
    except OSError:
        pass
    return rows


def summarize_segment(rows):
    active = [r for r in rows if r["load_intensity"] > 0]
    if not active:
        return None
    total_success = sum(r["success"] for r in active)
    total_failed = sum(r["failed"] for r in active)
    total_dropped = sum(r["dropped"] for r in active)
    total_req = total_success + total_failed + total_dropped
    weighted_rt = sum(r["avg_response_time"] * r["success"] for r in active)
    avg_rt = weighted_rt / total_success if total_success > 0 else 0.0
    duration = active[-1]["target_time"] - active[0]["target_time"] + 1
    throughput = total_success / duration if duration > 0 else 0.0
    fail_pct = (total_failed / total_req * 100) if total_req > 0 else 0.0
    drop_pct = (total_dropped / total_req * 100) if total_req > 0 else 0.0
    return {
        "total_success": total_success,
        "total_failed": total_failed,
        "total_dropped": total_dropped,
        "avg_response_time": avg_rt,
        "throughput": throughput,
        "fail_pct": fail_pct,
        "drop_pct": drop_pct,
    }


def kill_stale_java():
    subprocess.run(
        ["taskkill", "/F", "/IM", "java.exe"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)


def run_segment(lua_file, arrival_csv, threads, output_file):
    loadgen = subprocess.Popen(
        ["java"] + JVM_FLAGS + ["-jar", JAR, "loadgenerator"],
        cwd=WORK_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(LOADGEN_STARTUP_WAIT)
    try:
        director = subprocess.run(
            [
                "java", "-jar", JAR, "director",
                "-s", "127.0.0.1",
                "-a", arrival_csv,
                "-l", lua_file,
                "-o", output_file,
                "-t", str(threads),
                "-u", str(REQUEST_TIMEOUT_MS),
            ],
            cwd=WORK_DIR,
            timeout=SEGMENT_TIMEOUT,
        )
        return "pass" if director.returncode == 0 else "fail"
    except subprocess.TimeoutExpired:
        return "timeout"
    finally:
        loadgen.kill()
        try:
            loadgen.wait(timeout=8)
        except subprocess.TimeoutExpired:
            kill_stale_java()


def main():
    kill_stale_java()

    output_dir = os.path.join(WORK_DIR, OUTPUT_SUBDIR)
    os.makedirs(output_dir, exist_ok=True)

    profile_name = f"hunt_{TARGET_RPS}rps.csv"
    profile_rel = profile_name
    profile_abs = os.path.join(output_dir, profile_name)
    generate_stress_csv(TARGET_RPS, profile_abs, RAMP_SECONDS, SEGMENT_HOLD_SECONDS)
    print(f"Generated profile: {OUTPUT_SUBDIR}/{profile_name} "
          f"({TARGET_RPS} req/s, hold {SEGMENT_HOLD_SECONDS}s + ramp {RAMP_SECONDS}s)")

    log_path = os.path.join(output_dir, "thread_hunt_log.csv")
    log_exists = os.path.exists(log_path)
    log_file = open(log_path, "a", newline="", encoding="utf-8")
    log_writer = csv.writer(log_file)
    if not log_exists:
        log_writer.writerow([
            "timestamp", "service", "target_rps", "threads", "status", "elapsed_seconds",
            "total_success", "total_failed", "total_dropped",
            "avg_response_time", "throughput_rps", "fail_pct", "drop_pct",
            "output_file", "stop_reason",
        ])

    print()
    print("=" * 60)
    print("  TeaStore thread hunt (stepping threads each segment)")
    print(f"  Services:   {', '.join(s['name'] for s in SERVICES)}")
    print(f"  Target RPS: {TARGET_RPS}")
    print(f"  Threads:    {THREAD_START} .. {THREAD_MAX} step {THREAD_STEP}")
    print(f"  Stop if:    director fail/timeout, or drop>={STOP_DROP_PCT}%, fail>={STOP_FAIL_PCT}%")
    print(f"  Output:     {output_dir}")
    print(f"  Summary:    {log_path}")
    print("=" * 60)
    print()

    try:
        for service in SERVICES:
            threads = THREAD_START
            while threads <= THREAD_MAX:
                out_name = f"hunt_{service['name']}_r{TARGET_RPS}_t{threads}.csv"
                abs_out = os.path.join(output_dir, out_name)

                print("-" * 60)
                print(f"{service['name']} | {TARGET_RPS} req/s | {threads} threads")
                print(f"  Raw log: {out_name}")
                print("-" * 60)

                t0 = time.time()
                status = run_segment(service["lua"], profile_rel, threads, out_name)
                elapsed = time.time() - t0

                stats = summarize_segment(parse_limbo_csv(abs_out))
                stop_reason = ""

                if stats is None:
                    fail_pct = drop_pct = 0.0
                    ok = fl = dr = 0
                    avg_rt = thr = 0.0
                else:
                    fail_pct = stats["fail_pct"]
                    drop_pct = stats["drop_pct"]
                    ok = stats["total_success"]
                    fl = stats["total_failed"]
                    dr = stats["total_dropped"]
                    avg_rt = round(stats["avg_response_time"], 4)
                    thr = round(stats["throughput"], 2)

                if status != "pass":
                    stop_reason = status
                elif stats is None:
                    stop_reason = "no_csv_stats"
                elif drop_pct >= STOP_DROP_PCT:
                    stop_reason = f"drop_pct>={STOP_DROP_PCT}"
                elif fail_pct >= STOP_FAIL_PCT:
                    stop_reason = f"fail_pct>={STOP_FAIL_PCT}"

                log_writer.writerow([
                    datetime.now().isoformat(),
                    service["name"],
                    TARGET_RPS,
                    threads,
                    status,
                    round(elapsed, 1),
                    ok, fl, dr, avg_rt, thr,
                    round(fail_pct, 3), round(drop_pct, 3),
                    out_name,
                    stop_reason,
                ])
                log_file.flush()

                if status == "pass":
                    print(f"  DONE in {elapsed:.1f}s  "
                          f"ok={ok} fail={fl} drop={dr}  "
                          f"avgRT={avg_rt}  thr={thr} r/s")
                elif status == "timeout":
                    print(f"  TIMEOUT after {elapsed:.1f}s")
                else:
                    print(f"  FAILED after {elapsed:.1f}s")

                if stop_reason:
                    print(f"  Stop: {stop_reason}")
                    print()
                    break

                print(f"  Cooldown {COOLDOWN_BETWEEN_SEGMENTS}s...")
                time.sleep(COOLDOWN_BETWEEN_SEGMENTS)
                threads += THREAD_STEP
                if threads > THREAD_MAX:
                    print(f"  Finished ladder (last threads={threads - THREAD_STEP}, max={THREAD_MAX})")
                    print()
                    break
                print()
    finally:
        log_file.close()

    print("=" * 60)
    print("  Thread hunt finished. See thread_hunt_log.csv and hunt_*.csv")
    print("=" * 60)


if __name__ == "__main__":
    main()
