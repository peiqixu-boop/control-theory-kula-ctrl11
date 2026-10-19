"""Read saved time series from disk and calculate metrics independently of export."""
from pathlib import Path
import csv
import json
import numpy as np
from .model import metrics
from .data_archive import restore_saved_data

COLUMNS = 'time_s,reference,output,error,control'

def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

def analyse_saved(root):
    restore_saved_data(root)
    rows, checks = [], []
    for name in ['critical','fast','chr']:
        path = root/'data'/'generated'/f'{name}.csv'
        structured = np.genfromtxt(path, delimiter=',', names=True)
        assert structured.dtype.names == tuple(COLUMNS.split(','))
        data = np.column_stack([structured[col] for col in structured.dtype.names])
        t = data[:,0]
        assert np.isfinite(data).all() and np.all(np.diff(t)>0)
        assert np.allclose(data[:,3],data[:,1]-data[:,2],atol=1e-12)
        checks.append({'controller':name,'rows':len(data),'columns':list(structured.dtype.names),
                       'time_start_s':float(t[0]),'time_end_s':float(t[-1]),
                       'nonfinite_values':int((~np.isfinite(data)).sum()),
                       'strictly_increasing_time':True,'error_column_consistent':True})
        rows.append({'controller':name,**metrics(data)})
    write_csv(root/'results'/'metrics.csv', rows)
    (root/'results'/'data_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    with (root/'data'/'reference'/'table1.csv').open(encoding='utf-8') as f:
        refs={x['controller']:x for x in csv.DictReader(f)}
    comparisons=[]
    for row in rows:
        for metric in ['IAE','ITAE','ISE','ITSE']:
            ref=float(refs[row['controller']][metric]); val=row[metric]
            comparisons.append({'controller':row['controller'],'metric':metric,
              'published':ref,'replicated':val,'signed_difference':val-ref,
              'absolute_difference':abs(val-ref),'relative_difference_pct':100*(val-ref)/ref})
    write_csv(root/'results'/'comparison_table1.csv',comparisons)
    return rows,comparisons,checks
