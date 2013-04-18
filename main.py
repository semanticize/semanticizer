import logging
import procpipeline
from config import conf_get
from server import Server
from logging.handlers import TimedRotatingFileHandler
from textcat import NGram
import wpm.wpmutil as wpmutil


def start_server(lm_dir,
                 langcodes,
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
    # Fetch the language models needed for the textcat language guesser
    textcat = NGram(lm_dir)
    # Initialize the pipeline
    pipeline = procpipeline.build(langcodes, feature_config)
    # Create the FlaskServer
    logging.getLogger().info("Setting up server")
    server = Server()
    server.set_debug(verbose, logformat)
    # Setup all available routes / namespaces for the HTTP server
    server.setup_all_routes(pipeline, langcodes, textcat)
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
    init_logging(conf_get("log"),
                 conf_get("verbose"),
                 conf_get("logformat"))

    # Set the datasource and init it
    wpmdata_params = conf_get('wpmdata')
    wpmutil.datasource = conf_get("wpmdatasource")
    for langcode, langdata in wpmdata_params.iteritems():
        wpmutil.get_wpmdata(langcode, langname=langdata[0], path=langdata[1])

    # Print the configuration when in debug mode
    options = conf_get()
    logging.getLogger().info("Starting with configuration:")
    for key, value in options.iteritems():
        logging.getLogger().info(key + " : " + str(value))

    # If we use learning features, configure them
    feature_conf = None
    if conf_get("features") == True:
        feature_conf = {}
        feature_conf["wpminer_url"] = conf_get("wpmurl")
        feature_conf["wpminer_numthreads"] = conf_get("wpmthreads")
        feature_conf["picklepath"] = conf_get("cachedir")
        if conf_get("scikiturl"):
            feature_conf["remote_scikit_url"] = conf_get("scikiturl")

    # Start the server
    try:
        start_server(conf_get("lmpath"),
                     conf_get("langcodes").split(','),
                     conf_get("host"),
                     conf_get("port"),
                     conf_get("verbose"),
                     conf_get("logformat"),
                     feature_conf)
    except ValueError as e:
        logging.getLogger().fatal("Error running Semanticizer server: %s" \
                                  % e.message)
