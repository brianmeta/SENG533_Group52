import subprocess
import time

def capture_docker_stats(duration_seconds=120, interval=10, output_file="automated_stats.txt"):
    print(f"Starting Docker stats capture for {duration_seconds} seconds...")
    with open(output_file, "w") as f:
        for i in range(0, duration_seconds, interval):
            f.write(f"\n--- Timestamp: {i}s ---\n")
                                                                       
            result = subprocess.run(["docker", "stats", "--no-stream"], capture_output=True, text=True)
            f.write(result.stdout)
            print(f"Captured stats at {i}s")
            time.sleep(interval)
    print(f"Finished! Data saved to {output_file}")

if __name__ == "__main__":
                                                                        
    capture_docker_stats(output_file="stats_low.txt")
