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

import time

class Timer(object):
    """Convience method to time activities. Can be used as context."""
    
    def __init__(self, activity, name=None):
        self.name = name
        self.activity = activity
        self.tstart = time.time()
    
    def __del__(self):
        if self.name: print '[%s]' % self.name,
        print self.activity,
        print 'took %s seconds.' % (time.time() - self.tstart)

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        pass
