# Model and independently calculated parameters

Reference: K. S. Kula (2024), *Tuning a PI/PID Controller with Direct Synthesis to Obtain a Non-Oscillatory Response of Time-Delayed Systems*, Applied Sciences 14(13), 5468. DOI: https://doi.org/10.3390/app14135468.

The selected example is a simulation, not a data-fitting experiment. The correct nominal plant includes the exponential delay:

$$G(s)=\frac{2e^{-2s}}{4s+1},\qquad C(s)=K_p\left(1+\frac{1}{T_i s}\right).$$

## Derivation rather than copying printed gains

For the first-order plus dead-time plant $K e^{-\theta s}/(Ts+1)$, set $T_i=T$ (Eq. 39). Nominal pole-zero cancellation gives the characteristic equation

$$D(s)=Ts+KK_p e^{-\theta s}=0.$$

At the repeated real root, $D(s)=D'(s)=0$. Since $D'(s)=T-\theta KK_p e^{-\theta s}$, substituting $KK_p e^{-\theta s}=T/\theta$ into $D=0$ gives $s=-1/\theta$. Thus

$$K_p=\frac{T}{e\theta K},\quad T_i=T.$$

Equations (39), (45) on PDF p.8 give $K_p=1/e=0.36787944117144233$ for $K=2,T=4,\theta=2$. Equation (47) specifies a faster setting $K_{p1}=1.25K_p=0.4598493014643029$. The multiplier 1.25 is the paper's rule, not a newly derived global optimum. This delay system has infinitely many characteristic roots; the repeated-root calculation is not a claim that all of them are real.

CHR is independently computed using Section 5.1, PDF p.14: $K_p=0.35T/(K\theta)=0.35$, $T_i=1.2T=4.8$ s. These calculations are executable in `src/model.py`, and outputs are in `results/derived_parameters.csv`. Primary simulations use full precision. `rounded_parameters_metrics.csv` separately evaluates gains rounded to four decimal places.

## Physical states and delay handling

$$T\dot y(t)+y(t)=Ku(t-\theta),\quad \dot z(t)=r(t)-y(t),\quad u(t)=K_p[r(t)-y(t)+z(t)/T_i].$$

All states are zero initially, $u(t)=0$ for $t<0$, and $r(t)=1$ for $t\ge0$. There is no saturation, noise or disturbance in this nominal linear experiment. The implementation integrates both physical states, retaining the plant pole even when nominal cancellation is available. Therefore the same code can evaluate plant mismatch with fixed nominal gains.

The solver is RK4 with linearly interpolated delayed control history. Its complete accuracy is not automatically fourth order, because the interpolated history also introduces error. The grid must divide the delay. The initial derivative discontinuity at $t=\theta$ is handled with a left limit for the preceding RK4 endpoint, and the new input is used on the following step. Tests explicitly check zero response before the delay and the first analytically known segment. Arbitrary non-grid-aligned delays are outside this implementation's supported scope.

## Metrics and independent checks

With $e(t)=1-y(t)$ and numerical horizon $H$, use trapezoidal quadrature:

$$\mathrm{IAE}=\int_0^H|e(t)|\,dt,\quad\mathrm{ISE}=\int_0^He(t)^2\,dt,$$
$$\mathrm{ITAE}=\int_0^Ht|e(t)|\,dt,\quad\mathrm{ITSE}=\int_0^Ht e(t)^2\,dt.$$

For dimensionless unit-step error, IAE/ISE have units s and ITAE/ITSE have units s². ITSE weights by time, not time squared. Settling time is the last exit from the 2% band followed by remaining inside for the observed horizon. A linear interpolation estimates the boundary crossing; a response outside at the endpoint is marked not settled. Finite-horizon checks are not a proof of asymptotic stability under every perturbation. Overshoot is measured relative to the known target 1.

For $T_i=T$, an independent exact finite method-of-steps series is

$$y(t)=\sum_{k=1}^{\lfloor t/\theta\rfloor}(-1)^{k-1}\frac{[a(t-k\theta)]^k}{k!},\quad a=KK_p/T.$$

It is evaluated only through 20 s to avoid cancellation of large alternating terms at long horizons. Separate low-frequency identities for stable unit-step tracking are

$$\int_0^\infty e(t)\,dt=A,\quad \int_0^\infty t e(t)\,dt=A(A+T_i-T-\theta),\quad A=\frac{T_i}{KK_p}.$$

These are signed integrals: they equal IAE/ITAE only if the error stays nonnegative. They provide checks for CHR as well as the proposed settings. Finite-horizon residuals are reported. Padé orders 1, 3, 5 and 7 are independently simulated via rational closed-loop transfer functions and SciPy state-space step responses.

## Figure scope

The two proposed delayed-plant responses in Figure 2 are replicated. Its additional desired second-order reference curve is outside the selected baseline. Figure 8 is checked through the proposed critical-damping/CHR comparison. Figure annotations are approximate visual references; the original curves have not been digitized, so no numerical curve RMSE against the paper is claimed. The Padé RMSE is instead against our delay-history solution.

For the CHR case, the signed time-weighted integral is 38.79183673. The triangle inequality makes this a lower bound on infinite-horizon ITAE even without a global nonnegative-error proof. A separate 200 s, two-step-size check and the 30 s comparison are detailed in [validation.md](validation.md).
