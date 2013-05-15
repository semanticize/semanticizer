'''
Created on 13 Apr 2013

@author: evert
'''
import unittest
import procpipeline

from mock import patch


class Test(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_build(self):
        pass

    @patch('procpipeline.SemanticizeProcessor', autospec=True, create=True)
    def test_load_semanticize_processor(self, mock):
        # Initialize

        # ++++++++++++++++++++++++++++
        # ++++++++ Run tests +++++++++
        # ++++++++++++++++++++++++++++

        # Running with wikipedia_ids as None throws an AttributeException
        # because we access attributes
        self.assertRaises(AttributeError,
                          procpipeline._load_semanticize_processor,
                          None)

        # Running with a dict of zero wikipedia_ids should work fine
        assert procpipeline._load_semanticize_processor(dict())

        # use the mocked-out SemanticizeProcessor
        print procpipeline._load_semanticize_processor(
                                                {'me': ['hey', 'later'],
                                                 'you': ['hi', 'bye']})

    @unittest.skip("not yet implemented")
    def test_load_features(self):
        # Initialize

        # ++++++++++++++++++++++++++++
        # ++++++++ Run tests +++++++++
        # ++++++++++++++++++++++++++++
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
