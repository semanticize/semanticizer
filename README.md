Semanticizer
============

The Semanticizer is a web service application for semantic linking
created in 2012 by [Daan Odijk](http://staff.science.uva.nl/~dodijk/) at
[ILPS](http://ilps.science.uva.nl/) (University of Amsterdam). 

This project since received contributions from (in alphabetical order): 
[Lars Buitinck](http://staff.science.uva.nl/~buitinck/), 
[David Graus](http://graus.nu/), 
[Tom Kenter](http://staff.science.uva.nl/~tkenter1/), 
[Evert Lammerts](http://www.evertlammerts.nl/), 
[Edgar Meij](http://edgar.meij.pro/), 
[Daan Odijk](http://staff.science.uva.nl/~dodijk/), 
[Anne Schuth](http://www.anneschuth.nl/) and 
[Isaac Sijaranamual](http://nl.linkedin.com/pub/isaac-sijaranamual/).

The algorithms for this webservice are developed for and described in a
OAIR2013 publication on [Feeding the Second Screen](http://ilps.science.uva.nl/biblio/feeding-second-screen-semantic-linking-based-subtitles) by 
[Daan Odijk](http://staff.science.uva.nl/~dodijk/), 
[Edgar Meij](http://edgar.meij.pro/) and 
[Maarten de Rijke](http://staff.science.uva.nl/~mdr/). 
Part of this research was inspired by earlier ILPS publications: 
[Adding Semantics to Microblog Posts](http://ilps.science.uva.nl/biblio/adding-semantics-microblog-posts) 
and [Mapping Queries To The Linking Open Data Cloud](http://ilps.science.uva.nl/node/889).
If you use this webservice for your own research, please include a reference 
to any of these articles.


The [online documentation](http://semanticize.uva.nl/doc/) 
describes how to use the Semanticizer Web API. This [REST](http://en.wikipedia.org/wiki/Representational_state_transfer)-like web service returns [JSON](http://www.json.org/) and is exposed to public at: http://semanticize.uva.nl/api/. Currently an access key for the webservice is not needed.

The [code](https://github.com/semanticize/semanticizer/) is released under LGPL license. If you are have any questions, contact 
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
 * redis (optional, see point 3)
 * scikit-learn (optional, see point 5)
 * scipy (optional, see point 5)
 * mock (optional, used by the tests)
 
3. A Redis server needs to be set up and running.
(dload from http://semanticize.uva.nl/nl.tgz)

4. Run SemanticizerFlaskServer with link to wikipedia data:

    --langloc dutch nl nlwiki-20111104

5. In order to work with the scikit features you need to install the scikit-learn and scipy packages. Before installing scipy you need to have [swig](http://www.swig.org/download.html) installed. See INSTALL for instructions. (configure, make, make install).

## License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>.
