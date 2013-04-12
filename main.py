import logging
import inputdata
import procpipeline

from config import conf_get
from server import Server
from logging.handlers import TimedRotatingFileHandler


def start_server(lm_dir,
                 stopword_dir,
                 wp_ids,
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
    textcat = inputdata.load_textcat(lm_dir)
    # Fetch the stopwords from the stopword directory
    stopwords = inputdata.load_stopwords(stopword_dir)
    # Initialize the pipeline
    pipeline = procpipeline.build(wp_ids, feature_config)
    # Create the FlaskServer
    logging.getLogger().info("Setting up server")
    server = Server()
    server.set_debug(verbose, logformat)
    # Setup all available routes / namespaces for the HTTP server
    server.setup_all_routes(pipeline, wp_ids, stopwords, textcat)
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

    # Print the configuration when in debug mode
    options = conf_get()
    logging.getLogger().info("Starting with configuration:")
    for key, value in options.iteritems():
        logging.getLogger().info(key + " : " + str(value))

    # If we use learning features, configure them
    feature_config = None
    if conf_get("features") == True:
        feature_config = {}
        feature_config["wpminer_url"] = conf_get("article")
        feature_config["wpminer_numthreads"] = conf_get("threads")
        feature_config["picklepath"] = conf_get("pickledir")
        if conf_get("learn"):
            feature_config["remote_scikit_url"] = conf_get("learn")

    # Start the server
    try:
        start_server(conf_get("lm"),
                     conf_get("stopword"),
                     conf_get("langloc"),
                     conf_get("host"),
                     conf_get("port"),
                     conf_get("verbose"),
                     conf_get("logformat"))
    except ValueError as e:
        logging.getLogger().fatal("Error running Semanticizer server: %s" \
                                  % e.message)
