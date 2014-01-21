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

from pymongo import MongoClient

class MongoDB:
    def __init__(self, host='localhost', port=27017, **kwargs): 
        global client 
        client = MongoClient(host, port)
    
    def pipeline(self,  **kwargs):
        return Pipe()
    
    def exists(self, key):
        item = client.sem.wpm.find_one( {"_id": key})
        return False if not item else True
        
    def keys(self, key):
        item = client.sem.wpm.find( {"_id": "/"+key+"/"})
        return [] if not item else item
    
    def get(self, key):
        item = client.sem.wpm.find_one( {"_id": key})
        return item['value']
    
    def set(self, key, value):
        client.sem.wpm.save( {"_id":key, "value": value})
        return True
        
    def smembers(self, key):
        return self.get(key)
    
    def sismember(self, key, value):
        item = client.sem.wpm.find_one( {"_id": key})
        return False if not item else value in item['value']
    
    def sadd(self, key, *values):
        item = client.sem.wpm.find_one( {"_id": key})
        svalue = set(values) if not item else set(list(item['value']) + list(values))
        client.sem.wpm.update( {"_id":key},{'$set':{'value': list(svalue)}},upsert=True, multi=False)
        return [True]*len(values)
        
    def lrange(self, key, start, end):
        item = client.sem.wpm.find_one( {"_id": key})
        return [] if not item else value in item['value'][start:end]
        
    def rpush(self, key, *values):
        item = client.sem.wpm.find_one( {"_id": key})
        lvalue  = list(values) if not item else list(item['value']) + list(values)
        client.sem.wpm.update( {"_id":key},{'$set':{'value': lvalue}},upsert=True, multi=False)
        return [True]*len(values)
        
    def zscore(self, key, value):
        item = client.sem.wpm.find_one( {"_id": key})
        subkey = ":"+str(value)+":"
        if not item:
            return None
        if not subkey in item:
            return None
        return item[subkey]
    
    def zincrby(self, key, value, ammount=1):
        client.sem.wpm.update( {"_id":key},{'$inc':{":"+str(value)+":": 1}},upsert=True, multi=False)
        return True
    
    def delete(self,*keys):
        for key in keys:
            client.sem.wpm.remove({"_id":key})
        return True

#proxy all returns to pipe class
class Proxy(object):
    def __getattribute__(self,name):
        attr = object.__getattribute__(self, name)
        if hasattr(attr, '__call__'):
            def newfunc(*args, **kwargs):
                result = attr(*args, **kwargs)
                self.results.append(result)
                return True
            return newfunc
        else:
            return attr
        
#implicity add a decorator Proxy to all functions of MongoDB to fetch all returns and output them on execute
class Pipe(Proxy, MongoDB):
    def __init__(self):
        self.reset()
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.reset()

    def __del__(self):
        try:
            self.reset()
        except Exception:
            pass
        
    def __len__(self):
        return len(self.results)
         
    def reset(self):
        self.results = []
        
    def execute(self):
        results = self.results
        self.reset()
        return results