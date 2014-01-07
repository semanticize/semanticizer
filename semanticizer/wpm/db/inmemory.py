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



class MemoryDB:
    #store all data in memory instead of redis, mimic redis functions
    def __init__(self, **kwargs): 
        self.cache = dict()
    
    def pipeline(self,  **kwargs):
        return Pipe(self.cache)
    
    def exists(self, key):
        return key in self.cache
    
    def keys(self, key):
        key = key.replace("*", "")  
        # simple abstraction of redis wildcard key search, only valid for startswith equivalent search which should be sufficient, probably faster then full regular expression search over keys 
        return [k for k in self.cache.iterkeys() if k.startswith(key)]
    
    def get(self, key):
        return self.cache[key]
    
    def set(self, key, value):
        self.cache[key] = value
        return True
        
    def smembers(self, key):
        return self.get(key)
    
    def sismember(self, key, value):
        return value in self.cache[key]
    
    def sadd(self, key, *values):
        self.cache.setdefault(key, set()).update(values)
        return [True]*len(values)
        
    def lrange(self, key, start=0, end=-1):
        data = self.cache.get(key, list())
        if end < -1:
          return data[start:end+1] 
        elif end == -1:
          return data[start:] 
        else:
          return data[start:end] 
        
    def rpush(self, key, *values):
        self.cache.setdefault(key, []).extend(values)
        return [True]*len(values)
        
    def zscore(self, key, value):
        return self.cache[key][value]
    
    def zincrby(self, key, value, amount=1):
        # in case value does not exist init 
        if not value in self.cache.setdefault(key, {}):
            self.cache[key][value] = amount
        else:
            self.cache[key][value] += amount
        return self.cache[key][value]
        
    def delete(self,*keys):
        for key in keys:
            self.cache.pop(key, None)
        return True


#proxy all returns to pipe class
class Proxy(object):
    def __getattribute__(self,name):
        attr = object.__getattribute__(self, name)
        if hasattr(attr, '__call__') and name not in ["execute", "reset"]:
            def newfunc(*args, **kwargs):
                result = attr(*args, **kwargs)
                self.results.append(result)
                return True
            return newfunc
        else:
            return attr
        
#implicity add a decorator Proxy to all functions of MemoryDB to fetch all returns and output them on execute
class Pipe(Proxy, MemoryDB):
    def __init__(self, cache):
        self.reset()
        self.cache = cache
        
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