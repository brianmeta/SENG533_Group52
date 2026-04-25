# TeaStore Load-Test Report

- Generated at: `2026-04-23T06:12:55`
- Total CSV files cataloged: **276**
- LIMBO metric CSV files: **257**
- Aggregate successful transactions: **7,501,312.00**
- Aggregate failed transactions: **111,436.00**
- Aggregate dropped transactions: **6,065,008.00**

## Included Artifacts

- `catalog/all_csv_inventory.csv`: full per-file metadata + metrics
- `catalog/category_summary.csv`: category-level counts and aggregate stats
- `catalog/rq1_summary.csv`: flattened RQ1-oriented metrics for analysis
- `graphs/*.png`: generated visualizations

## Category Breakdown

| Category | File Count | LIMBO Files | Avg Throughput (req/s) |
|---|---:|---:|---:|
| intensity_profile | 3 | 0 | 0.00 |
| rq1_combined | 21 | 21 | 95.53 |
| rq1_isolated | 10 | 5 | 288.21 |
| rq1_service | 210 | 210 | 242.09 |
| run_log | 3 | 0 | 0.00 |
| stress | 23 | 19 | 1,320.38 |
| thread_hunt | 1 | 0 | 0.00 |
| uncategorized | 5 | 2 | 2.09 |

## Top 5 RQ1 Throughput Results

| Service | Intensity | Threads | Throughput (req/s) | Avg RT (s) | Fail % | Drop % |
|---|---|---:|---:|---:|---:|---:|
| image | high | 100 | 1,008.00 | 0.04 | 0.00 | 0.00 |
| recommender | high | 250 | 1,008.00 | 0.04 | 0.00 | 0.00 |
| recommender | high | 100 | 1,008.00 | 0.04 | 0.00 | 0.00 |
| image | high | 100 | 1,007.99 | 0.04 | 0.00 | 0.00 |
| image | high | 250 | 1,007.86 | 0.04 | 0.00 | 0.00 |

## Reproduction

```bash
python categorize_load_test_data.py
python plot_load_test_graphs.py
python build_load_test_report.py
```
