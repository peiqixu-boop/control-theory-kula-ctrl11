"""Recheck Week 8 evidence without changing the nominal baseline.

Reads archived CSVs in memory if ordinary CSVs are absent. Writes only to a
new output directory, after all checks succeed. Run from any working directory.
"""
from pathlib import Path
import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import platform
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
import numpy as np
import scipy
from src.model import tuning_rules, simulate, metrics, exact_cancelled_step

BASELINE_REVISION = 'b513f7b48265af0e214001b3b006d5b53b33560b'
METRICS = ('IAE', 'ITAE', 'ISE', 'ITSE')


def read_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_baseline(name):
    folder = ROOT / 'data/generated'
    archive = folder / 'archive'
    entry = json.loads((archive / 'manifest.json').read_text())[name]
    path = folder / f'{name}.csv'
    if path.exists():
        raw = path.read_bytes()
        source = 'saved CSV'
    else:
        chunks = []
        for index, part in enumerate(entry['parts'], 1):
            expected = f'{name}.csv.gz.part{index:03d}'
            if part['file'] != expected:
                raise ValueError(f'Unexpected archive part: {part["file"]}')
            chunk = (archive / expected).read_bytes()
            if sha256(chunk) != part['sha256']:
                raise ValueError(f'Archive checksum mismatch: {expected}')
            chunks.append(chunk)
        raw = gzip.decompress(b''.join(chunks))
        source = 'archive decoded in memory'
    if len(raw) != entry['bytes'] or sha256(raw) != entry['sha256']:
        raise ValueError(f'Baseline CSV checksum mismatch: {name}')
    data = np.loadtxt(io.BytesIO(raw), delimiter=',', skiprows=1)
    if data.shape != (100001, 5) or not np.isfinite(data).all():
        raise ValueError(f'Invalid baseline dimensions or values: {name}')
    np.testing.assert_allclose(data[:, 0], np.arange(100001) * .001, rtol=0, atol=1e-12)
    np.testing.assert_array_equal(data[:, 1], 1.0)
    np.testing.assert_allclose(data[:, 3], data[:, 1] - data[:, 2], rtol=0, atol=1e-12)
    return data, source, entry['sha256']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', default='results/week8',
                        help='New directory, relative to repository root unless absolute.')
    args = parser.parse_args()
    out = Path(args.output_dir)
    if not out.is_absolute():
        out = ROOT / out
    out = out.resolve()
    if out.exists():
        raise FileExistsError(f'Output already exists: {out}. Choose a new --output-dir.')
    config = json.loads((ROOT / 'config/experiment.json').read_text())
    expected = {'gain': 2.0, 'time_constant_s': 4.0, 'delay_s': 2.0}
    if (config['plant'] != expected or config['step_amplitude'] != 1.0
            or config['primary_step_s'] != .001 or config['primary_horizon_s'] != 100.0
            or config['sensitivity_factors'] != [.8, 1.0, 1.2]
            or config['sensitivity_step_s'] != .002):
        raise ValueError('This verification is specific to the frozen Week 8 experiment.')
    inputs = ['src/model.py', 'tests/test_model.py', 'config/experiment.json',
              'data/reference/table1.csv', 'data/generated/archive/manifest.json',
              'results/metrics.csv', 'results/sensitivity.csv', 'tools/verify_week8.py']
    report = {
        'utc_verified': datetime.now(timezone.utc).isoformat(),
        'baseline_source_revision': BASELINE_REVISION,
        'environment': {'python': platform.python_version(), 'numpy': np.__version__,
                        'scipy': scipy.__version__, 'platform': platform.system()},
        'input_sha256': {p: sha256((ROOT / p).read_bytes()) for p in inputs},
        'numeric_comparison_absolute_tolerance': 1e-8,
        'baseline': {}, 'sensitivity': {},
        'assumptions': 'Unit step; zero history; nominal explicit-delay PI loop. '
                       'Signed moment bounds require stability and convergent moments. '
                       'Sampled signs and finite uncertainty grids are not proofs.'}
    logs = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
    tests = unittest.TextTestRunner(stream=logs, verbosity=2).run(suite)
    if not tests.wasSuccessful() or tests.testsRun < 4:
        raise RuntimeError(logs.getvalue())
    report['scientific_tests_passed'] = tests.testsRun
    saved = {r['controller']: r for r in read_rows(ROOT / 'results/metrics.csv')}
    controllers = tuning_rules(2, 4, 2)
    for controller in controllers:
        data, source, digest = load_baseline(controller.name)
        rerun = simulate(2, 4, 2, controller, .001, 100)
        np.testing.assert_allclose(rerun, data, rtol=0, atol=1e-10)
        measured = metrics(rerun)
        for key, value in measured.items():
            np.testing.assert_allclose(value, float(saved[controller.name][key]), rtol=0, atol=1e-8)
        item = {'rows': len(data), 'input': source, 'csv_sha256': digest,
                'exact_array_match': bool(np.array_equal(rerun, data)),
                'max_absolute_data_difference': float(np.max(abs(rerun-data))),
                'metrics': measured}
        if controller.name != 'chr':
            mask = data[:, 0] <= 20
            exact = exact_cancelled_step(data[mask, 0], 2*controller.kp/4, 2)
            error = float(np.max(abs(rerun[mask, 2]-exact)))
            if error >= 1e-6:
                raise ValueError('Independent analytical response check failed.')
            item['exact_solution_max_output_error_0_20s'] = error
        report['baseline'][controller.name] = item

    chr_controller = controllers[2]
    reference = next(r for r in read_rows(ROOT / 'data/reference/table1.csv') if r['controller']=='chr')
    a = chr_controller.ti/(2*chr_controller.kp)
    weighted = a*(a+chr_controller.ti-4-2)
    report['chr_signed_moments_and_absolute_metric_lower_bounds'] = {'IAE': a, 'ITAE': weighted}
    horizons = []
    for step in (.001, .0005):
        data = simulate(2, 4, 2, chr_controller, step, 200)
        for end in (30, 100, 200):
            subset = data[data[:, 0] <= end]
            measured = metrics(subset)
            t, error = subset[:, 0], subset[:, 3]
            signed = float(np.trapezoid(error, t))
            signed_weighted = float(np.trapezoid(t*error, t))
            row = {'step_s': step, 'horizon_s': end, **measured,
                   'minimum_sampled_error': float(error.min()),
                   'signed_integral_residual': signed-a,
                   'signed_time_weighted_residual': signed_weighted-weighted}
            for key in METRICS:
                row[key+'_paper'] = float(reference[key])
                row[key+'_difference_pct'] = 100*(measured[key]/float(reference[key])-1)
            horizons.append(row)
        if abs(horizons[-1]['signed_integral_residual']) >= 1e-6 or abs(horizons[-1]['signed_time_weighted_residual']) >= 1e-5:
            raise ValueError('CHR 200 s moment check failed.')
    coarse = {r['horizon_s']: r for r in horizons if r['step_s']==.001}
    tails = [{'metric': key, 'value_30s': coarse[30][key], 'value_100s': coarse[100][key],
              'tail_30_100s': coarse[100][key]-coarse[30][key]} for key in METRICS]
    sensitivity = read_rows(ROOT / 'results/sensitivity.csv')
    expected_cases = {(c.name, tf, df) for c in controllers for tf in (.8,1.,1.2) for df in (.8,1.,1.2)}
    actual_cases = {(r['controller'], float(r['tau_factor']), float(r['delay_factor'])) for r in sensitivity}
    if len(sensitivity)!=27 or actual_cases!=expected_cases:
        raise ValueError('Expected exactly 27 distinct sensitivity cases.')
    rechecks = []
    for controller in controllers:
        group = []
        for old in [r for r in sensitivity if r['controller']==controller.name]:
            tf, df = float(old['tau_factor']), float(old['delay_factor'])
            measured = metrics(simulate(2, 4*tf, 2*df, controller, .002, 100))
            diff = max(abs(measured[k]-float(old[k])) for k in measured)
            if not np.isfinite(list(measured.values())).all() or diff>=1e-8:
                raise ValueError('Sensitivity reproduction check failed.')
            row = {'controller': controller.name, 'tau_factor': tf, 'delay_factor': df,
                   'max_metric_difference_from_saved': diff, **measured}
            group.append(row); rechecks.append(row)
        worst = max(group, key=lambda r:r['overshoot_pct'])
        fine = metrics(simulate(2,4*worst['tau_factor'],2*worst['delay_factor'],controller,.001,100))
        report['sensitivity'][controller.name] = {
            'cases': len(group), 'max_metric_difference': max(r['max_metric_difference_from_saved'] for r in group),
            'max_overshoot_pct': worst['overshoot_pct'], 'checked_tau_factor': worst['tau_factor'],
            'checked_delay_factor': worst['delay_factor'], 'fine_step_s': .001,
            'fine_overshoot_pct': fine['overshoot_pct'],
            'overshoot_refinement_difference_percentage_points': fine['overshoot_pct']-worst['overshoot_pct']}
    for p, digest in report['input_sha256'].items():
        if sha256((ROOT / p).read_bytes()) != digest:
            raise RuntimeError(f'Input changed during verification: {p}')
    report['all_checks_passed'] = True
    out.mkdir(parents=True, exist_ok=False)
    for filename, records in [('chr_horizon_comparison.csv', horizons), ('chr_tail_contributions.csv', tails), ('sensitivity_recheck.csv', rechecks)]:
        with (out / filename).open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader(); writer.writerows(records)
    (out/'verification.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (out/'tests.log').write_text(logs.getvalue(),encoding='utf-8')
    print(json.dumps({'all_checks_passed':True,'baseline_controllers':3,'scientific_tests':tests.testsRun,'sensitivity_cases':len(rechecks),'chr_horizon_cases':len(horizons),'output_directory':str(out)}))


if __name__ == '__main__':
    main()
