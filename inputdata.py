import os
import glob
import codecs
import logging

from textcat import NGram


def load_textcat(lm_dir):
    """
    Load the language models (lm files) in the textcat language guesser.
    Returns a classifier.

    @param lm_dir: Path to language model (.lm) files
    """
    logging.getLogger().info("Loading ngram model")
    textcat = NGram(lm_dir)
    logging.getLogger().info("Done loading ngram model")
    return textcat


def load_stopwords(stopword_dir):
    """
    Load all available stopword files in the given stopword dir. We assume
    all files in the dir are stopword files, that they are named
    <FILENAME>.<LANGCODE>, and that they're line-based. Returns a
    dictionary that contains a dictionary of stopwords, all initialized to
    0 (zero).

    @param stopword_dir: Path to the stopword files
    """
    logging.getLogger().info("Loading stopwords")
    stopwords = {}
    for fname in glob.glob(os.path.join(stopword_dir, "stopwords.*")):
        langcode = os.path.split(fname)[-1].split(".")[-1]
        stopwords[langcode] = {}
        for line in codecs.open(fname, 'r', 'utf-8'):
            stopwords[langcode][line.strip()] = 0
    logging.getLogger().info("Done loading stopwords")
    return stopwords
