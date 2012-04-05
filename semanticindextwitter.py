import os
import json

from time import sleep

root="/zfs/ilps-plexer/twitter-data/data/2012"

import httplib
connection =  httplib.HTTPConnection('localhost:9200')

# # Find max id from where to start posting again
# connection.request('GET', '/twitter/tweet/_search?size=1&fields=&sort=id:desc')
# result = json.loads(connection.getresponse().read())
# max_id = int(result["hits"]["hits"][0]["_id"])

# Helpers to compare filenames in gardenhose dump
def addzero(x): 
    parts = x.split('-')
    if parts[1][1] == '.':
        parts[1] = '0' + parts[1]
        return '-'.join(parts)
    else:
         return x
filecmp = lambda x,y: cmp(addzero(x), addzero(y))

# Initialize a Semanticizer
from nltk import word_tokenize
from Semanticizer import Semanticizer

semanticizer = Semanticizer()

def semanticize(sentence):
    result = {"sentiment_clues": {}, "links": []}
    words = word_tokenize(sentence.replace('-', ' '))
    for n in range(1,len(words)+1):
        for i in range(len(words)-n+1):
            word = ' '.join(words[i:i+n])
#           if semanticizer.sentiment_lexicon.has_key(word):
#               sentiment = semanticizer.sentiment_lexicon[word]
#               result["sentiment_clues"][word] = sentiment
            if semanticizer.labels.has_key(word):
                label = semanticizer.labels[word]
                for sense in label[4]:
                    if label[2] == 0:
                        senseprob = 0
                    else:
                        # Senseprob is # of links to target with anchor text
                        # over # of times anchor text used
                        senseprob = float(label[4][sense][0])/label[2]
                    if senseprob > 0.01:
                        title = semanticizer.page_title[sense].decode(errors="replace")
                        result["links"].append({
                            "label": word,
                            "title": title,
                            "senseProbability": senseprob
                        })
    return result           

dir_index = 0
file_index = 0
while True:
    dirs = sorted(os.listdir(root))
    assert dir_index < len(dirs)

    dir = dirs[dir_index]
    files = sorted(os.listdir(os.path.join(root, dir)), filecmp)

    if file_index == (len(files)-1) and dir_index == (len(files)-1):
        # The last file of the last dir
        print("At last file, so leeping for 30 minutes.")
        sleep(30*60)
        continue
    if file_index >= len(files):
        if dir_index < (len(dirs)-1):
            # Go to next dir
            dir_index += 1
            file_index = 0
            continue
        else:
            print("I should be here, so I'll be Sleeping for 30 minutes.")
            sleep(30*60)
            continue

    file = files[file_index]
    print "Loading tweets from: " + dir + "/" + file
    with open(os.path.join(root, dir, file)) as filep:
        for line in filep:
            try:
                tweet = json.loads(line)
            except ValueError:
                print "Error in tweet: " + line
                continue

            if tweet.has_key("delete"): continue
            if not tweet.has_key("id"): assert False, line
#           if int(tweet["id"]) <= max_id: continue

            assert tweet.has_key("text")
            tweet["semantic"] = semanticize(tweet["text"])

            connection.request('POST', '/semantictwitter/tweet/%d' % tweet["id"], json.dumps(tweet))
            result = connection.getresponse().read()
            result_json = json.loads(result)
            if not result_json.has_key("ok") or not result_json["ok"]:
                print result
                continue

    file_index += 1
