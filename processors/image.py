from Queue import Queue, Empty
from threading import Thread

import urllib2, re

from core import LinksProcessor

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
                            image = match.groups()[0]
                            if dimension >= min_dimension:
                                break

                if image != None:
                    if image.startswith("//"): 
                        image = "http:" + image
                    elif image.startswith("/"):
                        image = "http://" + url.split("/")[2] + image
                        
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
