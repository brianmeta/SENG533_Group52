
import subprocess
import os
import time
import csv
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.path.join(SCRIPT_DIR, "examples", "httploadgenerator")
JAR = "httploadgenerator.jar"
OUTPUT_SUBDIR = "stress_test_results"
PROFILE_SUBDIR = "stress_test_results"

SERVICES = [
    {"name": "persistence",  "lua": "teastore_persistence.lua"},
    {"name": "image",        "lua": "teastore_image.lua"},
]

STRESS_PROFILES = [
    {"name": "1000rps", "target": 1000},
    {"name": "2000rps", "target": 2000},
    {"name": "5000rps", "target": 5000},
]

THREAD_COUNTS = [250, 500]

RAMP_SECONDS = 5
HOLD_SECONDS = 115

LOADGEN_STARTUP_WAIT = 3
COOLDOWN_BETWEEN_TESTS = 5
REQUEST_TIMEOUT_MS = 10000
MAX_TEST_DURATION = 360

JVM_FLAGS = ["-Xss256k", "-Xmx512m"]


def generate_stress_csv(target_rate, filepath):
    rows = []
    t = 0.5

    while t <= RAMP_SECONDS:
        rate = (target_rate / RAMP_SECONDS) * t
        rows.append((t, min(rate, target_rate)))
        t += 1.0

    total_duration = RAMP_SECONDS + HOLD_SECONDS
    while t <= total_duration:
        rows.append((t, target_rate))
        t += 1.0

    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)


def run_test(lua_file, arrival_csv, threads, output_file):
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
            "timestamp", "service", "profile", "threads",
            "status", "elapsed_seconds", "output_file",
        ])

    profile_files = {}
    for profile in STRESS_PROFILES:
        rel_path = os.path.join(PROFILE_SUBDIR, f"stress_{profile['name']}.csv")
        abs_path = os.path.join(WORK_DIR, rel_path)
        generate_stress_csv(profile["target"], abs_path)
        profile_files[profile["name"]] = rel_path
        print(f"Generated profile: {rel_path} "
              f"(constant {profile['target']} req/s for {HOLD_SECONDS}s)")

    total = len(SERVICES) * len(STRESS_PROFILES) * len(THREAD_COUNTS)
    current = 0
    passed = 0
    failed = 0
    skipped = 0
    start_time = time.time()

    print()
    print("=" * 60)
    print("  TeaStore STRESS Test — Breaking Point Finder")
    print(f"  Services:    {', '.join(s['name'] for s in SERVICES)}")
    print(f"  Rates:       {', '.join(p['name'] for p in STRESS_PROFILES)}")
    print(f"  Threads:     {', '.join(str(t) for t in THREAD_COUNTS)}")
    print(f"  Total tests: {total}")
    print(f"  Max per test: {MAX_TEST_DURATION}s")
    print(f"  Output dir:  {output_dir}")
    print(f"  Run log:     {log_path}")
    print("=" * 60)
    print()

    try:
        for service in SERVICES:
            for profile in STRESS_PROFILES:
                for threads in THREAD_COUNTS:
                    current += 1
                    arrival_csv = profile_files[profile["name"]]
                    output_file = f"stress_{service['name']}_{profile['name']}_t{threads}.csv"
                    abs_output = os.path.join(output_dir, output_file)

                    if os.path.exists(abs_output) and os.path.getsize(abs_output) > 0:
                        skipped += 1
                        print(
                            f"[{current}/{total}] "
                            f"{service['name']} | {profile['name']} | {threads} threads "
                            f"-> SKIPPED (file exists)"
                        )
                        continue

                    print("-" * 60)
                    print(
                        f"[{current}/{total}] "
                        f"{service['name']} | {profile['name']} "
                        f"({profile['target']} req/s) | {threads} threads"
                    )
                    print(f"  Output: {output_file}")
                    print("-" * 60)

                    test_start = time.time()
                    status = run_test(service["lua"], arrival_csv, threads, output_file)
                    elapsed = time.time() - test_start

                    log_writer.writerow([
                        datetime.now().isoformat(),
                        service["name"],
                        profile["name"],
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
    print(f"  All stress tests complete!")
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
