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

from Queue import Queue, Empty
from threading import Thread

import urllib2, re

from .core import LinksProcessor

class AddImageProcessor(LinksProcessor):
    def postprocess(self, links, text, settings):
        if "image" in settings and "langcode" in settings:
            links = add_image_url(links, settings["langcode"])
        return (links, text, settings)

image_url_cache = {}

def add_image_url(links, langcode):
    urls = [link["url"].replace(".wikipedia.org/", ".m.wikipedia.org/") \
            for link in links]
    
    print "Getting images for %d Wikipedia pages" % len(urls)
    get_image_urls(urls)
    for link, url in zip(links, urls):
        if url in image_url_cache:
            print link["title"], "->", image_url_cache[url]
            link["image_url"] = image_url_cache[url]
    
    return links

IMG_DIMENSION_PATTERN = '<img .*?width="(\d+)" height="(\d+)".*?>'
IMG_URL_PATTERN = '<img .*?src="(.+?)".*?>'

BLACKLISTED_IMAGE_URLS = ('http://upload.wikimedia.org/wikipedia/en/f/f4/Ambox_content.png',
      'http://upload.wikimedia.org/wikipedia/en/thumb/9/99/Question_book-new.svg/50px-Question_book-new.svg.png',
      'http://upload.wikimedia.org/wikipedia/en/thumb/f/f2/Edit-clear.svg/40px-Edit-clear.svg.png',
      'http://upload.wikimedia.org/wikipedia/commons/thumb/f/f8/Wiktionary-logo-en.svg/37px-Wiktionary-logo-en.svg.png',
      'http://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Text_document_with_red_question_mark.svg/40px-Text_document_with_red_question_mark.svg.png')

def convert_image_url(image):
    if image.startswith("//"): 
        image = "http:" + image
    elif image.startswith("/"):
        image = "http://" + url.split("/")[2] + image
    return image

def get_image_urls(urls, num_of_threads=8, min_dimension=36):
    def worker():
        while True:
            try:
                url = queue.get_nowait()
                try:
                    page = urllib2.urlopen(url, timeout=1).read()
                except:
                	page = ""
                images = re.findall("<img.*?>", page)
                
                # Filter Wikipedia images
                images = [img for img in images if " id=" not in img \
                                                and " title=" not in img]
                image = None
                for img in images:
                    match = re.match(IMG_DIMENSION_PATTERN, img)
                    if match == None: continue
                    dimension = max([int(value) for value in match.groups()])
                    if dimension >= min_dimension: # Do not use fallback: or image == None:
                        match = re.match(IMG_URL_PATTERN, img)
                        if match != None and len(match.groups()) > 0:
                            image_url = convert_image_url(match.groups()[0])
                            if image_url in BLACKLISTED_IMAGE_URLS: continue
                            image = image_url
                            if dimension >= min_dimension:
                                break

                    image_url_cache[url] = image
                
                queue.task_done()
            except Empty:
                break
    
    queue = Queue()
    for url in urls:
        queue.put(url)
    
    for i in range(min(num_of_threads, len(urls))):
        t = Thread(target=worker)
        t.daemon = True
        t.start()
    
    queue.join()
