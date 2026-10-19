import unittest
import math
import numpy as np
from src.model import tuning_rules,simulate,metrics,Controller

class ModelChecks(unittest.TestCase):
    def test_double_root_and_rules(self):
        c=tuning_rules(2,4,2)
        kp=c[0].kp;s=-.5
        self.assertAlmostEqual(4*s+2*kp*math.exp(-2*s),0,places=14)
        self.assertAlmostEqual(4-2*2*kp*math.exp(-2*s),0,places=14)
        self.assertAlmostEqual(c[1].kp/c[0].kp,1.25)
        self.assertAlmostEqual(c[2].kp,.35)
        self.assertAlmostEqual(c[2].ti,4.8)

    def test_causality_and_first_delayed_interval(self):
        c=tuning_rules(2,4,2)[0]
        d=simulate(2,4,2,c,.002,4)
        np.testing.assert_array_equal(d[d[:,0]<=2,2],0)
        t=d[:,0]; expected=np.maximum(t-2,0)*2*c.kp/4
        np.testing.assert_allclose(d[:,2],expected,atol=1e-10)

    def test_zero_gain(self):
        d=simulate(2,4,2,Controller('zero',0,4,'test'),.01,10)
        np.testing.assert_array_equal(d[:,2],0)
        np.testing.assert_array_equal(d[:,4],0)

    def test_metrics_known_exponential(self):
        t=np.arange(0,40.0005,.001);e=np.exp(-t)
        d=np.column_stack([t,np.ones_like(t),1-e,e,np.zeros_like(t)])
        m=metrics(d)
        for name,target in [('IAE',1),('ITAE',1),('ISE',.5),('ITSE',.25)]:
            self.assertAlmostEqual(m[name],target,places=6)
        self.assertAlmostEqual(m['settling_time_s'],-math.log(.02),places=6)

if __name__=='__main__':unittest.main()
