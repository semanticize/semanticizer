import logging

from Configuration import conf_get
from Errors import InitError
from Semanticizer import Semanticizer
from logging.handlers import TimedRotatingFileHandler

def init_logging():
    file_handler = TimedRotatingFileHandler(conf_get("log"), when='midnight')
    file_handler.setFormatter(logging.Formatter(conf_get("logformat")))
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(conf_get("logformat")))
    if conf_get("verbose") == True:
        file_handler.setLevel(logging.DEBUG)
        stream_handler.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().addHandler(file_handler)
    logging.getLogger().addHandler(stream_handler)

if __name__ == '__main__':
    
    init_logging()
    
    server = Semanticizer()
    
    if conf_get("listlang"):
        server.list_lang(conf_get("lm"))
    else:
        try:
            server.start_server(conf_get("lm"),
                                conf_get("stopword"),
                                conf_get("langloc"),
                                conf_get("features"),
                                conf_get("scikit"),
                                conf_get("learn"),
                                conf_get("pickledir"),
                                conf_get("article"),
                                conf_get("threads"),
                                conf_get("host"),
                                conf_get("port"),
                                conf_get("verbose"),
                                conf_get("logformat"))
        except InitError as e:
            logging.getLogger().fatal("Error running Semanticizer server: %s" % e.value)