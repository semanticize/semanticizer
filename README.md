Semanticizer
============

Created in 2012 by [Daan Odijk](http://staff.science.uva.nl/~dodijk/) at
[ILPS](http://ilps.science.uva.nl/). Received contributions from 
[Lars Buitinck](http://staff.science.uva.nl/~buitinck/), 
[David Graus](http://graus.nu/), 
[Tom Kenter](http://staff.science.uva.nl/~tkenter1/), 
[Edgar Meij](http://edgar.meij.pro/), 
[Daan Odijk](http://staff.science.uva.nl/~dodijk/), 
[Anne Schuth](http://www.anneschuth.nl/).

The algorithms are described in the upcoming 
[OAIR2013 article](http://ilps.science.uva.nl/biblio/feeding-second-screen-semantic-linking-based-subtitles).

The [code](https://github.com/semanticize/semanticizer/) is currently not publicly
available, but a release is planned for 2013. If you are interested in this, contact 
[Daan](http://staff.science.uva.nl/~dodijk/).

If you want to dive into the code, start at Main.py.

## Requirements

1. The software has been tested with Python 2.7.3 on OS X 2.8

2. The following Python modules need to be installed (I used pip):
 * nltk
 * python-Levenshtein
 * networkx
 * lxml
 * flask
 * scikit-learn
 * scipy (see 6)

3. Create semanticizer/logs folder

4. Run SemanticizerFlaskServer with link to wikipedia data (dload from http://semanticize.uva.nl/nl.tgz):

    --langloc dutch nl nlwiki-20111104

5. In order to work with the scikit features you need to install the scikit-learn and scipy packages. Before installing scipy you need to have [swig](http://www.swig.org/download.html) installed. See INSTALL for instructions. (configure, make, make install)