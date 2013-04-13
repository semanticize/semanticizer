'''
Testsuite for the init.Initializer module
'''
import unittest
import os
import inputdata

from tempfile import mkstemp
from textcat import NGram
from mock import patch


class Test(unittest.TestCase):

    def setUp(self):
        self.tmpfile, self.tmpfilename = mkstemp()

    def test_load_textcat(self):
        # Initialize
        invalid_lm_dir = os.path.dirname(self.tmpfilename)
        valid_lm_dir = "../LM.lrej2011"

        # ++++++++++++++++++++++++++++
        # ++++++++ Run tests +++++++++
        # ++++++++++++++++++++++++++++

        # Fail if lm_dir isn't set
        self.assertRaises(AttributeError, inputdata.load_textcat)

        # Fail if lm_dir is invalid
        self.assertRaises(ValueError, inputdata.load_textcat, invalid_lm_dir)

        # Return an NGram object if lm_dir is valid
        self.assertIsInstance(inputdata.load_textcat(valid_lm_dir), NGram,
                              "_load_textcat with %s should result in a valid \
                              NGram instance. Does the path contain valid lm \
                              files?" % valid_lm_dir)

    def test_load_stopwords(self):
        # Initialize
        invalid_sw_dir = os.path.dirname(self.tmpfilename)
        valid_sw_dir = "../SW"

        # ++++++++++++++++++++++++++++
        # ++++++++ Run tests +++++++++
        # ++++++++++++++++++++++++++++

        # Fail if stopword_dir isn't set
        self.assertRaises(AttributeError, inputdata.load_stopwords)

        # Fail if stopword_dir is invalid
        stopwords = inputdata.load_stopwords(invalid_sw_dir)
        self.assertDictEqual(stopwords, {}, "Stopwords loaded from "
                            + invalid_sw_dir + " should be empty, but found "
                            + str(stopwords))

        # Load stopword dict if stopword_dir is valid
        stopwords = inputdata.load_stopwords(valid_sw_dir)
        self.assertTrue(len(stopwords) > 0, "Should have a list of stopwords, \
                                            but found an empty list")

    @patch('init.Initializer.SemanticizeProcessor', autospec=True, create=True)
    def test_load_semanticize_processor(self, mock):
        # Initialize

        # ++++++++++++++++++++++++++++
        # ++++++++ Run tests +++++++++
        # ++++++++++++++++++++++++++++

        # Running with wikipedia_ids as None throws an AttributeException
        # because we access attributes
        self.assertRaises(AttributeError,
                          initializer._load_semanticize_processor,
                          None)

        # Running with a dict of zero wikipedia_ids should work fine
        assert initializer._load_semanticize_processor(dict())

        # use the mocked-out SemanticizeProcessor
        print initializer._load_semanticize_processor(
                                                {'me': ['hey', 'later'],
                                                 'you': ['hi', 'bye']})


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
