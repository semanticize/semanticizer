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

from .emphasis_resolver import EmphasisResolver 

class MarkupStripper:
    def __init__(self):
        self.linkPattern = re.compile("\\[\\[(.*?:)?(.*?)(\\|.*?)?\\]\\]")
	self.emphasisResolver = EmphasisResolver()

    # Returns a copy of the given markup, where all markup has been removed except for 
    # internal links to other wikipedia pages (e.g. to articles or categories), section 
    # headers, list markers, and bold/italic markers. 
    # 
    # By default, unwanted markup is completely discarded. You can optionally specify 
    # a character to replace the regions that are discared, so that the length of the 
    # string and the locations of unstripped characters is not modified.
    def strip_all_but_internal_links_and_emphasis(self, markup, replacement=None):
        #deal with comments and math regions entirely seperately. 
        #Comments often contain poorly nested items that the remaining things will complain about.
        #Math regions contain items that look confusingly like templates.
        regions = self.gather_simple_regions(markup, "\\<\\!--(.*?)--\\>")
        regions = self.merge_region_lists(regions, self.gather_complex_regions(markup, "\\<math(\\s*?)([^>\\/]*?)\\>", "\\<\\/math(\\s*?)\\>"))
        clearedMarkup = self.strip_regions(markup, regions, replacement)


        #deal with templates entirely seperately. They often end in |}} which confuses the gathering of tables.
        regions = self.gather_templates(clearedMarkup) ;
        clearedMarkup = self.strip_regions(clearedMarkup, regions, replacement) 

        #now gather all of the other regions we want to ignore	
        regions = self.gather_tables(clearedMarkup)

        regions = self.merge_region_lists(regions, self.gather_html(clearedMarkup))
        regions = self.merge_region_lists(regions, self.gather_external_links(clearedMarkup))
        regions = self.merge_region_lists(regions, self.gather_magic_words(clearedMarkup))

        #ignore these regions now (they need to be blanked before we can correctly identify the remaining regions)
        clearedMarkup = self.strip_regions(clearedMarkup, regions, replacement)

        #print "Prior to removing misformatted start: "
        #print " - " + clearedMarkup

        regions = self.gather_misformatted_starts(clearedMarkup)
        clearedMarkup = self.strip_regions(clearedMarkup, regions, replacement)

        return clearedMarkup

    
    # Returns a copy of the given markup, where all links to wikipedia pages
    # that are not articles (categories, language links, etc) have been removed.
    # 
    # By default, unwanted markup is completely discarded. You can optionally specify
    # a character to replace the regions that are discarded, so that the length of the
    # string and the locations of unstripped characters is not modified.
    def strip_non_article_internal_links(self, markup, replacement=None):

        #currItem = "non-article internal links" ;
        regions = self.gather_complex_regions(markup, "\\[\\[", "\\]\\]")
        strippedMarkup = []
        lastPos = len(markup)

        #because regions are sorted by end position, we work backwards through them
        i = len(regions)
        while (i > 0):
            i -=1
            region = regions[i]
            #print " - - REGION: " + markup[region[0]:region[1]]

            #only deal with this region is not within a region we have already delt with. 
            if region[0] < lastPos:

                #copy everything between this region and start of last one we dealt with. 
                strippedMarkup.insert(0, markup[region[1]:lastPos] )

                linkMarkup = markup[region[0]:region[1]]

                #print "link [region[0],region[1]] = linkMarkup\n\n"

                #by default (if anything goes wrong) we will keep the link as it is
                strippedLinkMarkup = linkMarkup
                
                
                for m in self.linkPattern.finditer(linkMarkup):
                    prefix = m.group(1)
                    dest = m.group(2)
                    anchor = m.group(3)

                    if not prefix:
                        # this is not a link to another article, so get rid of it entirely
                        if replacement:
                            strippedLinkMarkup = linkMarkup.replace(".", str(replacement))		
                        else:
                            strippedLinkMarkup = ""
                    else:
                        if anchor and len(anchor) > 1:
                            #this has an anchor defined, so use that but blank out everything else

                            if replacement:
                                strippedLinkMarkup = replacement + replacement + dest.replace(".", str(replacement)) + replacement + anchor[1] + anchor[1] + replacement
                            else:
                                strippedLinkMarkup = anchor[1]

                        else:
                            # this has no anchor defined, so treat dest as anchor and blank out everything else
                            if replacement:
                                strippedLinkMarkup = replacement + replacement + dest + replacement + replacement ;
                            else:
                                strippedLinkMarkup = dest

                strippedMarkup.insert(0, strippedLinkMarkup)
                lastPos = region[0]

        if lastPos > 0:
            strippedMarkup.insert(0, markup[0:lastPos] )

	return "".join(strippedMarkup)	


    def strip_excess_newlines(self, markup):
	strippedMarkup = markup.replace("\n{3,}", "\n\n")
	return strippedMarkup.strip()


    # Gathers simple regions: ones which cannot be nested within each other.
    #
    # The returned regions (an array of start and end positions) will be sorted 
    # by end position (and also by start position, since they can't overlap) 
    
    def gather_simple_regions(self, markup, regex):
        # an array of regions we have identified
	# each region is given as an array containing start and end character indexes of the region. 
        regions = []
	p = re.compile(regex, re.DOTALL)
        for m in p.finditer(markup):
            region = (m.start(), m.end())
            regions.append(region)
	return regions


    # Merges two lists of regions into one sorted list. Regions that are contained
    # within other regions are discarded.
    # 
    # The resulting region list will be non-overlapping and sorted by end positions.

    def merge_region_lists(self, regionsA, regionsB):
        initialranges = regionsA + regionsB
        #when both are empty directly return
        if not initialranges:
            return initialranges
        i = sorted(set([tuple(sorted(x)) for x in initialranges]))
        # initialize final ranges to [(a,b)]
        f = [i[0]]
        for c, d in i[1:]:
            a, b = f[-1]
            if c<=b<d:
                f[-1] = a, d
            elif b<c<d:
                f.append((c,d))
            else:
                # else case included for clarity. Since 
                # we already sorted the tuples and the list
                # only remaining possibility is c<d<b
                # in which case we can silently pass
                pass
        return f

    # Gathers complex regions: ones which can potentially be nested within each other.
    # 
    # The returned regions (an array of start and end positions) will be either
    # non-overlapping or cleanly nested, and sorted by end position. 
    def gather_complex_regions(self, markup, startRegex, endRegex):
        
        # an array of regions we have identified
        # each region is given as an array containing start and end character indexes of the region. 
        regions = []
        # a stack of region starting positions
        startStack = []
        p = re.compile("((" + startRegex + ")|(" + endRegex + "))", re.DOTALL)

        for m in p.finditer(markup):
            p1 = m.start()
            p2 = m.end()
            
            if m.group(2):
                #this is the start of an item
                startStack.append(p1)
            else:
                #this is the end of an item
                if startStack:
                    start = startStack.pop()
                    region = (start, p2)
                    regions.append(region)
                    #print " - item [region[0],region[1]]: "+markup[region[0]:region[1]-region[0]]+"\n"
                #else:
                #    print "oops, we found the end of an item, but have no idea where it started"

        #if startStack:
        #   print "oops, we got to the end of the markup and still have items that have been started but not finished"
           
        return regions

    # Returns a copy of the given markup, where the given regions have been removed. 
    # Regions are identified using one of the gather methods.
    # 
    # By default, unwanted markup is completely discarded. You can optionally specify
    # a character to replace the regions that are discared, so that the length of the 
    # string and the locations of unstripped characters is not modified.
    def strip_regions(self, markup, regions, replacement):
        clearedMarkup = []
        lastPos = len(markup)
        
        #because regions are sorted by end position, we work backwards through them
        i = len(regions)
        while (i > 0):
            i -=1
            region = regions[i]
            
            #only deal with this region is not within a region we have already delt with. 
            if region[0] < lastPos:
                #copy markup after this region and before beginning of the last region we delt with
                if region[1] < lastPos:
                    clearedMarkup.insert(0, markup[region[1]:lastPos])
                if replacement:
                    fill = markup[region[0]:region[1]].replace(".", str(replacement)) ;
                    clearedMarkup.insert(0, fill)
                lastPos = region[0]
            #else:
            #    print " - - already dealt with\n"

        clearedMarkup.insert(0, markup[0:lastPos] )
        
        return "".join(clearedMarkup)

    # Gathers areas within the markup which correspond to templates (as identified by {{ and }} pairs). 
    def gather_templates(self, markup):
        # currItem = "templates" ;
        return self.gather_complex_regions(markup, "\\{\\{", "\\}\\}")

    # Gathers areas within the markup which correspond to tables (as identified by {| and |} pairs). 
    def gather_tables(self, markup):
	# currItem = "tables" ;
	return self.gather_complex_regions(markup, "\\{\\|", "\\|\\}")
    
    # Gathers areas within the markup which correspond to html tags. 
    # 
    # DIV and REF regions will enclose beginning and ending tags, and everything in between,
    # since we assume this content is supposed to be discarded. All other regions will only include the
    # individual tag, since we assume the content between such pairs is supposed to be retained. 
    def gather_html(self, markup):
        #currItem = "html" ;

        #gather and merge references
        regions = self.gather_references(markup)

        #gather <div> </div> pairs
        regions = self.merge_region_lists(regions, self.gather_complex_regions(markup, "\\<div(\\s*?)([^>\\/]*?)\\>", "\\<\\/div(\\s*?)\\>"))

        #gather remaining tags
        regions = self.merge_region_lists(regions, self.gather_simple_regions(markup, "\\<(.*?)\\>"))

        return regions


    # Gathers areas within the markup which correspond to references (markup to support claims or facts).
    # The regions will enclose beginning and ending tags, and everything in between,
    # since we assume this content is supposed to be discarded. 
    def gather_references(self, markup):
        # currItem = "references" ;
	#gather <ref/>
	regions = self.gather_simple_regions(markup, "\\<ref(\\s*?)([^>]*?)\\/\\>")

	#gather <ref> </ref> pairs (these shouldnt be nested, but what the hell...)
	regions = self.merge_region_lists(regions, self.gather_complex_regions(markup, "\\<ref(\\s*?)([^>\\/]*?)\\>", "\\<\\/ref(\\s*?)\\>"))

	return regions

    # Gathers all links to external web pages
    def gather_external_links(self, markup):
	# currItem = "external links" ;
	return self.gather_simple_regions(markup, "\\[(http|www|ftp).*?\\]")


    # Gathers items which MediaWiki documentation mysteriously refers to as "majic words": e.g. __NOTOC__
    def gather_magic_words(self, markup):
	# currItem = "magic words" ;
	return self.gather_simple_regions(markup, "\\_\\_([A-Z]+)\\_\\_")


    # Gathers paragraphs within the markup referred to by the given pointer, which are at the 
    # start and either begin with an indent or are entirely encased in italics. These correspond to quotes or disambiguation and 
    # navigation notes that the author should have used templates to identify, but didn't. 
    # This will only work after templates, and before list markers have been cleaned out.
    def gather_misformatted_starts(self, markup):

        #currItem = "starts" ;
        lines = markup.splitlines()
        ignoreUntil = 0

        for line in lines:
            isWhitespace = re.search("^(\\s*)$",line)
            isIndented = re.search("^(\\s*):.*", line)
            isItalicised = self.is_entirely_italicised(line)
            isImage = re.search("^(\\s*)\\[\\[Image\\:(.*?)\\]\\](\\s*)",line)

            # print " - - '" + line + "' " + isIndented + "," + isItalicised
            if isWhitespace or isIndented or isItalicised or isImage:
                #want to ignore this line
                ignoreUntil = ignoreUntil + len(line) + 1
                #print " - - - discard\n"	
            else:
                #print " - - - keep\n"
                break

        region = (0, ignoreUntil)
        regions = []
        regions.append(region)

        return regions

    def is_entirely_italicised(self, line):
        resolvedLine = self.emphasisResolver.resolve_emphasis(line) 
        p = re.compile("(\\s*)\\<i\\>(.*?)\\<\\/i\\>\\.?(\\s*)")
        results = p.finditer(resolvedLine)
        if not results:
            return False
        
        for m in results:
            if "</i>" in m.group(1):
                return False
            else:
                return True