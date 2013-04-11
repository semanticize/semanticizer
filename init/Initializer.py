from processors.core import SettingsProcessor, FilterProcessor
from processors.semanticizer import SemanticizeProcessor
from processors.features import FeaturesProcessor, ArticleFeaturesProcessor, \
                                ContextFeaturesProcessor
from processors.external import ArticlesProcessor, StatisticsProcessor
from processors.learning import LearningProcessor
from processors.image import AddImageProcessor
from init.Server import Server
from textcat import NGram
from tempfile import gettempdir

import logging
import os
import glob
import codecs
import time


class Initializer(object):
    """
    This class is can be used to initialize all processors.*, adding them
    to the pipeline, and starting the FlaskServer.
    """

    def __init__(self, wpminer_url=None, lm_dir=None,
                 stopword_dir=None, langloc=None):
        """
        Create a new Semanticizer and set the logger.

        @param wpminer_url: The URL of the WikipediaMiner database
        @param lm_dir: The directory containing the language model files for \
                       textcat
        @param stopword_dir: The directory containing the stopword files
        @param langloc: The value of --langloc, containing info on the \
                        WikipediaMiner data
        """
        # Set the logger
        self.logger = logging.getLogger()
        # Set the arguments
        self.wpminer_url = wpminer_url
        self.lm_dir = lm_dir
        self.stopword_dir = stopword_dir
        self.langloc = langloc
        # Initialize the optional configuration params with defaults
        self.remote_scikit_url = None
        self.wpminer_numthreads = 1
        self.serverhost = None
        self.serverport = None
        self.picklepath = gettempdir()
        self.include_features = False

    def start_server(self,
                     verbose=False,
                     logformat='[%(asctime)-15s][%(levelname)s][%(module)s][%(pathname)s:%(lineno)d]: %(message)s' ):
        """
        Start a SemanticizerFlaskServer with all processors loaded into the
        pipeline.

        @param verbose: Set whether the Flask server should be verbose
        @param logformat: The logformat used by the Flask server
        """
        # Fetch the language models needed for the textcat language guesser
        textcat = self._load_textcat()
        # Fetch the stopwords from the stopword directory
        stopwords = self._load_stopwords()
        # Load the languages and corresponding WikiPedia ids from the specified
        # language location
        wikipedia_ids = self._load_wp_languages()
        # Initialize the pipeline
        pipeline = self._load_pipeline(wikipedia_ids)
        # Create the FlaskServer
        self.logger.info("Setting up server")
        server = Server()
        server.set_debug(verbose, logformat)
        # Setup all available routes / namespaces for the HTTP server
        server.setup_all_routes(pipeline, stopwords, wikipedia_ids, textcat)
        self.logger.info("Done setting up server, now starting...")
        # And finally, start the thing
        server.start(self.serverhost, self.serverport)

    def _load_textcat(self):
        """
        Load the language models (lm files) in the textcat language guesser.
        Returns a classifier.
        """
        self.logger.info("Loading ngram model")
        textcat = NGram(self.lm_dir)
        self.logger.info("Done loading ngram model")
        return textcat

    def _load_stopwords(self):
        """
        Load all available stopword files in the given stopword dir. We assume
        all files in the dir are stopword files, that they are named
        <FILENAME>.<LANGCODE>, and that they're line-based. Returns a
        dictionary that contains a dictionary of stopwords, all initialized to
        0 (zero).
        """
        self.logger.info("Loading stopwords")
        stopwords = {}
        for fname in glob.glob(os.path.join(self.stopword_dir, "stopwords.*")):
            langcode = os.path.split(fname)[-1].split(".")[-1]
            stopwords[langcode] = {}
            for line in codecs.open(fname, 'r', 'utf-8'):
                stopwords[langcode][line.strip()] = 0
        self.logger.info("Done loading stopwords")
        return stopwords

    def _load_wp_languages(self):
        """
        Transform the langloc argument / config param into a dictionary with
        unique language codes.

        @return: a dictionary with the language codes as keys, and lists with \
                 the corresponsing language name and path as values
        """
        self.logger.info("Loading wikipedia languages")
        uniqlangs = {}
        for lang, langcode, loc in self.langloc:
            if langcode in uniqlangs:
                continue
            uniqlangs[langcode] = [lang, loc]
        self.logger.info("Done loading wikipedia languages")
        return uniqlangs

    def _load_pipeline(self, uniqlangs):
        """
        Initialize the pipeline.

        @param uniqlangs: A list of supported languages
        @param wikipedia_ids: A list with the wikipedia ids of the supported \
                              languages
        @return: The pipeline
        @todo: See todo at _load_languages
        """
        self.logger.info("Initializing pipeline")
        pipeline = []
        semanticize_processor = self._load_semanticize_processor(uniqlangs)
        pipeline.append(("Settings", SettingsProcessor()))
        pipeline.append(("Semanticize", semanticize_processor))
        pipeline.append(("Filter", FilterProcessor()))
        if self.include_features == True:
            self._load_features(pipeline, semanticize_processor, uniqlangs)
        pipeline.append(("AddImage", AddImageProcessor()))
        self.logger.info("Done initializing pipeline")
        return pipeline

    def _load_semanticize_processor(self, uniqlangs):
        """
        Load the Semanticizer.

        @param uniqlangs: the list of unique languages
        @return: a configured instance of SemanticizeProcessor
        @see: processors.SemanticizeProcessor
        """
        self.logger.info("Loading semanticizer")
        semanticize_processor = SemanticizeProcessor()
        start = time.time()
        self.logger.info("Loading semanticizers for langcode(s) "
                         + ", ".join(uniqlangs.keys()))
        semanticize_processor.load_languages(uniqlangs)
        self.logger.info("Loading semanticizers took %.2f seconds." \
                         % (time.time() - start))
        self.logger.info("Done loading semanticizer")
        return semanticize_processor

    def _load_features(self, pipeline, semanticize_processor, wikipedia_ids):
        """
        Load all features into the pipeline

        @param pipeline: A reference to the pipeline
        @param semanticize_processor: A reference to the semanticize processor
        @param wikipedia_ids: Wikipedia ids & data
        """
        self.logger.info("Loading features")
        assert self.wpminer_url != None, \
               "Initializer.wpminer_url needs to be set to include features"
        start = time.time()
        pipeline.append(("Features", FeaturesProcessor(semanticize_processor,
                                                       self.picklepath)))
        pipeline.append(("Articles", ArticlesProcessor(wikipedia_ids,
                                                       self.wpminer_url,
                                                       self.wpminer_numthreads,
                                                       self.picklepath)))
        pipeline.append(("Statistics", StatisticsProcessor( \
                                                    wikipedia_ids.keys(),
                                                    self.wpminer_numthreads,
                                                    self.picklepath)))
        pipeline.append(("ArticleFeatures", ArticleFeaturesProcessor()))
        pipeline.append(("ContextFeatures", ContextFeaturesProcessor()))
        self.logger.info("Loading features took %.2f seconds." \
                         % (time.time() - start))
        if self.remote_scikit_url == None:
            pipeline.append(("Learning", LearningProcessor()))
        else:
            pipeline.append(("Learning", \
                             LearningProcessor(self.remote_scikit_url)))
        self.logger.info("Done loading features")
