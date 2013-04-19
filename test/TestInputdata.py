'''
Testsuite for the init.Initializer module
'''
import unittest
import os
import inputdata

from tempfile import mkstemp
from textcat import NGram


class Test(unittest.TestCase):

    def setUp(self):
        self.tmpfile, self.tmpfilename = mkstemp()

    def test_load_textcat(self):
        # Initialize
        invalid_lm_dir = os.path.dirname(self.tmpfilename)
        valid_lm_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "../LM.lrej2011")

        # ++++++++++++++++++++++++++++
        # ++++++++ Run tests +++++++++
        # ++++++++++++++++++++++++++++

        # Fail if lm_dir isn't set
        self.assertRaises(TypeError, inputdata.load_textcat)

        # Fail if lm_dir is invalid
        self.assertRaises(ValueError, inputdata.load_textcat, invalid_lm_dir)

        # Return an NGram object if lm_dir is valid
        self.assertIsInstance(inputdata.load_textcat(valid_lm_dir), NGram,
                              "_load_textcat with %s should result in a" \
                              % valid_lm_dir + "valid_lm_dir NGram instance."
                              + "Does the path contain valid lm files?")


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
