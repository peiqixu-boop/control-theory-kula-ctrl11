"""Check nominal CHR signed moments and finite integration horizons.

Run from any directory: python tools/check_chr_integrals.py
This diagnostic does not overwrite the primary 100 s results.
"""
from pathlib import Path
import csv
import hashlib
import json
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import scipy
from src.model import metrics, simulate, tuning_rules


def main():
    config = json.loads((ROOT / 'config/experiment.json').read_text())
    plant = config['plant']
    gain, tau, delay = (plant[k] for k in ('gain', 'time_constant_s', 'delay_s'))
    controller = next(c for c in tuning_rules(gain, tau, delay) if c.name == 'chr')
    if (gain, tau, delay, config['step_amplitude']) != (2.0, 4.0, 2.0, 1.0):
        raise ValueError('This diagnostic compares the nominal Example 1 unit step only.')
    with (ROOT / 'data/reference/table1.csv').open(newline='') as f:
        reference = next(row for row in csv.DictReader(f) if row['controller'] == 'chr')
    a = controller.ti / (gain * controller.kp)
    weighted = a * (a + controller.ti - tau - delay)
    runs = []
    for step in (0.001, 0.0005):
        data = simulate(gain, tau, delay, controller, step, 200.0)
        for horizon in (30.0, 100.0, 200.0):
            sample = data[data[:, 0] <= horizon]
            t, e = sample[:, 0], sample[:, 3]
            measured = metrics(sample)
            signed = float(np.trapezoid(e, t))
            signed_weighted = float(np.trapezoid(t * e, t))
            runs.append({
                'step_s': step, 'horizon_s': horizon,
                'minimum_sampled_error': float(e.min()),
                'signed_error_integral': signed,
                'signed_time_weighted_integral': signed_weighted,
                'signed_integral_residual': signed - a,
                'signed_time_weighted_residual': signed_weighted - weighted,
                'metrics': measured,
                'difference_from_paper_pct': {
                    key: 100 * (measured[key] / float(reference[key]) - 1)
                    for key in ('IAE', 'ITAE', 'ISE', 'ITSE')},
            })
        # At 200 s, step refinement should leave only small numerical residuals.
        assert abs(runs[-1]['signed_integral_residual']) < 1e-6
        assert abs(runs[-1]['signed_time_weighted_residual']) < 1e-5
    report = {
        'environment': {'python': platform.python_version(),
                        'numpy': np.__version__, 'scipy': scipy.__version__},
        'input_sha256': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                         for path in ('src/model.py', 'config/experiment.json',
                                      'data/reference/table1.csv', 'tools/check_chr_integrals.py')},
        'analytic_signed_error_integral': a,
        'analytic_signed_time_weighted_integral': weighted,
        'infinite_horizon_IAE_lower_bound': abs(a),
        'infinite_horizon_ITAE_lower_bound': abs(weighted),
        'assumptions': 'Stable nominal unit-step feedback with zero history and convergent moments. '
                       'The lower bounds equal IAE/ITAE if error is nonnegative for all time; '
                       'sampled sign checks are not a proof of that condition.',
        'runs': runs,
    }
    target = ROOT / 'results/chr_integral_diagnostic.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
