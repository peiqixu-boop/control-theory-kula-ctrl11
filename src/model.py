"""Continuous PI/first-order plant with a stored-history transport delay.

RK4 advances plant and integral states. Delayed control values between stored
samples use linear interpolation, so RK4 alone does not imply fourth-order
accuracy for the complete delay scheme. The discontinuity at t=delay is aligned
with the grid and approached from the left at the preceding RK4 endpoint.
"""
from dataclasses import dataclass
import math
import numpy as np
from scipy import signal


@dataclass(frozen=True)
class Controller:
    name: str
    kp: float
    ti: float
    source: str


def tuning_rules(gain, tau, delay):
    if min(gain, tau, delay) <= 0:
        raise ValueError('This experiment requires positive gain, time constant and delay.')
    critical = tau / (math.e * delay * gain)
    return [
        Controller('critical', critical, tau, 'Equations (39), (45), PDF p.8'),
        Controller('fast', 1.25 * critical, tau, 'Equations (39), (47), PDF p.8'),
        Controller('chr', 0.35 * tau / (gain * delay), 1.2 * tau, 'Section 5.1, PDF p.14'),
    ]


def simulate(gain, tau, delay, controller, h, horizon, amplitude=1.0):
    """Return columns time_s, reference, output, error, control.

    Uses physical y,z states, not nominal pole cancellation. This also supports
    parameter uncertainty without retuning the controller. Grid alignment of
    the delay is required here to handle the initial discontinuity explicitly.
    """
    lag = int(round(delay / h))
    count = int(round(horizon / h))
    if lag < 1 or not math.isclose(lag*h, delay, abs_tol=1e-10):
        raise ValueError('Delay must be a positive integer multiple of h.')
    if not math.isclose(count*h, horizon, abs_tol=1e-10):
        raise ValueError('Horizon must be an integer multiple of h.')
    t = np.arange(count+1) * h
    y = np.zeros(count+1)
    u = np.zeros(count+1)
    z = 0.0
    kp, ti = controller.kp, controller.ti
    u[0] = kp * amplitude
    for n in range(count):
        j = n-lag
        # Delayed input at the start, midpoint and left endpoint of this step.
        start = u[j] if j >= 0 else 0.0
        middle = 0.5*(u[j]+u[j+1]) if j >= 0 else 0.0
        end = u[j+1] if j >= 0 else 0.0
        yn = y[n]
        k1y = (gain*start - yn) / tau
        k1z = amplitude - yn
        y2 = yn + h*k1y/2
        k2y = (gain*middle - y2) / tau
        k2z = amplitude - y2
        y3 = yn + h*k2y/2
        k3y = (gain*middle - y3) / tau
        k3z = amplitude - y3
        y4 = yn + h*k3y
        k4y = (gain*end - y4) / tau
        k4z = amplitude - y4
        y[n+1] = yn + h*(k1y + 2*k2y + 2*k3y + k4y)/6
        z += h*(k1z + 2*k2z + 2*k3z + k4z)/6
        u[n+1] = kp*(amplitude-y[n+1] + z/ti)
    return np.column_stack((t, np.full_like(t, amplitude), y, amplitude-y, u))


def metrics(data):
    t, r, y, e, _ = data.T
    target = r[-1]
    band = 0.02*abs(target)
    outside = np.flatnonzero(np.abs(e) > band)
    if not len(outside):
        settling = 0.0
    elif outside[-1] == len(t)-1:
        settling = float('nan')
    else:
        k = outside[-1]
        a, b = abs(e[k]), abs(e[k+1])
        settling = float(t[k] + (t[k+1]-t[k])*(a-band)/(a-b))
    return {
        'overshoot_pct': float(max(0.0, (y.max()-target)/abs(target)*100)),
        'settling_time_s': settling,
        'IAE': float(np.trapezoid(abs(e), t)),
        'ITAE': float(np.trapezoid(t*abs(e), t)),
        'ISE': float(np.trapezoid(e*e, t)),
        'ITSE': float(np.trapezoid(t*e*e, t)),
        'final_error': float(e[-1]),
        'tail_max_abs_error': float(np.max(abs(e[t >= t[-1]-min(10,t[-1]/5)]))),
    }


def exact_cancelled_step(t, a, delay):
    """Finite method-of-steps series, used ONLY for t <= 20 s in validation.

    Y(s)=a exp(-delay*s)/(s*(s+a exp(-delay*s))). Long horizons can cause
    cancellation in this alternating series, so it is not the main solver.
    """
    ans = np.zeros_like(t)
    for k in range(1, int(t[-1]/delay)+1):
        q = np.maximum(t-k*delay, 0.0)
        ans += (-1)**(k-1) * (a*q)**k / math.factorial(k)
    return ans


def pade_step(gain, tau, delay, controller, order, t):
    """Independent rational transfer-function simulation with diagonal [n/n] Pade.

    Coefficients are from the diagonal exponential approximant. scipy.signal
    uses its state-space/matrix-exponential step implementation; no DDE history
    code is reused. All polynomial arrays below are descending powers of s.
    """
    n = order
    c = [math.factorial(2*n-k)*math.factorial(n) /
         (math.factorial(2*n)*math.factorial(k)*math.factorial(n-k))*delay**k
         for k in range(n+1)]
    nd = np.array([(-1)**k*c[k] for k in range(n+1)])[::-1]
    dd = np.array(c)[::-1]
    num = gain*controller.kp*np.polymul([controller.ti, 1], nd)
    den = np.polyadd(np.polymul([tau*controller.ti, controller.ti, 0], dd), num)
    _, y = signal.step(signal.TransferFunction(num, den), T=t)
    return y, np.roots(den)
