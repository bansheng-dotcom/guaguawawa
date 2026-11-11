import unittest
from local_actions import check_text
class LocalTextCases(unittest.TestCase):
 def test_real(self): self.assertEqual(check_text('hello','xhs')['capability_status'],'real')
 def test_limit_failure(self): self.assertFalse(check_text('x'*1001,'xhs')['ok'])
if __name__=='__main__': unittest.main()
