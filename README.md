# Kula 2024 PI controller replication

Independent Python implementation of Example 1 from K. S. Kula (2024), *Tuning a PI/PID Controller with Direct Synthesis to Obtain a Non-Oscillatory Response of Time-Delayed Systems*, Applied Sciences 14(13), 5468. [Paper](https://doi.org/10.3390/app14135468).

The code computes the PI gains from the published rules, simulates the delayed plant, exports and reloads simulation data, compares four integral metrics with Table 1, and runs numerical and parameter-sensitivity checks.

## Install and run

The recorded and rechecked environment is **CPython 3.12.14, 64-bit Windows**, with the exact versions in `requirements.txt`. Use Python 3.12 to reproduce that environment.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run_replication.py
.venv\Scripts\python -m unittest discover -s tests -v
```

macOS/Linux with Python 3.12 installed:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run_replication.py
.venv/bin/python -m unittest discover -s tests -v
```

The commands below use `python` to mean the interpreter in this environment. Dependency installation needs network access; simulations do not need MATLAB, a GPU, an external dataset or network downloads. The main script resolves data paths relative to its own location and regenerates results and figures.

Python 3.12 is the validated choice, not a claim that SciPy excludes Python 3.14. [SciPy 1.17.0 supports Python 3.11–3.14](https://docs.scipy.org/doc/scipy/release/1.17.0-notes.html), and [PyPI provides a CPython 3.14 Windows x86-64 wheel](https://pypi.org/project/scipy/1.17.0/#files), including `scipy-1.17.0-cp314-cp314-win_amd64.whl`. The full pipeline has not been validated here on Python 3.14. For installation errors, check the active interpreter, architecture, pip version and package index before changing the pinned numerical dependencies.

## Model and scope

The nominal plant is `G(s) = 2 exp(-2s) / (4s + 1)`, with `C(s) = Kp (1 + 1/(Ti s))`.

| Controller | Kp | Ti (s) |
|---|---:|---:|
| Proposed critical | 0.36787944117144233 | 4.0 |
| Proposed faster | 0.4598493014643029 | 4.0 |
| CHR | 0.35 | 4.8 |

Gains are computed in `src/model.py`; printed rounded values are used only in a separate sensitivity check. The baseline uses a unit step, zero states and input history, a 0.001 s step and a 100 s horizon. RK4 advances the plant and PI states using interpolated delayed input history. The delay must be a positive integer multiple of the time step.

The selected targets are the two controlled responses in Figure 2, the critical/CHR comparison in Figure 8, and the corresponding Table 1 rows. The additional desired reference curve in Figure 2 is outside scope. Original trajectories have not been digitized.

## Results

| Controller | 2% settling time (s) | Overshoot (%) | ITAE at 100 s | Paper ITAE |
|---|---:|---:|---:|---:|
| Critical | 13.063 | 0.000 | 18.6831 | 18.654 |
| Faster | 8.178 | 1.798 | 12.1202 | 12.198 |
| CHR | 24.356 | 0.000 | 38.7915 | 36.45 |

All eight proposed-controller integral values differ from Table 1 by less than 0.638%. The CHR 100 s ITAE is 6.424% above the paper value.

**CHR interpretation:** the stable nominal model has an exact signed time-weighted error integral of 38.79183673, which is also a lower bound for its infinite-horizon ITAE. A 200 s rerun gives ITAE 38.79183667; halving the step gives 38.79183672. Thus 36.45 is incompatible with the infinite-horizon ITAE of this same model and setup. At 30 s, IAE and ITAE are within 0.05% of the paper, supporting a shorter-window explanation. The author's actual integration settings remain unconfirmed. See [validation and CHR analysis](docs/validation.md) for the assumptions, derivation and all four metrics.

Primary outputs:

- [Baseline response plots](results/figures/baseline_responses.png)
- [Computed controller gains](results/derived_parameters.csv)
- [Metrics](results/metrics.csv) and [Table 1 comparison](results/comparison_table1.csv)
- [Data checks](results/data_checks.json) and [execution logs](results/logs/run.log)
- [Numerical validation](docs/validation.md) and [method derivation](docs/method.md)
- [Model assumptions and deviations](docs/deviations.md)

## Week 8 progress

The Week 8 verification re-executes the frozen experiment without changing the
100 s baseline. All three saved trajectories match exactly in the recorded
environment, four scientific tests pass, and all 27 fixed-gain plant-mismatch
cases reproduce the saved metrics. CHR checks cover 30, 100 and 200 s with
steps of 0.001 and 0.0005 s; a separate table records the 30–100 s tail.

- [Stage findings and remaining work](docs/week8_progress.md)
- [Verification results and environment](results/week8/verification.json)
- [CHR horizon comparison](results/week8/chr_horizon_comparison.csv)
- [CHR tail contributions](results/week8/chr_tail_contributions.csv)
- [27-case sensitivity recheck](results/week8/sensitivity_recheck.csv)
- [Scientific test log](results/week8/tests.log)

To repeat these checks into a new directory:

```bash
python tools/verify_week8.py --output-dir results/week8_rerun
```

Relative output paths are resolved from the repository root. The destination
must not exist; choose another directory for subsequent runs. Missing baseline
CSVs are decoded from the checked archive in memory, without restoring or
overwriting the original data. The command requires only the numerical
dependencies in `requirements.txt` and does not build a report.

## Data and reproduction

These are model-generated simulation data, not measurements. Three baseline CSVs each contain 100001 rows with columns `time_s, reference, output, error, control`. Paper reference values are stored separately in `data/reference/`.

Full CSVs are stored losslessly as gzip parts under `data/generated/archive/`. To restore missing CSVs, verify their SHA-256 hashes and recompute comparisons without running the solver:

```bash
python analyse_saved_data.py
```

To rerun the focused CHR check at 30, 100 and 200 s with steps of 0.001 and 0.0005 s:

```bash
python tools/check_chr_integrals.py
```

This writes `results/chr_integral_diagnostic.json` and leaves the primary 100 s outputs unchanged. The diagnostic checks the signed moments; sampled nonnegative errors are not a proof of global monotonicity.

After intentionally regenerating the baseline CSVs, refresh the lossless archive with:

```bash
python tools/pack_data.py
```

See [data provenance](docs/data_provenance.md) for serialization, reference sources and environment records.

## Code layout

| Path | Purpose |
|---|---|
| `config/experiment.json` | Plant parameters, time steps, horizons, Padé orders and sensitivity factors |
| `src/model.py` | Tuning rules, stored-history solver, metrics and independent delay checks |
| `src/analysis.py` | CSV validation and comparison with published metrics |
| `src/data_archive.py` | Restore and verify archived CSVs |
| `run_replication.py` | Simulations, validation, sensitivity analysis and figures |
| `analyse_saved_data.py` | Reload existing data without simulation |
| `tests/test_model.py` | Four scientific correctness checks |
| `tools/check_chr_integrals.py` | Focused CHR horizon and signed-moment diagnostic |
| `tools/pack_data.py` | Lossless data packaging |
| `results/` | Saved numerical outputs, plots, logs and execution provenance |

The 27-case sensitivity grid holds controller gains fixed while changing the plant time constant and delay by -20%, 0% and +20%. It is an exploratory finite grid, not a robust-stability certificate. Faster tuning reaches about 10.105% overshoot in the tested grid. The nominal model has no actuator limits, noise or disturbances.
