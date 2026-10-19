# Numerical validation and CHR integral comparison

## Solver checks

The four checks in `tests/test_model.py` cover the repeated-root tuning equations, causality and the first delayed interval, zero controller gain, and metric integration against a known exponential response. They pass in the recorded Python 3.12 environment.

The main run also checks:

- Step refinement at 0.004, 0.002 and 0.001 s: `results/time_step_convergence.csv`.
- An independent finite method-of-steps solution for the two proposed controllers through 20 s: `results/exact_solution_check.csv`.
- Signed error moments for all three controllers: `results/signed_integral_check.csv`.
- Padé orders 1, 3, 5 and 7 against the stored-history solution: `results/pade_comparison.csv`.
- Independent rerun and saved-data restoration evidence: `results/clean_checkout_verification.json`.

For the faster controller, the order-7 Padé maximum output error is approximately 0.01092 over 0–40 s and 0.000117 after 4 s. Approximation error is concentrated around delay onset. Padé is not used as the primary delay solver.

## Exact signed moments

For the unity negative-feedback loop with unit-step reference, zero initial history,

$$G(s)=\frac{K e^{-\theta s}}{Ts+1}, \qquad C(s)=K_p\left(1+\frac{1}{T_i s}\right),$$

the error transform is

$$E(s)=\frac{T_i(Ts+1)}
{T_i s(Ts+1)+KK_p(T_i s+1)e^{-\theta s}}.$$

Assuming the closed loop is stable and the relevant moments converge, expansion at $s=0$ gives

$$E(s)=A+A(T+\theta-T_i-A)s+O(s^2), \qquad A=\frac{T_i}{KK_p}.$$

Since $E(0)=\int_0^\infty e(t)\,dt$ and $-E'(0)=\int_0^\infty t e(t)\,dt$,

$$\int_0^\infty e(t)\,dt=A,\qquad
\int_0^\infty t e(t)\,dt=A(A+T_i-T-\theta).$$

These are **signed** integrals. They equal IAE and ITAE only if $e(t)\geq0$ for all time. Nevertheless, the triangle inequality always gives, under the same convergence assumptions,

$$\mathrm{IAE}_\infty\geq|A|,\qquad
\mathrm{ITAE}_\infty\geq|A(A+T_i-T-\theta)|.$$

For the paper's CHR settings $K=2$, $T=4$, $\theta=2$, $K_p=0.35$, $T_i=4.8$,

$$A=6.85714285714,\qquad A(A+T_i-T-\theta)=38.79183673469.$$

Thus the Table 1 values IAE = 6.795 and ITAE = 36.45 are below the infinite-horizon lower bounds for this same stable nominal model, step normalization and controller realization. They cannot be those infinite-horizon metrics under these assumptions. This conclusion does not require a proof that the error remains nonnegative.

## Finite-horizon evidence

The paper defines infinite-horizon metrics in Section 5.3, but the actual finite integration interval used for Table 1 is not identified in that description. CHR parameters are in Section 5.1, and Table 1 appears on printed page 16 of the [paper](https://doi.org/10.3390/app14135468).

The stored baseline and the focused rerun give:

| Metric | Paper CHR | 30 s, h = 0.001 s | Relative difference at 30 s | 100 s, h = 0.001 s |
|---|---:|---:|---:|---:|
| IAE | 6.795 | 6.79434217 | -0.009681% | 6.85713995 |
| ITAE | 36.45 | 36.46713083 | +0.046998% | 38.79152398 |
| ISE | 4.332 | 4.33148654 | -0.011853% | 4.33176755 |
| ITSE | 12.054 | 12.04596092 | -0.066692% | 12.05537746 |

The 30–100 s tail contributes approximately 0.00028102 to ISE and 0.00941653 to ITSE. The tail matters much more for IAE (0.06279778) and ITAE (2.32439315). Agreement in ISE/ITSE therefore does not determine the integration horizon nearly as strongly as IAE/ITAE in this case.

At 200 s, the focused diagnostic returns:

| Step (s) | Signed time-weighted integral and sampled ITAE | Difference from analytic signed moment |
|---|---:|---:|
| 0.001 | 38.79183666679 | -6.79e-8 |
| 0.0005 | 38.79183671759 | -1.71e-8 |

All sampled errors in these two runs are positive. This is numerical evidence for equality of the signed and absolute metrics over the simulated interval, not an all-time sign proof. The infinite-horizon lower-bound argument above does not depend on that sampled-sign observation.

Reproduce this diagnostic with:

```bash
python tools/check_chr_integrals.py
```

The output `results/chr_integral_diagnostic.json` includes all six horizon/step combinations, input hashes and runtime versions. It leaves the primary 100 s outputs unchanged.

**Interpretation:** the converged nominal computation is supported by analytic moments and step refinement. The reported CHR IAE/ITAE are consistent with a shorter integration window near 30 s. This is a supported explanation, not confirmation that the author used exactly 30 s. A single truncated trajectory does not match all four published metrics exactly, and other implementation or reporting differences remain possible. Keep the 100 s baseline and show the finite-horizon comparison separately.

## Scope and sensitivity

The model uses explicit transport delay, full-precision gains and no saturation, noise or disturbances. Original paper trajectories were not digitized, so there is no original-curve RMSE.

The 27-case grid in `results/sensitivity.csv` holds gains fixed while varying plant time constant and delay independently by -20%, 0%, +20%. Maximum observed overshoot is approximately 4.845% for critical tuning and 10.105% for faster tuning; CHR has no observed overshoot in this grid. The worst cases were step-refined in `results/sensitivity_refinement.csv`. These finite tests do not establish stability or performance over a continuous uncertainty set.
