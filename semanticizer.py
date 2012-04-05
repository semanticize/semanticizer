PICKLE_ROOT = './enwiki-20111007-pickles/'
WIKIPEDIAMINER_ROOT = './enwiki-20111007-wikipediaminer/'

class Semanticizer:

	def load_page_titles(self, filename):
		print 'Loading page titles...'
		self.page_title = {}
		self.title_page = {}
		file = open(filename, 'r')
		for line in file:
			splits = line.split(',')
			id = int(splits[0])
			title = splits[1][1:]
			self.page_title[id] = title
			self.title_page[title] = id

		print '%d pages loaded.' % len(self.page_title)

	def load_labels(self, filename):
		self.labels = {}
		print 'Loading labels...'
		file = open(filename, 'r')
		for line in file:
			stats_part, senses_part = line.split(',v{')
			senses = senses_part[:-1].split('s')[1:]
			stats = stats_part[1:].split(',')
			text = stats[0]
			label = map(int, stats[1:])
			label.append({})
			for sense_text in senses:
				sense_parts = sense_text[1:-1].split(',')
				id = int(sense_parts[0])
				label[-1][id] = map(int, sense_parts[1:3]) + [sense_parts[3] == 'T', sense_parts[4] == 'T']

			self.labels[text] = label

	def load_category_parents(self, filename):
		print 'Loading category parents...'
		self.category_parents = {}
		file = open(filename, 'r')
		for line in file:
			line = line.replace('v{', '').replace('}\n', '')
			ids = line.split(',')
			category_id = int(ids[0])
			self.category_parents[category_id] = []
			for parent_id in ids[1:]:
				self.category_parents[category_id].append(int(parent_id))

		print '%d category parents loaded.' % len(self.category_parents)

	def load_category_titles(self, filename):
		print 'Loading category titles...'
		self.category_title = {}
		file = open(filename, 'r')
		for line in file:
			if not line.startswith('INSERT INTO `category` VALUES'):
				continue
			splits = line[31:-3].split('),(')
			for split in splits:
				data = split.split(',')
				self.category_title[int(data[0])] = ','.join(data[1:-4])[1:-1]

		print '%d category titles loaded.' % len(self.category_title)

	def load_article_parents(self, filename):
		print 'Loading article parents...'
		self.article_parents = {}
		file = open(filename, 'r')
		for line in file:
			line = line.replace('v{', '').replace('}\n', '')
			ids = line.split(',')
			article_id = int(ids[0])
			if article_id == 44731:
				print line
			self.article_parents[article_id] = []
			for parent_id in ids[1:]:
				self.article_parents[article_id].append(int(parent_id))

		print '%d article parents loaded.' % len(self.article_parents)

	def senses(self, text):
		raw_label = self.labels[text]
		label = {'LinkOccCount': raw_label[0],
		 'LinkDocCount': raw_label[1],
		 'TextOccCount': raw_label[2],
		 'TextDocCount': raw_label[3],
		 'Senses': {}}
		for id, raw_sense in raw_label[4].iteritems():
			sense = {'LinkOccCount': raw_sense[0],
			 'LinkDocCount': raw_sense[1],
			 'FromTitle': raw_sense[2],
			 'FromRedirect': raw_sense[3]}
			label['Senses'][self.page_title[id]] = sense

		return label

	def load_sentiment_lexicon(self, filename):
		print 'Loading sentiment lexicon...'
		self.sentiment_lexicon = {}
		file = open(filename, 'r')
		for line in file:
			words = line.strip().split('\t')
			self.sentiment_lexicon[words[0]] = words[1]

		print '%d sentiment words loaded.' % len(self.sentiment_lexicon)
		
	def __init__(self):
		self.load_sentiment_lexicon('./sentiment_lexicon_nl.txt')
		self.load_labels(WIKIPEDIAMINER_ROOT + 'label.csv')
		self.load_page_titles(WIKIPEDIAMINER_ROOT + 'page.csv')


if __name__ == '__main__':
	type_uri = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
	semanticizer = Semanticizer()
	print 'Loading text...'
	print
	import sys
	text = sys.stdin.read()
	from nltk import sent_tokenize, word_tokenize
	sentences = sent_tokenize(text)
	for sentence in sentences:
		print sentence
		words = word_tokenize(sentence)
		for n in range(1, len(words) + 1):
			for i in range(len(words) - n + 1):
				word = ' '.join(words[i:i + n])
				if semanticizer.sentiment_lexicon.has_key(word):
					print '{0:<5}\t{1}'.format(semanticizer.sentiment_lexicon[word], word)
				if semanticizer.labels.has_key(word):
					label = semanticizer.labels[word]
					for sense in label[4]:
						senseprob = float(label[4][sense][0]) / label[2]
						if senseprob > 0.05:
							title = semanticizer.page_title[sense]
							import urllib, urllib2, json
							resource = 'http://nl.dbpedia.org/resource/%s' % urllib.quote(title)
							print '%.2f -> %s' % (senseprob, resource),
							response = urllib2.urlopen(resource.replace('/resource/', '/data/') + ".json")
							data = json.loads(response.read())
							if data.has_key(resource):
								if data[resource].has_key(type_uri):
									print [element["value"] for element in data[resource][type_uri]],
							print
