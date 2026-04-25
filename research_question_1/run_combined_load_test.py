
import subprocess
import os
import time
import csv
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.path.join(SCRIPT_DIR, "examples", "httploadgenerator")
JAR = "httploadgenerator.jar"
OUTPUT_SUBDIR = "combined_test_results"

LUA_SCRIPT = "teastore_all_services.lua"

INTENSITIES = [
    {"name": "low",  "csv": "increasingLowIntensity.csv"},
    {"name": "med",  "csv": "increasingMedIntensity.csv"},
    {"name": "high", "csv": "increasingHighIntensity.csv"},
]

THREAD_COUNTS = [1, 5, 10, 25, 50, 100, 250]

LOADGEN_STARTUP_WAIT = 3
COOLDOWN_BETWEEN_TESTS = 5
REQUEST_TIMEOUT_MS = 10000
MAX_TEST_DURATION = 300


def run_test(arrival_csv, threads, output_file):
    loadgen = subprocess.Popen(
        ["java", "-jar", JAR, "loadgenerator"],
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
                "-l", LUA_SCRIPT,
                "-o", output_file,
                "-t", str(threads),
                "-u", str(REQUEST_TIMEOUT_MS),
            ],
            cwd=WORK_DIR,
            timeout=MAX_TEST_DURATION,
        )
        return "pass" if director.returncode == 0 else "fail"
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT after {MAX_TEST_DURATION}s - killing test")
        return "timeout"
    finally:
        loadgen.kill()
        try:
            loadgen.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def main():
    output_dir = os.path.join(WORK_DIR, OUTPUT_SUBDIR)
    os.makedirs(output_dir, exist_ok=True)

    log_path = os.path.join(output_dir, "_run_log.csv")
    log_exists = os.path.exists(log_path)
    log_file = open(log_path, "a", newline="")
    log_writer = csv.writer(log_file)
    if not log_exists:
        log_writer.writerow([
            "timestamp", "intensity", "threads",
            "status", "elapsed_seconds", "output_file",
        ])

    total = len(INTENSITIES) * len(THREAD_COUNTS)
    current = 0
    passed = 0
    failed = 0
    skipped = 0
    start_time = time.time()

    print("=" * 60)
    print("  TeaStore COMBINED Load Test (all services at once)")
    print(f"  Lua script:  {LUA_SCRIPT}")
    print(f"  Intensities: {', '.join(i['name'] for i in INTENSITIES)}")
    print(f"  Threads:     {', '.join(str(t) for t in THREAD_COUNTS)}")
    print(f"  Total tests: {total}")
    print(f"  Max per test: {MAX_TEST_DURATION}s")
    print(f"  Output dir:  {output_dir}")
    print(f"  Run log:     {log_path}")
    print("=" * 60)
    print()

    try:
        for intensity in INTENSITIES:
            for threads in THREAD_COUNTS:
                current += 1
                output_file = os.path.join(
                    OUTPUT_SUBDIR,
                    f"combined_{intensity['name']}_t{threads}.csv",
                )
                abs_output = os.path.join(WORK_DIR, output_file)

                if os.path.exists(abs_output) and os.path.getsize(abs_output) > 0:
                    skipped += 1
                    print(
                        f"[{current}/{total}] "
                        f"all_services | {intensity['name']} | {threads} threads "
                        f"-> SKIPPED (file exists)"
                    )
                    continue

                print("-" * 60)
                print(
                    f"[{current}/{total}] "
                    f"all_services | {intensity['name']} intensity | {threads} threads"
                )
                print(f"  Output: {output_file}")
                print("-" * 60)

                test_start = time.time()
                status = run_test(intensity["csv"], threads, output_file)
                elapsed = time.time() - test_start

                log_writer.writerow([
                    datetime.now().isoformat(),
                    intensity["name"],
                    threads,
                    status,
                    round(elapsed, 1),
                    output_file,
                ])
                log_file.flush()

                if status == "pass":
                    passed += 1
                    print(f"  DONE in {elapsed:.1f}s")
                elif status == "timeout":
                    failed += 1
                    print(f"  TIMEOUT after {elapsed:.1f}s")
                else:
                    failed += 1
                    print(f"  FAILED after {elapsed:.1f}s")

                if current < total:
                    print(f"  Cooldown {COOLDOWN_BETWEEN_TESTS}s...")
                    time.sleep(COOLDOWN_BETWEEN_TESTS)

                print()
    finally:
        log_file.close()

    total_elapsed = time.time() - start_time

    print("=" * 60)
    print(f"  All combined tests complete!")
    print(f"  Passed: {passed}  |  Failed: {failed}  |  Skipped: {skipped}  |  Total: {total}")
    print(f"  Total time: {total_elapsed / 60:.1f} minutes")
    print(f"  Results in: {output_dir}")
    print(f"  Run log:    {log_path}")
    print("=" * 60)
    print()
    print("Output files:")
    for f in sorted(os.listdir(output_dir)):
        if f.endswith(".csv"):
            print(f"  {f}")


if __name__ == "__main__":
    main()
