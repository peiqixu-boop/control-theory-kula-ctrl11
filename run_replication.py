"""Run from a checkout with: python run_replication.py

No network or external data download is required. All primary controller gains
are calculated from published rules. The rounded-gain run is secondary only.
"""
from pathlib import Path
import csv
import hashlib
import json
import logging
import platform
import sys
import time
from datetime import datetime, timezone
from dataclasses import asdict, replace
import numpy as np
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.model import tuning_rules, simulate, metrics, exact_cancelled_step, pade_step
from src.analysis import write_csv, analyse_saved, COLUMNS

ROOT = Path(__file__).resolve().parent
LABELS = {'critical':'Proposed critical damping','fast':'Proposed faster setting','chr':'CHR'}
STYLES = {'critical':'-','fast':'--','chr':':'}

def savefig(fig, name):
    fig.savefig(ROOT/'results'/'figures'/f'{name}.png', dpi=220, bbox_inches='tight')
    fig.savefig(ROOT/'results'/'figures'/f'{name}.svg', bbox_inches='tight')
    plt.close(fig)

def main():
    started=time.perf_counter()
    for p in ['data/generated','results/figures','results/logs']:
        (ROOT/p).mkdir(parents=True,exist_ok=True)
    log=logging.getLogger('replication'); log.setLevel(logging.INFO)
    log.handlers.clear()
    for handler in [logging.StreamHandler(sys.stdout),logging.FileHandler(ROOT/'results/logs/run.log',mode='w')]:
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s')); log.addHandler(handler)
    config=json.loads((ROOT/'config/experiment.json').read_text())
    environment={'utc_started':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),
        'numpy':np.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__,
        'platform':platform.system()+' '+platform.machine(),'command':'python run_replication.py',
        'input_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
            for p in ['config/experiment.json','data/reference/table1.csv','src/model.py','src/analysis.py','src/data_archive.py','run_replication.py']}}
    (ROOT/'results/environment.json').write_text(json.dumps(environment,indent=2))
    log.info('START %s',environment)
    plant=config['plant']; gain=plant['gain']; tau=plant['time_constant_s']; delay=plant['delay_s']
    controllers=tuning_rules(gain,tau,delay)
    write_csv(ROOT/'results/derived_parameters.csv',[asdict(c) for c in controllers])
    log.info('Independently derived parameters: %s',[asdict(c) for c in controllers])
    h=config['primary_step_s']; H=config['primary_horizon_s']
    baseline={}
    for c in controllers:
        d=simulate(gain,tau,delay,c,h,H)
        baseline[c.name]=d
        np.savetxt(ROOT/'data/generated'/f'{c.name}.csv',d,delimiter=',',header=COLUMNS,comments='',fmt='%.17g')
        log.info('SIMULATED %s, %s rows, step %.6g s, horizon %.6g s',c.name,len(d),h,H)
    results,comparison,checks=analyse_saved(ROOT)
    log.info('RELOADED AND VALIDATED: %s',checks)
    for row in results: log.info('METRICS %s',row)

    convergence=[]; exact=[]; rounding=[]; horizon=[]
    for c in controllers:
        bm=metrics(baseline[c.name])
        for step in config['convergence_steps_s']:
            d=baseline[c.name] if step==h else simulate(gain,tau,delay,c,step,H)
            m=metrics(d)
            for key in ['IAE','ITAE','ISE','ITSE','settling_time_s','overshoot_pct']:
                delta=m[key]-bm[key]
                convergence.append({'controller':c.name,'step_s':step,'metric':key,'value':m[key],
                    'difference_from_finest':delta,'relative_difference_pct':100*delta/abs(bm[key]) if abs(bm[key])>1e-8 else ''})
        if c.name!='chr':
            d=baseline[c.name]; mask=d[:,0]<=20
            theoretical=exact_cancelled_step(d[mask,0],gain*c.kp/tau,delay)
            error=float(np.max(abs(d[mask,2]-theoretical)))
            exact.append({'controller':c.name,'time_end_s':20,'max_absolute_output_error':error})
            assert error<1e-6, f'Analytical delay solution mismatch: {error}'
        rounded=replace(c,kp=round(c.kp,4))
        rm=metrics(simulate(gain,tau,delay,rounded,h,H))
        rounding.append({'controller':c.name,'rounded_kp':rounded.kp,**rm})
        for end in config['horizon_checks_s']:
            d=baseline[c.name]
            horizon.append({'controller':c.name,'horizon_s':end,**metrics(d[d[:,0]<=end])})
    write_csv(ROOT/'results/time_step_convergence.csv',convergence)
    write_csv(ROOT/'results/exact_solution_check.csv',exact)
    write_csv(ROOT/'results/rounded_parameters_metrics.csv',rounding)
    write_csv(ROOT/'results/horizon_convergence.csv',horizon)
    log.info('EXACT METHOD-OF-STEPS CHECK: %s',exact)

    # Known integral identity: integral(e) = Ti/(K*Kp) for a stable unit step.
    identities=[]
    for c in controllers:
        d=baseline[c.name]; numeric=float(np.trapezoid(d[:,3],d[:,0]))
        target=c.ti/(gain*c.kp)
        weighted=float(np.trapezoid(d[:,0]*d[:,3],d[:,0]))
        weighted_target=target*(target+c.ti-tau-delay)
        identities.append({'controller':c.name,'signed_error_integral':numeric,'analytic_value':target,'absolute_error':abs(numeric-target),
            'signed_time_weighted_integral':weighted,'analytic_time_weighted_value':weighted_target,
            'time_weighted_absolute_error':abs(weighted-weighted_target)})
        assert abs(numeric-target)<1e-5
        assert abs(weighted-weighted_target)<1e-3
    write_csv(ROOT/'results/signed_integral_check.csv',identities)

    # Independent Pade implementation on a common 0.01 s output grid.
    stride=int(round(.01/h))
    if stride<1 or not np.isclose(stride*h,.01):
        raise ValueError('Primary h must divide the 0.01 s Pade comparison output grid.')
    pade_results=[]; pade_curves={}; sample=baseline['critical'][::stride,0]
    sample=sample[sample<=40]
    for c in controllers:
        reference=baseline[c.name][::stride,2][:len(sample)]
        for order in config['pade_orders']:
            y,poles=pade_step(gain,tau,delay,c,order,sample)
            err=y-reference
            pade_results.append({'controller':c.name,'order':order,'max_abs_output_error':float(max(abs(err))),
                'rms_output_error':float(np.sqrt(np.mean(err**2))),
                'max_abs_error_after_2delay':float(max(abs(err[sample>=2*delay]))),
                'max_real_pole':float(max(poles.real))})
            if c.name=='fast': pade_curves[order]=y
    write_csv(ROOT/'results/pade_comparison.csv',pade_results)
    log.info('PADE CHECK: %s',[x for x in pade_results if x['order']==7])

    # Optional compact extension, distinct from the published nominal comparison.
    sensitivity=[]
    for c in controllers:
        for tf in config['sensitivity_factors']:
            for df in config['sensitivity_factors']:
                d=simulate(gain,tau*tf,delay*df,c,config['sensitivity_step_s'],H)
                m=metrics(d)
                sensitivity.append({'controller':c.name,'tau_factor':tf,'delay_factor':df,
                    'fixed_kp':c.kp,'fixed_ti':c.ti,**m})
    write_csv(ROOT/'results/sensitivity.csv',sensitivity)
    log.info('SENSITIVITY: %d fixed-controller cases completed.',len(sensitivity))
    sensitivity_checks=[]
    for c in controllers:
        worst=max((x for x in sensitivity if x['controller']==c.name),key=lambda x:x['overshoot_pct'])
        d=simulate(gain,tau*worst['tau_factor'],delay*worst['delay_factor'],c,h,H)
        fine=metrics(d)
        sensitivity_checks.append({'controller':c.name,'tau_factor':worst['tau_factor'],'delay_factor':worst['delay_factor'],
          'coarse_step_s':config['sensitivity_step_s'],'fine_step_s':h,
          'coarse_overshoot_pct':worst['overshoot_pct'],'fine_overshoot_pct':fine['overshoot_pct'],
          'overshoot_difference_percentage_points':fine['overshoot_pct']-worst['overshoot_pct']})
    write_csv(ROOT/'results/sensitivity_refinement.csv',sensitivity_checks)

    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(10,3.4),layout='constrained')
    for ax,names,end,title in [(axes[0],['critical','fast'],20,'Figure 2 target'),
                              (axes[1],['critical','chr'],40,'Figure 8 target')]:
        for name in names:
            d=baseline[name]; ax.plot(d[::10,0],d[::10,2],STYLES[name],color='black',label=LABELS[name],lw=1.6)
        ax.axhline(1,color='0.55',lw=.7); ax.axhspan(.98,1.02,color='.92',label='2% band')
        ax.set(xlim=(0,end),ylim=(0,1.08),xlabel='Time (s)',ylabel='Output y(t)',title=title)
        ax.legend(fontsize=8,loc='lower right'); ax.grid(alpha=.2)
    savefig(fig,'baseline_responses')

    fig,ax=plt.subplots(figsize=(7,3.4),layout='constrained')
    for name in ['critical','fast','chr']:
        d=baseline[name];ax.plot(d[::10,0],d[::10,4],STYLES[name],color='black',label=LABELS[name])
    ax.set(xlim=(0,25),xlabel='Time (s)',ylabel='Controller output u(t)');ax.legend();ax.grid(alpha=.2)
    savefig(fig,'control_effort')

    fig,axes=plt.subplots(1,2,figsize=(10,3.4),layout='constrained')
    ref=baseline['fast'][::stride,2][:len(sample)]
    axes[0].plot(sample,ref,color='black',label='Stored history')
    for order,y in pade_curves.items():
        axes[0].plot(sample,y,lw=1,ls='--',label=f'Pade order {order}')
        axes[1].plot(sample,abs(y-ref),label=f'Order {order}')
    axes[0].set(xlim=(0,15),xlabel='Time (s)',ylabel='Output y(t)',title='Faster controller')
    axes[1].set(xlim=(0,15),xlabel='Time (s)',ylabel='Absolute output error',yscale='log',ylim=(1e-9,1),title='Delay approximation error')
    for ax in axes: ax.grid(alpha=.2);ax.legend(fontsize=8)
    savefig(fig,'pade_validation')

    fig,axes=plt.subplots(1,3,figsize=(10,3.2),layout='constrained')
    for ax,c in zip(axes,controllers):
        vals=np.array([x['overshoot_pct'] for x in sensitivity if x['controller']==c.name]).reshape(3,3)
        ax.imshow(vals,cmap='Greys',vmin=0,vmax=max(x['overshoot_pct'] for x in sensitivity),origin='lower')
        for i in range(3):
            for j in range(3):ax.text(j,i,f'{vals[i,j]:.2f}%',ha='center',va='center',color='white' if vals[i,j]>8 else 'black')
        ax.set(xticks=[0,1,2],yticks=[0,1,2],xticklabels=['0.8','1.0','1.2'],yticklabels=['0.8','1.0','1.2'],xlabel='Delay / nominal delay',ylabel='Time constant / nominal',title=LABELS[c.name])
    savefig(fig,'sensitivity_overshoot')

    summary={'metrics':results,'max_table1_abs_relative_difference_pct':max(abs(x['relative_difference_pct']) for x in comparison),
        'exact_solution_checks':exact,'signed_integral_checks':identities,
        'sensitivity_cases':len(sensitivity),'elapsed_seconds':time.perf_counter()-started,
        'remote_repository':'https://github.com/peiqixu-boop/control-theory-kula-replication','simulation_status':'completed',
        'published_curve_digitisation':'not performed; visual/feature comparison only'}
    (ROOT/'results/summary.json').write_text(json.dumps(summary,indent=2))
    log.info('COMPLETE in %.2f s; published maximum relative metric difference %.4f%%',summary['elapsed_seconds'],summary['max_table1_abs_relative_difference_pct'])

if __name__=='__main__': main()
