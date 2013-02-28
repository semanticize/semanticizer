import networkx
from networkx.algorithms.centrality import degree_centrality

from multiprocessing import Pool

def pagerank_worker(graph, page_ranked):
    print "Pagerank on graph with %d nodes and %d edges." \
              % (len(graph.nodes()), \
                 len(graph.edges()))
    for node in graph.nodes():
        page_ranked.setdefault(node, 1)
        
    from networkx.algorithms.link_analysis import pagerank
    from time import time
    
    try:
        start = time()
        page_ranked = pagerank(graph, max_iter=1000, nstart=page_ranked) # 0.2-1.5s for #node = 2500
        print "Pagerank took: %f seconds" % (time()-start)
    except ZeroDivisionError:
        print "ZeroDivisionError in pagerank"
    
    page_ranked_sorted = sorted(page_ranked.items(), key=lambda x: x[1], reverse=True)
    print page_ranked_sorted[:4]
    
pool = Pool()

class contextGraph:
    def __init__(self, label, threshold_function, threshold, min_t):
        self.graph = networkx.Graph()
        self.page_ranked = {}
        self.chunk = -1
        self.feature_label = "CONTEXT_" + label.upper()

        self.threshold_function = threshold_function
        self.threshold = threshold
        self.min_t = min_t
        
        #                       min_t = t - 25
        #                       if min_t >= 0:
        #                               print "Cleaning graph with %d nodes and %d edges." \
        #                                                                         % (len(context_graph.nodes()), \
        #                                                                                len(context_graph.edges()))
        
    def to_dict_of_dicts(self):
        return networkx.convert.to_dict_of_dicts(self.graph)

    def add_chunk(self):
        self.chunk += 1
        self.page_ranked.setdefault("[Chunk%d]" % self.chunk, 0)
        if self.chunk > 0:
            self.graph.add_edge("[Chunk%d]" % self.chunk, \
                                "[Chunk%d]" % (self.chunk-1), t=self.chunk)
        
    def add_link(self, link):
    	assert link.has_key("title")
    	assert link.has_key("sense_probability")
    	assert link.has_key("label")

    	if link[self.threshold_function] < self.threshold: return
    
    	label_text = "[%d-%s]" % (self.chunk, link["label"])
    	self.page_ranked.setdefault(link["title"], 1)
    	self.page_ranked.setdefault(label_text, 0)
    	self.graph.add_edge(label_text, link["title"], t=self.chunk) # weight=senseProbability
    	self.graph.add_edge(label_text, "[Chunk%d]" % self.chunk, t=self.chunk)

    def prepare_features(self):
        self.clean_graph(self.chunk-self.min_t)
    
#         from threading import Thread
#         from multiprocessing import Process
        
#        def pagerank_worker():
#            print "Pagerank on graph with %d nodes and %d edges." \
#                      % (len(self.graph.nodes()), \
#                         len(self.graph.edges()))
#            for node in self.graph.nodes():
#                self.page_ranked.setdefault(node, 1)
#    
#            self.page_ranked = self.pagerank()

#        self.pagerank_thread = Thread(target=pagerank_worker)
#        self.pagerank_thread.start()

#         self.pagerank_thread = Process(target=pagerank_worker, args=(self.graph, self.page_ranked,))
#         self.pagerank_thread.start()
        
        self.pagerank_result = pool.apply_async(pagerank_worker, (self.graph, self.page_ranked,))
        
#         def degree_centrality_worker():
#             self.degree_centralities = degree_centrality(self.graph)
#         
#         self.degree_centrality_thread = Thread(target=degree_centrality_worker)
#         self.degree_centrality_thread.start()

        self.degree_centrality_result = pool.apply_async(degree_centrality, (self.graph,))

    def compute_features(self, title):
#         self.degree_centrality_thread.join()
#         self.pagerank_thread.join()
        self.degree_centralities = self.degree_centrality_result.get()
        self.pagerank_result.wait()
        
        features = {}
        features[self.feature_label + "_DEGREE"] = 0
        features[self.feature_label + "_PAGERANK"] = 0
        features[self.feature_label + "_PAGERANK_NORMALIZED"] = 0
        features[self.feature_label + "_DEGREE_CENTRALITY"] = 0
        if title in self.page_ranked:
            features[self.feature_label + "_PAGERANK"] = self.page_ranked[title]
            features[self.feature_label + "_PAGERANK_NORMALIZED"] = \
                len(self.graph.nodes()) * self.page_ranked[title]
        if title in self.degree_centralities:
            features[self.feature_label + "_DEGREE"] = \
                self.graph.degree(title)
            features[self.feature_label + "_DEGREE_CENTRALITY"] = \
                self.degree_centralities[title]                                
        return features

