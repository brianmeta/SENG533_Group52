import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os

def generate_throughput_report(csv_path, output_name=None, test_name="Load Test"):
    if not os.path.exists(csv_path):
        print(f"Error: Could not find file {csv_path}")
        return

               
    df = pd.read_csv(csv_path, skiprows=1)
    df.columns = ['Target Time', 'Load Intensity', 'Successful Transactions', 
                  'Failed Transactions', 'Dropped Transactions', 
                  'Avg Response Time', 'Final Batch Dispatch Time']

                                                                         
                                                                 
    failure_rows = df[df['Failed Transactions'] > 0]
    bottleneck_intensity = failure_rows['Load Intensity'].iloc[0] if not failure_rows.empty else None

                    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(f'Performance Saturation Analysis: {test_name}', fontsize=16)

                                                   
    ax1.plot(df['Load Intensity'], df['Successful Transactions'], color='blue', marker='o', markersize=3, label='Successful Req/s')
    ax1.set_title('Throughput vs. Load Intensity')
    ax1.set_xlabel('Load Intensity (Requests/s)')
    ax1.set_ylabel('Successful Transactions')
    ax1.grid(True, linestyle='--', alpha=0.7)
    
    if bottleneck_intensity:
        ax1.axvline(x=bottleneck_intensity, color='red', linestyle='--', 
                    label=f'Bottleneck (~{bottleneck_intensity} req/s)')
    ax1.legend()

                                                    
    ax2.plot(df['Target Time'], df['Successful Transactions'], color='green', label='Successful')
    ax2.plot(df['Target Time'], df['Failed Transactions'], color='red', label='Failed')
    ax2.set_title('System Status over Time')
    ax2.set_xlabel('Target Time (Seconds)')
    ax2.set_ylabel('Number of Transactions')
    ax2.grid(True, linestyle='--', alpha=0.7)
    ax2.legend()

                 
    if not output_name:
        base_name = os.path.splitext(csv_path)[0]
        output_name = f"{base_name}_graph.png"
        
    plt.tight_layout()
                                                 
    plt.subplots_adjust(top=0.9) 
    plt.savefig(output_name, dpi=300)
    print(f"Success! Graph saved as: {output_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Graph LIMBO load testing results.")
    parser.add_argument("csv_file", help="Path to the LIMBO output CSV file")
    parser.add_argument("--out", "-o", help="Name of the output PNG file", default=None)
    parser.add_argument("--name", "-n", help="Title to display on the graph", default="Load Test")
    
    args = parser.parse_args()
    generate_throughput_report(args.csv_file, args.out, args.name)
