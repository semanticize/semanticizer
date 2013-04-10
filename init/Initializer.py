from processors.core import SettingsProcessor, FilterProcessor
from processors.semanticizer import SemanticizeProcessor
from processors.features import FeaturesProcessor, ArticleFeaturesProcessor, ContextFeaturesProcessor
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
    
    def __init__(self, wpminer_url, lm_dir, stopword_dir, langloc):
        """
        Create a new Semanticizer and set the logger.
        
        @param wpminer_url: The URL of the WikipediaMiner database
        @param lm_dir: The directory containing the language model files for textcat
        @param stopword_dir: The directory containing the stopword files
        @param langloc: The value of --langloc, containing info on the WikipediaMiner data
        """
        # Set the logger
        self.logger = logging.getLogger()
        # Set the arguments
        self.wpminer_url = wpminer_url
        self.lm_dir = lm_dir
        self.stopword_dir = stopword_dir
        self.langloc = langloc
        # Initialize the optional configuration params
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
        Start a SemanticizerFlaskServer with all processors loaded into the pipeline.
        
        @param verbose: Set whether the Flask server should be verbose
        @param logformat: The logformat used by the Flask server
        """
        # Fetch the language models needed for the textcat language guesser
        textcat = self._load_textcat(self.lm_dir)
        # Fetch the stopwords from the stopword directory
        stopwords = self._load_stopwords(self.stopword_dir)
        # Load the languages and corresponding WikiPedia ids from the specified language location
        uniqlangs, wikipedia_ids = self._load_language(self.langloc, textcat.listLangs(), stopwords)
        # Initialize the pipeline
        pipeline = self._load_pipeline(uniqlangs, wikipedia_ids)
        # Create the FlaskServer
        server = Server()
        server.set_debug(verbose, logformat)
        # Setup all available routes / namespaces for the HTTP server
        server.setup_all_routes(pipeline, stopwords, uniqlangs, textcat)
        # And finally, start the thing
        server.start(self.serverhost, self.serverport)
        
    def _load_textcat(self, lm_dir):
        """
        Load the language models (lm files) in the textcat language guesser. Returns a classifier.
        
        @param lm_dir: The path to the language model files
        """
        self.logger.info("Loading ngram model")
        textcat = NGram(lm_dir)
        return textcat
    
    def _load_stopwords(self, stopword_dir):
        """
        Load all available stopword files in the given stopword dir. We assume all files in the dir
        are stopword files, that they are named <FILENAME>.<LANGCODE>, and that they're line-based.
        Returns a dictionary that contains a dictionary of stopwords, all initialized to 0.
        
        @param stopword_dir: The path to the stopword files
        """
        self.logger.info("Loading stopwords")
        stopwords = {}
        for fname in glob.glob(os.path.join(stopword_dir, "stopwords.*")):
            langcode = os.path.split(fname)[-1].split(".")[-1]
            stopwords[langcode] = {}
            for line in codecs.open(fname, 'r', 'utf-8'):
                stopwords[langcode][line.strip()] = 0
        return stopwords
            
    def _load_language(self, langloc, available_lang, stopwords):
        """
        Check that we have stopwords for the given language and that the language code
        is available in our textcat language guesser. Also filter out duplicate languages.
        Returns two dictionaries.
        
        @param langloc: The "langloc" argument / configuration param
        @param available_lang: The available languages in textcat
        @param stopwords: List of languages we have stopwords for
        @return: two dictionaries
        @todo: more or less the same data twice in the return seems overhead
        """
        uniqlangs = {}
        wikipedia_ids = {}
        for lang, langcode, loc in langloc:
            if not langcode in stopwords:
                raise ValueError("No stopwords for \"" + langcode + "\", stopwords are available for " + ", ".join(sorted(stopwords)))
            if not lang in available_lang:
                raise ValueError("Language \"" + lang + "\" is not available, available languages are: " + ", ".join(sorted(available_lang)))
            if langcode in uniqlangs:
                continue
            wikipedia_ids[langcode] = loc.split('/')[-2]
            uniqlangs[langcode] = [lang, loc]
        return (uniqlangs, wikipedia_ids)
    
    
    def _load_pipeline(self, uniqlangs, wikipedia_ids):
        """
        Initialize the pipeline.
        
        @param uniqlangs: A list of supported languages
        @param wikipedia_ids: A list with the wikipedia ids of the supported languages
        @return: The pipeline
        @todo: See todo at _load_languages
        """
        pipeline = []
        semanticize_processor = self._load_semanticize_processor(uniqlangs)
        pipeline.append(("Settings", SettingsProcessor()))
        pipeline.append(("Semanticize", semanticize_processor))
        pipeline.append(("Filter", FilterProcessor()))
        if self.include_features == True:
            self._load_features(pipeline, semanticize_processor, wikipedia_ids, uniqlangs)
        pipeline.append(("AddImage", AddImageProcessor()))
        return pipeline
    
    def _load_semanticize_processor(self, uniqlangs):
        """
        Load the Semanticizer.
        
        @param uniqlangs: the list of unique languages
        @return: a configured instance of SemanticizeProcessor
        @see: processors.SemanticizeProcessor
        """
        semanticize_processor = SemanticizeProcessor()
        start = time.time()
        self.logger.info("Loading semanticizers for langcode(s) " + ", ".join(uniqlangs.keys()))
        semanticize_processor.load_languages(uniqlangs)
        self.logger.info("Loading semanticizers took %.2f seconds." % (time.time() - start))
        return semanticize_processor
    
    def _load_features(self, pipeline, semanticize_processor, wikipedia_ids, uniqlangs):
        """
        Load all features into the pipeline
        
        @param pipeline: A reference to the pipeline
        @param semanticize_processor: A reference to the semanticize processor
        @param wikipedia_ids: A list of Wikipedia ids
        @param uniqlangs: A list of unique languages
        """
        self.logger.info("Loading features...")
        start = time.time()
        pipeline.append(("Features", FeaturesProcessor(semanticize_processor, self.picklepath)))
        pipeline.append(("Articles", ArticlesProcessor(wikipedia_ids, self.wpminer_url, self.wpminer_numthreads, self.picklepath)))
        pipeline.append(("Statistics", StatisticsProcessor(uniqlangs.keys(), self.wpminer_numthreads, self.picklepath)))
        pipeline.append(("ArticleFeatures", ArticleFeaturesProcessor()))
        pipeline.append(("ContextFeatures", ContextFeaturesProcessor()))
        self.logger.info("Loading features took %.2f seconds." % (time.time() - start))
        if not self.remote_scikit_url:
            pipeline.append(("Learning", LearningProcessor()))
        else:
            pipeline.append(("Learning", LearningProcessor(self.remote_scikit_url)))