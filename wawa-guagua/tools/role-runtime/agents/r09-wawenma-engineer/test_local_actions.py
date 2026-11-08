import unittest, tempfile, os
from agent import _run_local_verify
class LocalVerifyCases(unittest.TestCase):
 def test_unapproved_command_blocked(self):
  r=_run_local_verify('.', 'pytest', 'cmd.exe'); self.assertEqual(r['capability_status'],'blocked')
 def test_local_unittest_real(self):
  with tempfile.TemporaryDirectory() as d:
   r=_run_local_verify(d,'unittest', __import__('sys').executable)
   self.assertEqual(r['capability_status'],'real')
if __name__=='__main__': unittest.main()
