# Week 8 verification and preliminary findings

This stage adds a reproducible recheck of the existing experiment and compact
evidence tables. It does not change the controller rules, solver, nominal
parameters or saved 100 s baseline. The source baseline is revision
`b513f7b48265af0e214001b3b006d5b53b33560b`; input hashes and the actual execution
environment are recorded in [verification.json](../results/week8/verification.json).

## Results confirmed

| Check | Recorded outcome |
|---|---|
| Saved nominal trajectories | Three 100001-row CSVs verified against the archive manifest; all rerun values match exactly in the recorded environment |
| Scientific correctness tests | Four pass: tuning identities, causality and first delayed interval, zero gain, exponential-response metrics |
| Independent analytical response | Maximum output error below 1.8e-9 over 0–20 s for the two proposed tunings |
| Fixed-gain plant mismatch | All 27 saved cases reproduced; maximum metric difference is zero in the recorded environment |
| CHR diagnosis | Six combinations of two steps and three horizons; 200 s signed moments agree with the analytical limits within the stated numerical thresholds |

Exact numerical equality describes this recorded execution, not a promise of
bitwise identity on every platform. The verifier accepts at most 1e-10 absolute
difference in saved trajectory values and 1e-8 in saved metrics, and records the
actual differences. It checks input hashes before and after execution and
refuses to overwrite an existing output directory.

The primary replicated integral values remain within 0.638% of the published
values for both proposed tunings. CHR IAE differs by +0.9145% and ITAE by
+6.4239% at 100 s. See the existing
[complete Table 1 comparison](../results/comparison_table1.csv).

## What the CHR comparison shows

| Metric | Paper | 0–30 s | 0–100 s | Contribution from 30–100 s |
|---|---:|---:|---:|---:|
| IAE | 6.795 | 6.794342 | 6.857140 | 0.062798 |
| ITAE | 36.450 | 36.467131 | 38.791524 | 2.324393 |
| ISE | 4.332 | 4.331487 | 4.331768 | 0.000281 |
| ITSE | 12.054 | 12.045961 | 12.055377 | 0.009417 |

Values above use h = 0.001 s. IAE and ISE have units s; ITAE and ITSE have units
s² for the dimensionless unit step. The late error contributes much more to
time-weighted absolute error than to squared error. Thus close ISE/ITSE
agreement does not imply the same integration window was used.

For the same stable nominal loop, assuming convergent error moments, the exact
signed moments imply the infinite-horizon bounds
IAE >= 6.857142857 and ITAE >= 38.791836735. These follow from the triangle
inequality and do not require an all-time nonnegative-error proof. At 200 s,
the rerun ITAE is 38.791836667 with h = 0.001 s and 38.791836718 with h = 0.0005 s.
The derivation and assumptions are in [validation.md](validation.md).

These checks support the original baseline. The paper's CHR IAE and ITAE cannot
be the infinite-horizon metrics of this same stable model and realization.
A finite window near 30 s is a supported explanation, not confirmation of the
author's settings. It does not exactly match all four published entries. The
100 s baseline remains unchanged, and other implementation or reporting
differences remain possible. The smaller discrepancies for the proposed
controllers also remain incompletely explained.

Full results are available in
[chr_horizon_comparison.csv](../results/week8/chr_horizon_comparison.csv) and
[chr_tail_contributions.csv](../results/week8/chr_tail_contributions.csv).
The earlier CHR diagnostic is retained as an independent stage record rather
than overwritten.

## Parameter mismatch extension

The verifier repeats all nine combinations per controller of time-constant and
delay factors 0.8, 1.0 and 1.2. Plant gain remains 2 and controller gains stay
fixed at nominal settings. Runs use h = 0.002 s and horizon 100 s.

| Controller | Nominal overshoot | Maximum observed grid overshoot |
|---|---:|---:|
| Critical | 0% | 4.845% |
| Faster | 1.798% | 10.105% |
| CHR | 0% | 0% |

Critical and Faster maxima occur at T = 4.8 s and delay = 2.4 s. Rechecking each
controller's selected maximum-overshoot case at h = 0.001 s changes overshoot
by less than 1e-6 percentage points. CHR ties at zero in every grid case; its
selected refinement case is simply the first tied case, not a uniquely worst
plant. The [recheck table](../results/week8/sensitivity_recheck.csv) records all
27 cases, and the JSON summary records the refined cases.

The nominal below-2% overshoot property of Faster does not persist across this
grid. These finite tests do not prove robust stability or performance throughout
a continuous uncertainty set.

## Reproduce this stage

Install the numerical dependencies as described in the repository README, then:

```bash
python tools/verify_week8.py --output-dir results/week8_rerun
```

The destination must be new. The script can run from any current directory;
relative output paths are relative to the repository root. It validates the
frozen settings and reads missing baseline CSVs directly from the archive in
memory. No original baseline outputs, source files or archived data are changed.
The generated files are `verification.json`, `tests.log`,
`chr_horizon_comparison.csv`, `chr_tail_contributions.csv` and
`sensitivity_recheck.csv`. No document-generation dependencies are required.

## Remaining work before the final submission

- Independently review the CHR derivation, evidence and uncertainty statements.
- If a fuller Padé assessment is retained, compare integral metrics, settling
  time and overshoot on a common horizon. Existing Padé evidence compares
  waveforms over 0–40 s and must not be presented as a completed 100 s metric study.
- Complete and confirm team assignments and actual contribution statements.
- Check final references, figure provenance and consistency with this evidence.

Original published trajectories have not been digitized. No pointwise error
against the paper, physical measurements, continuous-set robustness guarantee
or confirmed author integration window is claimed.
