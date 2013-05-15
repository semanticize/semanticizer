'''
Created on 13 Apr 2013

@author: evert
'''
import unittest


class Test(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    @unittest.skip("not yet implemented")
    def test_start_server(self):
        pass

    @unittest.skip("not yet implemented")
    def test_init_logging(self):
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
