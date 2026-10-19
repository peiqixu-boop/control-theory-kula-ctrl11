# Deviations and assumptions

| Item | Published method | This implementation | Impact and response |
|---|---|---|---|
| Software | MATLAB/Simulink 2023b, PDF p.10 | Python 3.12 / NumPy / SciPy / Matplotlib | Independent implementation; environment and numerical checks recorded. |
| Controller values | Analytical rules and rounded example values | Full-precision gains calculated from Eqs. 39/45/47 and Section 5.1 | Separate rounded-gain simulation quantifies rounding. |
| Numerical solver | Exact solver settings are not specified in the selected paper descriptions | RK4 states, linear interpolation of stored input history; grid divides delay | Treat as an implementation choice, not an assertion about the author's solver. Step refinement and analytical checks validate accuracy. |
| Transport delay | Exponential delay in the plant | Explicit delayed input for the primary simulation | Same delayed model. Padé is only an independent approximation check. |
| Integral horizon | Formulas integrate to infinity; practical implementation horizon is not specified | Baseline integrates over [0,100] s; fixed 20/30/50/100 s comparison | CHR signed moments rule out the reported values as infinite-horizon metrics of this nominal model. A roughly 30 s window is consistent with IAE/ITAE, but the author's settings are unconfirmed; see validation.md. |
| Initial/reference conventions | Unit-step plots; detailed solver history is not supplied | Zero plant/integrator states and zero input history; unit reference at t=0 | Explicit, reproducible assumption; zero-response delay interval tested. |
| Figure 2 scope | Two controlled responses plus a desired second-order reference curve | Two proposed PI controlled responses only | Matches the selected two-controller target. Extra reference curve is not claimed reproduced. |
| Figure comparison | Printed curves and annotations | Independent plots; approximate settling-time annotations compared | No original sampled curves were available in the supplied material; no exact original-curve RMSE is claimed. |
| Data | Model-driven simulation | Reference CSV plus separately labeled synthetic CSV files | Simulation data are explicitly distinguished from measurements. |
| Uncertainty | Paper discusses model mismatch through several examples | A distinct 3x3 grid of time constant/delay factors for each fixed nominal controller | Additional experiment, not a reproduction of the paper's entire robustness study. |
| Step size support | General continuous delay model | Current solver requires delay to be a positive integer multiple of the chosen step | All actual nominal and uncertainty runs satisfy this; arbitrary delays need an extended solver. |

No plant or controller parameters were tuned to reduce Table 1 errors. The primary nominal model has no actuator limits, noise or disturbances. Reported settling is measured over the simulated horizon, not an independent proof of asymptotic stability.
