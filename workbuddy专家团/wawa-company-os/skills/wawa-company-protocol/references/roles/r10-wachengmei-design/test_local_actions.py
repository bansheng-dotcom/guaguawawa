import unittest, tempfile, os
from local_actions import inspect_media
class LocalMediaCases(unittest.TestCase):
 def test_real_image(self):
  with tempfile.TemporaryDirectory() as d:
   p=os.path.join(d,'x.png'); open(p,'wb').write(b'png')
   self.assertEqual(inspect_media(p)['capability_status'],'real')
 def test_missing_blocked(self):
  r=inspect_media('missing.mp4'); self.assertEqual(r['capability_status'],'blocked')
if __name__=='__main__': unittest.main()
