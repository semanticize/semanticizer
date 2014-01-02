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

cache = dict()

class MemoryDB:
    #store all data in memory instead of redis, mimic redis functions
    def __init__(self, **kwargs): 
        pass
    
    def pipeline(self,  **kwargs):
        return Pipe()
    
    def exists(self, key):
        return key in cache
    
    def keys(self, key):
        return [k for k in cache.iterkeys() if k.startswith(key.replace("*", ""))]
    
    def get(self, key):
        return cache[key]
    
    def set(self, key, value):
        cache[key] = value
        return True
        
    def smembers(self, key):
        return self.get(key)
    
    def sismember(self, key, value):
        return value in cache[key]
    
    def sadd(self, key, *values):
        if not key in cache:
            cache[key] = set()
        for value in values:
            cache[key].add(value)
        return [True]*len(values)
        
    def lrange(self, key, start, end):
        data = cache.get(key, set())
        return list(data)[start:end] 
        
    def rpush(self, key, *values):
        if not key in cache:
            cache[key] = list()
        for value in values:
            cache[key].append(value)
        return [True]*len(values)
        
    def zscore(self, key, value):
        return cache[key][value]
    
    def zincrby(self, key, value, ammount=1):
        # in case key does not exist create dict
        if not key in cache:
            cache[key] = dict()
        # in case value does not exist init 
        if value in cache[key]:
            cache[key][value] = ammount
        cache[key][value] += ammount
        return cache[key][value]
        
    def delete(self,*keys):
        for key in keys:
            cache.pop(key, None)
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
        
#implicity add a decorator Proxy to all functions of MemoryDB to fetch all returns and output them on execute
class Pipe(Proxy, MemoryDB):
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