#!/usr/bin/env python

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
import logging
from logging.handlers import TimedRotatingFileHandler
import sys

from semanticizer import procpipeline
from semanticizer.config import config_get
from semanticizer.server import Server
from semanticizer.wpm.data import init_datasource

def init_wsgi_server(langcodes,
                 verbose=False,
                 logformat='[%(asctime)-15s][%(levelname)s][%(module)s][%(pathname)s:%(lineno)d]: %(message)s',
                 use_features=False,
                 debug=False):
    """
    Start a SemanticizerFlaskServer with all processors loaded into the
    pipeline.

    @param verbose: Set whether the Flask server should be verbose
    @param logformat: The logformat used by the Flask server
    """
    # Initialize the pipeline
    pipeline = procpipeline.build(langcodes, use_features, debug=debug)
    # Create the FlaskServer
    logging.getLogger().info("Setting up server")
    server = Server()
    server.set_debug(verbose, logformat)
    # Setup all available routes / namespaces for the HTTP server
    server.setup_all_routes(pipeline, langcodes)
    logging.getLogger().info("Done setting up server, now starting...")
    # And finally, start the thing
    return server.app

def init_logging(log, verbose, logformat):
    """
    A convencience function that initializes the logging framework by setting
    the path to the log, verbosity, and the logformat.
    """
    root = logging.getLogger()
    formatter = logging.Formatter(logformat)
    
    file_handler = TimedRotatingFileHandler(log, when='midnight')
    stream_handler = logging.StreamHandler(sys.stdout)

    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    if verbose == True:
        root.setLevel(logging.DEBUG)
        
    root.addHandler(stream_handler)  
    root.addHandler(file_handler) 

# Init the logger
init_logging(config_get(('logging', 'path'), 'log.txt'),
             config_get(('logging', 'verbose'), False),
             config_get(('logging', 'format'), None))

# Set the datasource and init it
wpmlangs = config_get(('wpm', 'languages'))
init_datasource(wpmlangs)

# Init the server
application = init_wsgi_server(config_get(('wpm', 'languages')).keys(),
                 config_get(('logging', 'verbose'), False),
                 config_get(('logging', 'format'), None),
                 config_get(('linkprocs', 'includefeatures'), False),
                 config_get(('server', 'debug'), False))

# debug middleware for wsgi errors
#import paste 
#from paste.exceptions.errormiddleware import ErrorMiddleware
#application = ErrorMiddleware(application, debug=True)