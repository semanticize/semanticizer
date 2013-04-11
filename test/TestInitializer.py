'''
Testsuite for the init.Initializer module
'''
import unittest
import os

from init.Initializer import Initializer
from tempfile import mkstemp
from textcat import NGram

class Test(unittest.TestCase):
    
    def setUp(self):
        self.tmpfile, self.tmpfilename = mkstemp()
        self.initializer = Initializer(None, None, None, None)

    def test_start_server(self):
        pass

    def test_load_textcat(self):
        invalid_lm_dir = os.path.dirname(self.tmpfilename)
        valid_lm_dir = "../LM.lrej2011"
        self.assertRaises(ValueError, self.initializer._load_textcat, invalid_lm_dir)
        self.assertIsInstance(self.initializer._load_textcat(valid_lm_dir),
                              NGram,
                              "_load_textcat with %s should result in a valid NGram instance. Does the path contain valid lm files?" % valid_lm_dir)
        pass
    
    def test_load_stopwords(self):
        pass
    
    def test_load_language(self):
        pass
    
    def test_load_pipeline(self):
        pass
    
    def test_load_semanticize_processor(self):
        pass
    
    def test_load_features(self):
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()