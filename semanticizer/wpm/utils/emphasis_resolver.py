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

# This parses MediaWiki syntax for '''bold''' and ''italic'' text with the equivalent html markup.
class EmphasisResolver:
    def resolve_emphasis(self, text):
        sb = []
        for line in text.split("\n"):
            sb.append(self.resolve_line(line))
            sb.append("\n")

        result = "".join(sb)
        result = result[:-1]
        return result

    # This is a direct translation of the php function doAllQuotes used by the original MediaWiki software.
    # 
    # @param line the line to resolve emphasis within
    # @return the line, with all emphasis markup resolved to html tags
    # 
    def resolve_line(self, line):
        
        #print "Resolving line '" + line + "'"
        
        arr = self.get_splits("$"+line)
        if len(arr) <= 1:
            return line

        # First, do some preliminary work. This may shift some apostrophes from
        # being mark-up to being text. It also counts the number of occurrences
        # of bold and italics mark-ups.

        numBold = 0
        numItalics = 0

        for i, value in enumerate(arr):
            if (i % 2 == 1):
                # If there are ever four apostrophes, assume the first is supposed to
                # be text, and the remaining three constitute mark-up for bold text.
                if (len(arr[i]) == 4):
                    arr[i-1] = arr[i-1] + "'" ;
                    arr[i] = self.get_filled_string(3) ;
                elif len(arr[i]) > 5:
                    # If there are more than 5 apostrophes in a row, assume they're all
                    # text except for the last 5.
                    arr[i-1] = arr[i-1] + self.get_filled_string(len(arr[i])-5)
                    arr[i] = self.get_filled_string(5)
                
                size = len(arr[i])
                if size == 2:
                    numItalics +=1
                elif size == 3:
                    numBold+=1
                elif size == 5:
                    numItalics +=1
                    numBold +=1

        # If there is an odd number of both bold and italics, it is likely
        # that one of the bold ones was meant to be an apostrophe followed
        # by italics. Which one we cannot know for certain, but it is more
        # likely to be one that has a single-letter word before it.
        if (numBold%2==1) and (numItalics%2==1):
            i= 0
            firstSingleLetterWord = -1
            firstMultiLetterWord = -1
            firstSpace = -1

            for r in arr:
                if i%2==1 and len(r)==3:
                    x1 = arr[i-1][len(arr[i-1])-1]
                    x2 = arr[i-1][len(arr[i-1])-2]
                    if x1==' ':
                        if firstSpace == -1:
                            firstSpace = i ;
                    elif x2==' ':
                        if firstSingleLetterWord == -1:
                            firstSingleLetterWord = i
                    else:
                        if firstMultiLetterWord == -1:
                            firstMultiLetterWord = i

                i += 1

            # If there is a single-letter word, use it!
            if firstSingleLetterWord > -1:
                arr[firstSingleLetterWord] = "''"
                arr[firstSingleLetterWord-1] = arr[firstSingleLetterWord] + "'" 
            elif firstMultiLetterWord > -1:
                # If not, but there's a multi-letter word, use that one.
                arr[firstMultiLetterWord] = "''" 
                arr[firstMultiLetterWord-1] = arr[firstMultiLetterWord] + "'" 
            elif firstSpace > -1:
                # ... otherwise use the first one that has neither.
                # (notice that it is possible for all three to be -1 if, for example,
                # there is only one pentuple-apostrophe in the line)
                arr[firstSpace] = "''" 
                arr[firstSpace-1] = arr[firstSpace] + "'" 

        # Now let's actually convert our apostrophic mush to HTML!

        output = []
        buffer = []
        state = "" ;
        i = 0
        for r in arr:
            if i%2==0:
                if state == "both":
                    buffer.append(r)
                else:
                    output.append(r)
            else:
                if len(r) == 2:
                    if state == "i":
                        output.append("</i>")
                        state = ""
                    elif state == "bi":
                        output.append("</i>")
                        state = "b"
                    elif state =="ib":
                        output.append("</b></i><b>"); 
                        state = "b";
                    elif state =="both":
                        output.append("<b><i>") ;
                        output.append("".join(buffer))
                        output.append("</i>") ;
                        state = "b";
                    else:
                        # $state can be "b" or ""
                        output.append("<i>")
                        state = state + "i"
                elif len(r) == 3:
                    if state == "b":
                        output.append("</b>")
                        state = ""
                    elif state == "bi":
                        output.append("</i></b><i>")
                        state = "i"
                    elif state =="ib":
                        output.append("</b>"); 
                        state = "i";
                    elif state =="both":
                        output.append("<i><b>") ;
                        output.append("".join(buffer))
                        output.append("</b>") ;
                        state = "i";
                    else:
                        # $state can be "b" or ""
                        output.append("<b>")
                        state = state + "b"
                elif len(r) == 5:
                    if state == "b":
                        output.append("</b><i>")
                        state = "i"
                    elif state == "i":
                        output.append("</i><b>")
                        state = "b"
                    elif state =="bi":
                        output.append("</i></b>"); 
                        state = "";
                    elif state =="ib":
                        output.append("</b></i>") ;
                        state = "";
                    elif state =="both":
                        output.append("<i><b>") ;
                        output.append("".join(buffer))
                        output.append("</b></i>") ;
                        state = "i";
                    else:
                        # ($state == "")
                        buffer = []
                        state = "both"
            i += 1


        # Now close all remaining tags.  Notice that the order is important.
        if state == "b" or state == "ib":
            output.append("</b>")

        if state == "i" or state == "bi" or state == "ib":
            output.append("</i>")
        if state == "bi":
            output.append("</b>")

        # There might be lonely ''''', so make sure we have a buffer
        if state == "both" and len(buffer) > 0:
            output.append("<b><i>")
            output.append("".join(buffer))
            output.append("</i></b>")

        #remove leading $
        output = output[1:]

        return "".join(output)

        

    # Does the same job as php function preg_split 
    def get_splits(self, text):
        #return re.split("\\'{2,}", text)
        splits = []
        lastCopyIndex = 0
        p = re.compile("\\'{2,}")

        for m in p.finditer(text):
            if m.start() > lastCopyIndex:
                splits.append( text[lastCopyIndex: m.start()] )
            splits.append( m.group() )
            lastCopyIndex = m.end()

        if lastCopyIndex < len(text)-1:
            splits.append(text[lastCopyIndex])

        return splits


    def get_filled_string(self, length):
        sb = []
        for i in xrange(0,length): 
            sb.append("'")
        return "".join(sb)

## EmphasisResolver testing using 
## python -m semanticizer.wpm.utils.emphasis_resolver
if __name__ == '__main__':  
    er = EmphasisResolver()
    markup = "'''War''' is an openly declared state of organized [[violent]] [[Group conflict|conflict]], typified by extreme [[aggression]], [[societal]] disruption, and high [[Mortality rate|mortality]]. As a behavior pattern, warlike tendencies are found in many [[primate]] species, including [[humans]], and also found in many [[ant]] species. The set of techniques used by a group to carry out war is known as '''warfare'''." 
    #markup = "Parsing '''MediaWiki''''s syntax for '''bold''' and ''italic'' markup is a '''''deceptively''' difficult'' task. Whoever came up with the markup scheme should be '''shot'''." ; 
    print er.resolve_emphasis(markup)