import unittest, tempfile, os
from local_actions import clean_csv
class LocalCsvCases(unittest.TestCase):
 def test_real_dedup_and_funnel(self):
  with tempfile.TemporaryDirectory() as d:
   p=os.path.join(d,'crm.csv')
   open(p,'w',encoding='utf-8').write('email,stage\na@x,lead\na@x,won\nb@x,lead\n')
   r=clean_csv(p); self.assertEqual(r['duplicates_removed'],1); self.assertEqual(r['funnel']['lead'],2)
if __name__=='__main__': unittest.main()
