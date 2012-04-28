import socket
BUFFER_SIZE = 1024

def send_to_socket(host, port, text):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.settimeout(5)
	sock.connect((host, port))
	sock.sendall(text)
	response = ""
	while True:
		data = sock.recv(BUFFER_SIZE)
		if not data: break
		response += data
	sock.close()
	return response

import json
def json_service(host, port, text):
	response = send_to_socket(host, port, text)
	if len(response) == 0: return {}
	return json.loads(response.decode())

import sys
text = sys.stdin.read()

for port in range(8005, 8016):
	response = json_service("zookst14.science.uva.nl", port, text)
	print repr(port) + ':', repr(response)