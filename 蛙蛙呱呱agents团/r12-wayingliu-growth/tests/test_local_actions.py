import unittest
from local_actions import recalc
class LocalMetricCases(unittest.TestCase):
 def test_real(self): self.assertAlmostEqual(recalc({'leads':10,'customers':2})['conversion_rate'],.2)
 def test_zero_safe(self): self.assertIsNone(recalc({'spend':0,'revenue':5})['roi'])
if __name__=='__main__': unittest.main()
