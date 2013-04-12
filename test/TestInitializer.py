'''
Testsuite for the init.Initializer module
'''
import unittest
import os

from init.Initializer import Initializer
from tempfile import mkstemp
from textcat import NGram
from mock import patch


class Test(unittest.TestCase):

    def setUp(self):
        self.tmpfile, self.tmpfilename = mkstemp()

    def test_start_server(self):
        pass

    def test_load_textcat(self):
        # Initialize
        initializer = Initializer()
        invalid_lm_dir = os.path.dirname(self.tmpfilename)
        valid_lm_dir = "../LM.lrej2011"

        # ++++++++++++++++++++++++++++
        # ++++++++ Run tests +++++++++
        # ++++++++++++++++++++++++++++

        # Fail if lm_dir isn't set
        self.assertRaises(AttributeError, initializer._load_textcat)

        # Fail if lm_dir is invalid
        initializer.lm_dir = invalid_lm_dir
        self.assertRaises(ValueError, initializer._load_textcat)

        # Return an NGram object if lm_dir is valid
        initializer.lm_dir = valid_lm_dir
        self.assertIsInstance(initializer._load_textcat(), NGram,
                              "_load_textcat with %s should result in a valid \
                              NGram instance. Does the path contain valid lm \
                              files?" % valid_lm_dir)

    def test_load_stopwords(self):
        # Initialize
        initializer = Initializer()
        invalid_sw_dir = os.path.dirname(self.tmpfilename)
        valid_sw_dir = "../SW"

        # ++++++++++++++++++++++++++++
        # ++++++++ Run tests +++++++++
        # ++++++++++++++++++++++++++++

        # Fail if stopword_dir isn't set
        self.assertRaises(AttributeError, initializer._load_stopwords)

        # Fail if stopword_dir is invalid
        initializer.stopword_dir = invalid_sw_dir
        stopwords = initializer._load_stopwords()
        self.assertDictEqual(stopwords, {}, "Stopwords loaded from "
                            + invalid_sw_dir + " should be empty, but found "
                            + str(stopwords))

        # Load stopword dict if stopword_dir is valid
        initializer.stopword_dir = valid_sw_dir
        stopwords = initializer._load_stopwords()
        self.assertTrue(len(stopwords) > 0, "Should have a list of stopwords, \
                                            but found an empty list")

    def test_load_wp_languages(self):
        # Initialize
        initializer = Initializer()
        path = "/Users/evertlammerts/Downloads/zfs/ilps-plexer/wikipediaminer/nlwiki-20111104/"

        # ++++++++++++++++++++++++++++
        # ++++++++ Run tests +++++++++
        # ++++++++++++++++++++++++++++

        # Throw typeerror if langloc isn't set...
        self.assertRaises(TypeError, initializer._load_wp_languages)
        # ... or is not iterable
        initializer.langloc = 15
        self.assertRaises(TypeError, initializer._load_wp_languages)

        # Throw valueerror if langloc can't be unpacked
        initializer.langloc = "hallo"
        self.assertRaises(ValueError, initializer._load_wp_languages)
        initializer.langloc = {'a': 'b'}
        self.assertRaises(ValueError, initializer._load_wp_languages)

        # Return an emnpty dict if value is empty
        initializer.langloc = {}
        self.assertDictEqual(initializer._load_wp_languages(), {},
                              "_load_wp_languages should return an empty dict")

        # Test the transformation is done right
        initializer.langloc = [("dutch", "nl", path)]
        expected = {'nl': ['dutch', path]}
        actual = initializer._load_wp_languages()
        self.assertDictEqual(actual, expected,
                             "_load_wp_languages should return " + \
                             str(expected) + ", got " + str(actual) \
                             + "instead")

        # Test uniqueness
        initializer.langloc = [("dutch", "nl", path), \
                               ("dutch", "nl", path)]
        self.assertEqual(len(initializer._load_wp_languages()),
                         1,
                         "_load_wp_languages should have filtered \
                         duplicate entries")

    def test_load_pipeline(self):
        # Initialize
        initializer = Initializer()

        # ++++++++++++++++++++++++++++
        # ++++++++ Run tests +++++++++
        # ++++++++++++++++++++++++++++

    @patch('init.Initializer.SemanticizeProcessor', autospec=True, create=True)
    def test_load_semanticize_processor(self, mock):
        # Initialize
        initializer = Initializer()

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

    def test_load_features(self):
        # Initialize
        initializer = Initializer()

        # ++++++++++++++++++++++++++++
        # ++++++++ Run tests +++++++++
        # ++++++++++++++++++++++++++++


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
