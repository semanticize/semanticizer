# 2012.03.15 15:29:37 CET

from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint

import json

class JsonRequestClient(Protocol):
	def __init__(self, request):
		self.request = request
		
	def connectionMade(self):
		self.transport.write(self.request.data)

	def dataReceived(self, data):
		self.request.response = json.loads(data)
		self.transport.loseConnection()

class JsonRequestClientFactory(ClientFactory):
	def __init__(self, request):
		self.request = request
		
	def buildProtocol(self, addr):
		return JsonRequestClient(self.request)

	def clientConnectionFailed(self, connector, reason):
		try:
			reactor.stop()
		except:
			pass
		raise Exception('Connection failed:', reason.getErrorMessage())
	
	def clientConnectionLost(self, connector, reason):
		reactor.stop()
		
class JsonRequestRequest():
	def __init__(self, server, port, data):
		self.data = data
		reactor.connectTCP(server, port, JsonRequestClientFactory(self))
        
if __name__ == '__main__':
	import sys
	text = sys.stdin.read()

	request = JsonRequestRequest(sys.argv[1], int(sys.argv[2]), text.strip())
	reactor.run()	
	print request.response
	
# 	for sentence in request.response:
# 		print sentence["sentence"]
# 		for sentiment in sentence["sentiment"]:
# 			for word, label in sentiment.items():
# 				print '{0:<5}\t{1}'.format(label, word)
	if "links" in request.response:
		for link in request.response["links"]:
			print '%.2f -> %s' % (link["sense_probability"], link["title"])