# def update_graph_weighted_linkprob(label, sense, article, t, context_graph, page_ranked):
# 	if not article.attrib.has_key("title"): return
# 	assert sense["title"]==article.attrib["title"], sense["title"]+"!="+article.attrib["title"]
# 	linkProbability = float(label["linkProbability"])
# 	commonness = float(sense["priorProbability"])
# 	if (linkProbability*commonness) < 0.1: return
# 
# 	title = sense["title"]
# 	label_text = "[%d-%d-%s]" % (t, label["startIndex"], label["text"])
# 	page_ranked.setdefault(title, 1)
# 	page_ranked.setdefault(label_text, 0)
# 	context_graph.add_edge(label_text, title, t=t, weight=linkProbability)
# 	context_graph.add_edge(label_text, "[Chunk%d]" % t, t=t)
# 
# def update_graph_weighted_commonness(label, sense, article, t, context_graph, page_ranked):
# 	if not article.attrib.has_key("title"): return
# 	assert sense["title"]==article.attrib["title"], sense["title"]+"!="+article.attrib["title"]
# 	senseProbability = float(sense["priorProbability"])*float(label["linkProbability"])
# 	commonness = float(sense["priorProbability"])
# 	if senseProbability < 0.1: return
# 
# 	title = sense["title"]
# 	label_text = "[%d-%d-%s]" % (t, label["startIndex"], label["text"])
# 	page_ranked.setdefault(title, 1)
# 	page_ranked.setdefault(label_text, 0)
# 	context_graph.add_edge(label_text, title, t=t, weight=commonness)
# 	context_graph.add_edge(label_text, "[Chunk%d]" % t, t=t)
# 
# def update_graph_weighted_senseprob(label, sense, article, t, context_graph, page_ranked, weight=1):
# 	if not article.attrib.has_key("title"): return
# 	assert sense["title"]==article.attrib["title"], sense["title"]+"!="+article.attrib["title"]
# 	commonness = float(sense["priorProbability"])
# 	senseProbability = float(sense["priorProbability"])*float(label["linkProbability"])
# 	if senseProbability < 0.1: return
# 
# 	title = sense["title"]
# 	label_text = "[%d-%d-%s]" % (t, label["startIndex"], label["text"])
# 	page_ranked.setdefault(title, 1)
# 	page_ranked.setdefault(label_text, 0)
# 	context_graph.add_edge(label_text, title, t=t, weight=senseProbability)
# 	context_graph.add_edge(label_text, "[Chunk%d]" % t, t=t, weight=weight)
# 
# def update_graph_enriched_outlinks(label, sense, article, t, context_graph, page_ranked, weight=1):
# 	"""Update context_graph"""
# 	import networkx
# 
# 	if not article.attrib.has_key("title"): return
# 	assert sense["title"]==article.attrib["title"], sense["title"]+"!="+article.attrib["title"]
# 	senseProbability = float(sense["priorProbability"])*float(label["linkProbability"])
# 	commonness = float(sense["priorProbability"])
# 	if senseProbability < 0.1: return
# 
# 	title = sense["title"]
# 	label_text = "[%d-%d-%s]" % (t, label["startIndex"], label["text"])
# 	page_ranked.setdefault(title, 1)
# 	page_ranked.setdefault(label_text, 0)
# 	for child in article:
# 		if child.tag == "OutLinks":
# 			for link in child:
# 				target = link.attrib["title"]
# 				context_graph.add_edge(title, target, weight=senseProbability, t=t)
# 				page_ranked.setdefault(target, 0)
# 
# 	context_graph.add_edge(label_text, "[Chunk%d]" % t, t=t, weight=weight)
# 
# def update_graph_enriched(label, sense, article, t, context_graph, page_ranked, weight=1):
# 	"""Update context_graph"""
# 	import networkx
# 
# 	if not article.attrib.has_key("title"): return
# 	assert sense["title"]==article.attrib["title"], sense["title"]+"!="+article.attrib["title"]
# 	senseProbability = float(sense["priorProbability"])*float(label["linkProbability"])
# 	commonness = float(sense["priorProbability"])
# 	if senseProbability < 0.1: return
# 
# 	title = sense["title"]
# 	label_text = "[%d-%d-%s]" % (t, label["startIndex"], label["text"])
# 	page_ranked.setdefault(title, 1)
# 	page_ranked.setdefault(label_text, 0)
# 	for child in article:
# 		if child.tag == "InLinks":
# 			for link in child:
# 				target = link.attrib["title"]
# 				context_graph.add_edge(title, target, weight=senseProbability, t=t)
# 				page_ranked.setdefault(target, 0)
# 		elif child.tag == "OutLinks":
# 			for link in child:
# 				target = link.attrib["title"]
# 				context_graph.add_edge(target, title, weight=senseProbability, t=t)
# 				page_ranked.setdefault(target, 0)
# 
# 	context_graph.add_edge(label_text, "[Chunk%d]" % t, t=t, weight=weight)
# 
# def update_graph_category(label, sense, article, t, context_graph, page_ranked):
# 	"""Update context_graph"""
# 	import networkx
# 
# 	if not article.attrib.has_key("title"): return
# 	assert sense["title"]==article.attrib["title"], sense["title"]+"!="+article.attrib["title"]
# 	senseProbability = float(sense["priorProbability"])*float(label["linkProbability"])
# 	commonness = float(sense["priorProbability"])
# 	if senseProbability < 0.1: return
# 
# 	title = sense["title"]
# 	label_text = "[%d-%d-%s]" % (t, label["startIndex"], label["text"])
# 	page_ranked.setdefault(title, 1)
# 	page_ranked.setdefault(label_text, 0)
# 	for child in article:
# 		if child.tag == "InLinks":
# 			for link in child:
# 				target = link.attrib["title"]
# 				context_graph.add_edge(title, target, weight=senseProbability, t=t)
# 				page_ranked.setdefault(target, 0)
# 		elif child.tag == "OutLinks":
# 			for link in child:
# 				target = link.attrib["title"]
# 				context_graph.add_edge(target, title, weight=senseProbability, t=t)
# 				page_ranked.setdefault(target, 0)
# 		elif child.tag == "ParentCategories":
# 			for link in child:
# 				target = link.attrib["title"]
# 				context_graph.add_edge(title, target, weight=senseProbability, t=t)
# 				page_ranked.setdefault(target, 0)
# 
# 	context_graph.add_edge(label_text, "[Chunk%d]" % t, t=t)
				
    def clean_graph(self, min_t):
    	# Remove edges with a t lower than min_t
    	for edge in self.graph.edges():
    		if self.graph[edge[0]][edge[1]]["t"] < min_t:
    			self.graph.remove_edge(edge[0], edge[1])
    	# Remove nodes that have become disconnected
    	for node in self.graph.nodes():
    		if self.graph.degree(node) == 0:
    			self.graph.remove_node(node)
    			del self.page_ranked[node]

    def pagerank(self):
    # 	from networkx.algorithms.link_analysis import pagerank_scipy
    # 	from networkx.algorithms.link_analysis import pagerank_numpy
    	from networkx.algorithms.link_analysis import pagerank
    	from time import time
    	try:
    		start = time()
    # 		page_ranked = pagerank(graph, max_iter=1000) # 1.7s for #nodes = 2500
    		page_ranked = pagerank(self.graph, max_iter=1000, nstart=self.page_ranked) # 0.2-1.5s for #node = 2500
    # 		page_ranked = pagerank_scipy(graph) # 1.0s for #nodes = 2500
    # 		page_ranked = pagerank_numpy(graph) # > 30s if #nodes > 1000
    		print "Pagerank took: %f seconds" % (time()-start)
    	except ZeroDivisionError:
    		print "ZeroDivisionError in pagerank"
    
    	page_ranked_sorted = sorted(self.page_ranked.items(), key=lambda x: x[1], reverse=True)
    	print page_ranked_sorted[:4]
    	
    # 	from networkx.algorithms.centrality import *
    
    # 	start = time()
    # 	degree_centrality = degree_centrality(graph) # 0.003s for 1500 nodes
    # 	print "Degree centrality took: %f seconds" % (time()-start)	
    # 		
    # 	start = time()
    # 	closeness_centrality = closeness_centrality(graph) # 4s for 1500 nodes
    # 	print "Closeness centrality took: %f seconds" % (time()-start)	
    # 
    # 	start = time()
    # 	betweenness_centrality = betweenness_centrality(graph) # 18s for 1500 nodes
    # 	print "Betweenness centrality took: %f seconds" % (time()-start)	
    
    	return self.page_ranked
