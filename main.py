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
import procpipeline
from config import conf_get
from server import Server
from logging.handlers import TimedRotatingFileHandler
import wpm.wpmutil as wpmutil


def start_server(langcodes,
                 host,
                 port,
                 verbose=False,
                 logformat='[%(asctime)-15s][%(levelname)s][%(module)s][%(pathname)s:%(lineno)d]: %(message)s',
                 feature_config=None):
    """
    Start a SemanticizerFlaskServer with all processors loaded into the
    pipeline.

    @param verbose: Set whether the Flask server should be verbose
    @param logformat: The logformat used by the Flask server
    """
    # Initialize the pipeline
    pipeline = procpipeline.build(langcodes, feature_config)
    # Create the FlaskServer
    logging.getLogger().info("Setting up server")
    server = Server()
    server.set_debug(verbose, logformat)
    # Setup all available routes / namespaces for the HTTP server
    server.setup_all_routes(pipeline, langcodes)
    logging.getLogger().info("Done setting up server, now starting...")
    # And finally, start the thing
    server.start(host, port)


def init_logging(log, verbose, logformat):
    """
    A convencience function that initializes the logging framework by setting
    the path to the log, verbosity, and the logformat.
    """
    file_handler = TimedRotatingFileHandler(log, when='midnight')
    file_handler.setFormatter(logging.Formatter(logformat))
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(logformat))
    if verbose == True:
        file_handler.setLevel(logging.DEBUG)
        stream_handler.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().addHandler(file_handler)
    logging.getLogger().addHandler(stream_handler)


if __name__ == '__main__':
    # Init the logger
    init_logging(conf_get('logging', 'path'),
                 conf_get('logging', 'verbose'),
                 conf_get('logging', 'format'))

    # Set the datasource and init it
    wpmlangs = conf_get('wpm', 'languages')
    wpmutil.init_datasource(wpmlangs)

    # If we use learning features, configure them
    feature_conf = None
    if conf_get('linkprocs', 'includefeatures') == True:
        feature_conf = {}
        feature_conf["wpminer_url"] = conf_get('wpm', 'bdburl')
        feature_conf["wpminer_numthreads"] = conf_get('wpm', 'threads')
        feature_conf["picklepath"] = conf_get('misc', 'tempdir')
        try:
            feature_conf["remote_scikit_url"] = conf_get('scikit', 'url')
        except KeyError:
            pass

    # Start the server
    try:
        start_server(conf_get('wpm', 'languages').keys(),
                     conf_get('server', 'host'),
                     conf_get('server', 'port'),
                     conf_get('logging', 'verbose'),
                     conf_get('logging', 'format'),
                     feature_conf)
    except ValueError as e:
        logging.getLogger().fatal("Error running Semanticizer server: %s" \
                                  % e.message)
