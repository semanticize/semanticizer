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

import time
import logging

from .processors.core import SettingsProcessor, FilterProcessor
from .processors.semanticizer import SemanticizeProcessor
from .processors.features import FeaturesProcessor, ArticleFeaturesProcessor, \
                                 ContextFeaturesProcessor
from .processors.multiple import MultipleEntityFeaturesProcessor
from .processors.external import ArticlesProcessor, StatisticsProcessor
from .processors.learning import LearningProcessor
from .processors.image import AddImageProcessor

from .config import config_get


def build(langcodes, use_features=False, debug=False):
    """
    Initialize the pipeline.

    @param wikipedia_ids: A list with all loaded wikipedia ids
    @return: The pipeline
    @todo: See todo at _load_languages
    """
    logging.getLogger().info("Initializing pipeline")
    pipeline = []
    if 'max_ngram_length' in config_get('semanticize', {}):
        max_ngram_length = config_get(('semanticize', 'max_ngram_length'))
    else:
        max_ngram_length = None
    semanticize_processor = _load_semanticize_processor(langcodes,
                                                        max_ngram_length,
                                                        debug=debug)
    settings = config_get("settings", {})
    pipeline.append(("Settings", SettingsProcessor(settings)))
    pipeline.append(("Semanticize", semanticize_processor))
    pipeline.append(("Filter", FilterProcessor()))
    if use_features:
        _load_features(pipeline, langcodes)
    pipeline.append(("AddImage", AddImageProcessor()))
    logging.getLogger().info("Done initializing pipeline")
    return pipeline


def _load_semanticize_processor(langcodes, max_ngram_length=None, debug=False):
    """
    Load the Semanticizer.

    @param wikipedia_ids: A list with all loaded wikipedia ids
    @return: a configured instance of SemanticizeProcessor
    @see: processors.SemanticizeProcessor
    """
    logging.getLogger().info("Loading semanticizer")
    semanticize_processor = SemanticizeProcessor(debug=debug)
    start = time.time()
    logging.getLogger().info("Loading semanticizers for langcode(s) "
                     + ", ".join(langcodes))
    semanticize_processor.load_languages(langcodes, max_ngram_length)
    logging.getLogger().info("Loading semanticizers took %.2f seconds." \
                     % (time.time() - start))
    logging.getLogger().info("Done loading semanticizer")
    return semanticize_processor


def _load_features(pipeline, langcodes):
    """
    Load all features into the pipeline

    @param pipeline: A reference to the pipeline
    @param semanticize_processor: A reference to the semanticize processor
    @param wikipedia_ids: Wikipedia ids & data
    """
    logging.getLogger().info("Loading features")
    start = time.time()
    pipeline.append(("Features",
                     FeaturesProcessor(langcodes)))
    pipeline.append(("Articles",
                     ArticlesProcessor(langcodes,
                                       config_get(('wpm', 'bdburl')),
                                       config_get(('wpm', 'threads'), 1),
                                       config_get(('misc', 'tempdir')))))
    pipeline.append(("Statistics",
                     StatisticsProcessor(langcodes,
                                         config_get(('wpm', 'threads'), 1),
                                         config_get(('misc', 'tempdir')))))
    pipeline.append(("ArticleFeatures", ArticleFeaturesProcessor()))
    pipeline.append(("MultipleFeatures", MultipleEntityFeaturesProcessor()))
    pipeline.append(("ContextFeatures", ContextFeaturesProcessor()))
    logging.getLogger().info("Loading features took %.2f seconds." \
                      % (time.time() - start))
    model_dir = config_get(('learning', 'model_dir'), \
                           config_get(('misc', 'tempdir')))
    pipeline.append(("Learning", LearningProcessor(model_dir)))
    logging.getLogger().info("Done loading features")
