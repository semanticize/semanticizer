#!/usr/bin/env python

# Copyright (c) 2006 Thomas Mangin

#This program is distributed under Gnu General Public License 
#(cf. the file COPYING in distribution). Alternatively, you can use
#the program under the conditions of the Artistic License (as Perl).

#This program is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 2 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import re
from exceptions import KeyboardInterrupt

nb_ngrams = 400

class _NGram:
    def __init__ (self,arg={}):
        t = type(arg)
        if t == type(""):
            self.addText(arg)
            self.normalise()
        elif t == type({}):
            self.ngrams = arg
            self.normalise()
        else:
            self.ngrams = dict()

    def addText (self,text):
        ngrams = dict()
        
        text = text.replace('\n',' ')
        text = re.sub('\s+',' ',text)
        words = text.split(' ')

        for word in words:
            word = '_'+word+'_'
            size = len(word)
            for i in xrange(size):
                for s in (1,2,3,4):
                    sub = word[i:i+s]
                    #print "[",sub,"]"
                    if not ngrams.has_key(sub):
                        ngrams[sub] = 0
                    ngrams[sub] += 1

                    if i+s >= size:
                        break
        self.ngrams = ngrams
        return self

    def sorted (self):
        sorted = [(self.ngrams[k],k) for k in self.ngrams.keys()]
        sorted.sort()
        sorted.reverse()
        sorted = sorted[:nb_ngrams]
        return sorted

    def normalise (self):
        count = 0
        ngrams = dict()
        for v,k in self.sorted():
            ngrams[k] = count
            count += 1

        self.ngrams = ngrams
        return self

    def addValues (self,key,value):
        self.ngrams[key] = value
        return self

    def compare (self,ngram):
        d = 0
        ngrams = ngram.ngrams
        for k in self.ngrams.keys():
            if ngrams.has_key(k):
                d += abs(ngrams[k] - self.ngrams[k])
            else:
                d += nb_ngrams
        return d


import os
import glob

class NGram:
    def __init__ (self,folder,ext='.lm'):
        self.ngrams = dict()
        folder = os.path.join(folder,'*'+ext)
        size = len(ext) 
        count = 0
        
        for fname in glob.glob(os.path.normcase(folder)):
            count += 1
            lang = os.path.split(fname)[-1][:-size]
            ngrams = dict()
            file = open(fname,'r')
        
            for line in file.readlines():
                parts = line[:-1].split('\t ')
                if len(parts) != 2:
                    raise ValueError("invalid language file %s line : %s" % (fname,parts))
                try:
                    ngrams[parts[0]] = int(parts[1])
                except KeyboardInterrupt:
                    raise
                except:
                    raise ValueError("invalid language file %s line : %s" % (fname,parts))
                    
            if len(ngrams.keys()):
                self.ngrams[lang] = _NGram(ngrams)
            
            file.close()
    
        if not count:
            raise ValueError("no language files found")

    def classify (self,text):
        ngram = _NGram(text)
        r = 'guess'

        langs = self.ngrams.keys()
        r = langs.pop()
        min = self.ngrams[r].compare(ngram)

        for lang in langs:
            d = self.ngrams[lang].compare(ngram)
            if d < min:
                min = d
                r = lang

        return r

class Generate:
    def __init__ (self,folder,ext='.txt'):
        self.ngrams = dict()
        folder = os.path.join(folder,'*'+ext)
        size = len(ext)
        count = 0
        
        for fname in glob.glob(os.path.normcase(folder)):
            count += 1
            lang = os.path.split(fname)[-1][:-size]
            n = _NGram()
            
            file = open(fname,'r')
            for line in file.readlines():
                n.addText(line)
            file.close()
                
            n.normalise()
            self.ngrams[lang] = n
            
    def save (self,folder,ext='.lm'):
        for lang in self.ngrams.keys():
            fname = os.path.join(folder,lang+ext)
            file = open(fname,'w')
            for v,k in self.ngrams[lang].sorted():
                file.write("%s\t %d\n" % (k,v))
            file.close()

if __name__ == '__main__':
    import sys

    text = sys.stdin.readline()
    n = _NGram()

    l = NGram('LM')
    print l.classify(text)

