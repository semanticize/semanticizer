# Copyright 2012-2013, University of Amsterdam. This program is free software:
# you can redistribute it and/or modify it under the terms of the GNU Lesser 
# General Public License as published by the Free Software Foundation, either 
# version 3 of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or 
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License 
# for more details.
# 
# You should have received a copy of the GNU Lesser General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>.

'''
Testsuite for the config.py module
'''
# Disable check for calling protected members
# pylint: disable-msg=W0212
# Disable check for naming conventions that disturb setUp and tearDown
# pylint: disable-msg=C0103
# Disable check for too many public methods
# pylint: disable-msg=R0904

import unittest
import config
from os import remove
from argparse import ArgumentTypeError
from argparse import ArgumentParser
from tempfile import mkstemp
from ConfigParser import MissingSectionHeaderError


class Test(unittest.TestCase):
    """Testclass for config.py"""

    def setUp(self):
        """setup the test by creating a tempfile and a test config"""
        self.tmpfile, self.tmpfilename = mkstemp()
        self.testconfig = {
                'port': 6000,
                'lmpath': self.tmpfilename,
                'verbose': None
                }

    def tearDown(self):
        """Tear down by removing the tempfile created during setup"""
        remove(self.tmpfilename)

    def test_readable_path(self):
        """Test the function that guarantees a path given in the config
        is readable"""
        valid_path = '/'
        invalid_path = '/invalid/path'
        self.assertTrue(
                config._readable_path(valid_path).endswith(valid_path),
                "_readable_path returns an unexpected value for %s" \
                % valid_path)
        self.assertRaises(ArgumentTypeError,
                          config._readable_path,
                          invalid_path)

    def test_writable_file(self):
        """Test the function that guarantees a path given in the config
        is writable"""
        valid_file = self.tmpfilename
        invalid_file = '/test/test/invalid'
        self.assertTrue(
                config._writable_file(valid_file).endswith(valid_file),
                "_writable_file returns an unexpected value for %s" \
                % valid_file)
        self.assertRaises(ArgumentTypeError,
                          config._writable_file,
                          invalid_file)

    def test_valid_absolute_url(self):
        """Test the function that guarantees a value given in the config
        is a valid URL"""
        valid_url = 'http://www.google.com:890/something?param=1&else=2'
        invalid_url = 'ha//%st||al}avista'
        self.assertEqual(
                config._valid_absolute_url(valid_url),
                valid_url,
                "_valid_absolute_url returns an unexpected value for %s" \
                % valid_url)
        self.assertRaises(ArgumentTypeError,
                          config._valid_absolute_url,
                          invalid_url)

    def test_get_conf_vals(self):
        """Test the params are being parsed as we expect"""
        # the expected result after parsing the config
        result = ["--lmpath", self.tmpfilename, "--port", "6000", "--verbose"]
        # writing a random line to the config file and test that ConfigParser
        # raises a MissingSectionHeaderError
        tmpfile = open(self.tmpfilename, 'w')
        tmpfile.write("somekey = somevalue\n")
        tmpfile.close()
        self.assertRaises(MissingSectionHeaderError,
                          config._get_conf_vals,
                          self.tmpfilename)
        # writing valid values to the config file and comparing the result to
        # what we expect
        tmpfile = open(self.tmpfilename, 'w')
        tmpfile.write("[generic]\n")
        for key, value in self.testconfig.iteritems():
            if value:
                tmpfile.write(key + " = " + str(value) + "\n")
            else:
                tmpfile.write(key + "\n")
        tmpfile.close()
        self.assertEqual(config._get_conf_vals(self.tmpfilename),
                         result,
                         "_get_conf_vals doesn't create the expected list: ")

    def test_get_arg_parser(self):
        """Test we get a valid ArgumentParser"""
        self.assertIsInstance(config._get_arg_parser(),
                              ArgumentParser,
                              "_get_arg_parser doesn't return an instance of \
                              ArgumentParser")

    def test_set_data_and_set_conf(self):
        """Test the set_data and set_conf functions"""
        # generate and set data
        configuration = []
        for key, value in self.testconfig.iteritems():
            configuration += ["--" + key]
            if value:
                configuration += [str(value)]
        config.set_data(configuration)
        # check we can read back the data we set
        self.assertEqual(config.conf_get("port"),
                         6000,
                         "can't find argument values set by set_data")
        self.assertEqual(config.conf_get("verbose"),
                         True,
                         "can't find argument values set by set_data")
        # check that the system exits when we give unrecognized arguments
        config.set_data("--some values --that --dont --exist".split())
        self.assertRaises(SystemExit, config._set_conf)

    def test_conf_get(self):
        """Test the most important function of the config module: conf_get"""
        # generate and set data
        configuration = []
        for key, value in self.testconfig.iteritems():
            configuration += ["--" + key]
            if value:
                configuration += [str(value)]
        config.set_data(configuration)
        # check we can read back the data we set
        config.conf_get("port")
        self.assertEqual(config.conf_get("port"),
                         6000,
                         "can't find argument values set by set_data")
        self.assertEqual(config.conf_get("lmpath"),
                         self.tmpfilename,
                         "can't find argument values set by set_data")
        self.assertEqual(config.conf_get("nonexisting"),
                         None,
                         "conf_get doesn't return None on a nonexisting param")


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
