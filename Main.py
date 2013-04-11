import logging

from Configuration import conf_get
from init.Initializer import Initializer
from logging.handlers import TimedRotatingFileHandler

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
    
    # Create the server
    server = Initializer(conf_get("article"),
                         conf_get("lm"),
                         conf_get("stopword"),
                         conf_get("langloc"))
    
    # Configure the server
    if conf_get("learn"):
        server.remote_scikit_url = conf_get("learn")
    
    if conf_get("threads"):
        server.wpminer_numthreads = conf_get("threads")
    
    if conf_get("pickledir"):
        server.picklepath = conf_get("pickledir")
    
    if conf_get("host"):
        server.serverhost = conf_get("host")
    
    if conf_get("port"):
        server.serverport = conf_get("port")

    server.include_features = conf_get("features")

    # Start the server
    try:
        server.start_server(conf_get("verbose"),
                            conf_get("logformat"))
    except AssertionError as e:
        logging.getLogger().fatal("Error running Semanticizer server: %s" % e.message)