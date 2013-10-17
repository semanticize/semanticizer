# -*- coding: utf-8 -*-
#
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

import re

# Kan ook met de hand...:(\A|\s|\'|"|\.|\,|:|;|!|\?)
#                        (?=(\s|\'|"|\.|\,|:|;|!|\?|\'s|\Z)
# reNonWordChars = re.compile('(?u)\W+', re.UNICODE)

# We took the reg exp from scikit-learn:
# https://github.com/scikit-learn/scikit-learn/blob/master/sklearn/feature_extraction/text.py
reTokenPattern = re.compile(r"(?u)\b\w\w+\b", re.UNICODE)

def ngramToPattern(sNgram):
    return ngramsToPattern([sNgram])

def ngramsToPattern(aNgrams):
    #import sys
    #print >> sys.stderr, "n-grams: '%s'" % aNgrams
    try:
        # So this reads, inside out:
        # Replace all white space by a single space and re.escape that.
        # Replace the (by now escaped) spaces by '\s+'s and join the different
        # n-grams by pipes ('|')
        # 
        sNgrams = '|'.join([re.escape(re.sub('\s+', ' ', x)).replace('\\ ', '\s+')  for x in aNgrams])
        reNgrams = re.compile('((\A|\W)(' + sNgrams + ')(?=\W|\Z))',
                              flags=re.UNICODE|re.IGNORECASE)
    except OverflowError:
        # Some articles have such a ridiculous number of inlink anchors that
        # the regular expression gets too big.
        # This doesn't happen if we make it a bit stricter....
        # So, if that happens we make the same expression but we do not replace
        # the spaces by \s+'s
        sNgrams = '|'.join([re.escape(re.sub('\s+', ' ', x)) for x in aNgrams])
        reNgrams = re.compile('((\A|\W)(' + sNgrams + ')(?=\W|\Z))',
                              flags=re.UNICODE|re.IGNORECASE)
    return reNgrams

# For one word
def findNgramInText(sNgram, sText):
    return findNgramsInText([sNgram], sText)

# For several words
def findNgramsInText(aNgrams, sText):
    # A check beforehand because an empty array will lead to a pattern that
    # matches empty lines, double spaces, etc....
    if len(aNgrams) == 0:
        return []
    return re.findall(ngramsToPattern(aNgrams), sText)

if __name__ == "__main__":
    sText = u"aap noot mies\nwim jüf duif “Noot” roos ühalloü"

    aMatches = findNgramInText(u'aap', sText)
    print "%s" % aMatches

    aMatches = findNgramInText(u'hallo', sText)
    print "%s" % aMatches

    aMatches = findNgramsInText([u'mies wim', u'noot'], sText)
    print "%s" % aMatches
