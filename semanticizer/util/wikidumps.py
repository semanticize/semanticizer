# Copyright 2012 University of Amsterdam
# Copyright 2014 Netherlands eScience Center
# Written by Lars Buitinck.

"""Parsing utilities for Wikipedia database dumps."""

from __future__ import print_function

import re
import xml.etree.ElementTree as etree   # don't use LXML, it's slower (!)


def _get_namespace(tag):
    try:
        namespace = re.match(r"^{(.*?)}", tag).group(1)
    except AttributeError:
        namespace = ''
    if not namespace.startswith("http://www.mediawiki.org/xml/export-"):
        raise ValueError("namespace %r not recognized as MediaWiki dump"
                         % namespace)
    return namespace


def extract_pages(f):
    """Extract pages from Wikimedia database dump.

    Parameters
    ----------
    f : file-like or str
        Handle on Wikimedia article dump. May be any type supported by
        etree.iterparse.

    Returns
    -------
    pages : iterable over (int, string, string)
        Generates (page_id, title, content) triples.
        In Python 2.x, may produce either str or unicode strings.
    """
    elems = (elem for _, elem in etree.iterparse(f, events=["end"]))

    # We can't rely on the namespace for database dumps, since it's changed
    # it every time a small modification to the format is made. So, determine
    # those from the first element we find, which will be part of the metadata,
    # and construct element paths.
    elem = next(elems)
    namespace = _get_namespace(elem.tag)
    ns_mapping = {"ns": namespace}
    page_tag = "{%(ns)s}page" % ns_mapping
    text_path = "./{%(ns)s}revision/{%(ns)s}text" % ns_mapping
    id_path = "./{%(ns)s}id" % ns_mapping
    title_path = "./{%(ns)s}title" % ns_mapping

    for elem in elems:
        if elem.tag == page_tag:
            text = elem.find(text_path).text
            if text is None:
                # Empty article; these occur in Wikinews dumps.
                continue
            yield (int(elem.find(id_path).text),
                   elem.find(title_path).text,
                   text)

            # Prune the element tree, as per
            # http://www.ibm.com/developerworks/xml/library/x-hiperfparse/
            # We do this only for <page>s, since we need to inspect the
            # ./revision/text element. That shouldn't matter since the pages
            # comprise the bulk of the file.
            elem.clear()


if __name__ == "__main__":
    # Test; will write article info + prefix of content to stdout
    import sys

    if len(sys.argv) > 1:
        print("usage: %s; will read from standard input" % sys.argv[0],
              file=sys.stderr)
        sys.exit(1)

    for pageid, title, text in extract_pages(sys.stdin):
        title = title.encode("utf-8")
        text = text[:40].replace("\n", "_").encode("utf-8")
        print("%d '%s' (%s)" % (pageid, title, text))
