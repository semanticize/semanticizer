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
    	assert link.has_key(self.threshold_function)
    	assert link.has_key("label")

    	if link[self.threshold_function] < self.threshold: return
    
    	label_text = "[%d-%s]" % (self.chunk, link["label"])
    	self.page_ranked.setdefault(link["title"], 1)
    	self.page_ranked.setdefault(label_text, 0)
    	self.graph.add_edge(label_text, link["title"], t=self.chunk) # weight=senseProbability
    	self.graph.add_edge(label_text, "[Chunk%d]" % self.chunk, t=self.chunk)

    def prepare_features(self):
        self.clean_graph(self.chunk-self.min_t)
        
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
    # 		pagerank(graph, max_iter=1000) # 1.7s for #nodes = 2500
    		pagerank(self.graph, max_iter=1000, nstart=self.page_ranked) # 0.2-1.5s for #node = 2500
    # 		pagerank_scipy(graph) # 1.0s for #nodes = 2500
    # 		pagerank_numpy(graph) # > 30s if #nodes > 1000
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
