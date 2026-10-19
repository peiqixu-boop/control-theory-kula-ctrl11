"""Demonstrate loading and processing the existing exported data without simulation."""
from pathlib import Path
from src.analysis import analyse_saved

if __name__=='__main__':
    metrics,comparison,checks=analyse_saved(Path(__file__).resolve().parent)
    for check in checks:
        print(f"Loaded {check['controller']}: {check['rows']} rows; "
              f"{check['nonfinite_values']} nonfinite values; "
              f"time [{check['time_start_s']}, {check['time_end_s']}] s")
    print(f'Recomputed {len(metrics)} controller summaries and {len(comparison)} published-value comparisons.')
