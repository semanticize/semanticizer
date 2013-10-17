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

import sys
from ..wpm.wpmdata_redis import WpmLoader

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print "Usage: %s language_name language_code path_to_wpm_dump" \
               % sys.argv[0]
        sys.exit(1)
    try:
        loader = WpmLoader()
        loader.load_wpminer_dump(sys.argv[1], sys.argv[2], sys.argv[3])
    except IOError as err:
        print err.message
