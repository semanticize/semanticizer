'''
Testsuite for the Configuration module
'''
import unittest
import Configuration
from os import remove
from argparse import ArgumentTypeError
from argparse import ArgumentParser
from tempfile import mkstemp
from ConfigParser import MissingSectionHeaderError

class Test(unittest.TestCase):

    def setUp(self):
        self.tmpfile, self.tmpfilename = mkstemp()
        self.config = {
                "port": 6000,
                "lm": self.tmpfilename,
                "verbose": None
                }
        
    def tearDown(self):
        remove(self.tmpfilename)

    def test_readable_path(self):
        valid_path = "/"
        invalid_path = "/invalid/path"
        self.assertTrue(
                Configuration._readable_path(valid_path).endswith(valid_path),
                "_readable_path seems to return an unexpected value for %s" % valid_path)
        self.assertRaises(ArgumentTypeError, Configuration._readable_path, invalid_path)
    
    def test_writable_file(self):
        valid_file = self.tmpfilename
        invalid_file = "/test/test/invalid"
        self.assertTrue(
                Configuration._writable_file(valid_file).endswith(valid_file),
                "_writable_file seems to return an unexpected value for %s" % valid_file)
        self.assertRaises(ArgumentTypeError, Configuration._writable_file, invalid_file)
    
    def test_valid_absolute_url(self):
        valid_url = "http://www.google.com:890/something?param=1&else=2"
        invalid_url = "ha//\\\st||al}avista"
        self.assertEqual(
                Configuration._valid_absolute_url(valid_url),
                valid_url,
                "_valid_absolute_url seems to return an unexpected value for %s" % valid_url)
        self.assertRaises(ArgumentTypeError, Configuration._valid_absolute_url, invalid_url)
    
    def test_validate_langloc(self):
        valid_langloc = ["one", "two", self.tmpfilename]
        invalid_langloc = ["one", "two", "/some/nonexisting/file"]
        class Object(object):pass
        namespace =  Object()
        action = Configuration.ValidateLangloc(["--langloc"], "langloc")
        action.__call__(None, namespace, valid_langloc)
        self.assertTrue(hasattr(namespace, "langloc"), "ValidateLangloc didn't set a valid langloc!")
        action.__call__(None, namespace, valid_langloc)
        self.assertTrue(len(getattr(namespace, "langloc")) == 2, "ValidateLangloc should have two locations, has %d instead" % len(getattr(namespace, "langloc")))
        self.assertRaises(ArgumentTypeError, action.__call__, None, namespace, invalid_langloc)
        
    def test_get_conf_vals(self):
        # the expected result after parsing the config 
        result = [ "--lm", self.tmpfilename, "--port", "6000", "--verbose" ]
        # writing a random line to the config file and test that ConfigParser raises a MissingSectionHeaderError
        f = open(self.tmpfilename,'w')
        f.write("somekey = somevalue\n")
        f.close()
        self.assertRaises(MissingSectionHeaderError, Configuration._get_conf_vals, self.tmpfilename)
        # writing valid values to the config file and comparing the result to what we expect 
        f = open(self.tmpfilename,'w')
        f.write("[generic]\n")
        for key, value in self.config.iteritems():
            if value:
                f.write(key + " = " + str(value) + "\n")
            else:
                f.write(key + "\n")
        f.close()
        self.assertEqual(Configuration._get_conf_vals(self.tmpfilename), result, "_get_conf_vals doesn't create the expected list")
        
    def test_get_arg_parser(self):
        self.assertIsInstance(Configuration._get_arg_parser(), ArgumentParser, "_get_arg_parser doesn't return an instance of ArgumentParser")
        
    def test_set_data_and_set_conf(self):
        # generate and set data
        config = []
        for key, value in self.config.iteritems():
            config += ["--" + key]
            if value:
                config += [str(value)]
        Configuration.set_data(config)
        # check we can read back the data we set
        self.assertEqual(Configuration.conf_get("port"), 6000, "can't find argument values set by set_data")
        self.assertEqual(Configuration.conf_get("verbose"), True, "can't find argument values set by set_data")
        # check that the system exits when we give unrecognized arguments
        Configuration.set_data("--some values --that --dont --exist".split())
        self.assertRaises(SystemExit, Configuration._set_conf)
        
    def test_conf_get(self):
        # generate and set data
        config = []
        for key, value in self.config.iteritems():
            config += ["--" + key]
            if value:
                config += [str(value)]
        Configuration.set_data(config)
        # check we can read back the data we set
        self.assertEqual(Configuration.conf_get("port"), 6000, "can't find argument values set by set_data")
        self.assertEqual(Configuration.conf_get("lm"), self.tmpfilename, "can't find argument values set by set_data")
        self.assertEqual(Configuration.conf_get("nonexisting"), None, "conf_get doesn't return None on a non-existing param")


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()