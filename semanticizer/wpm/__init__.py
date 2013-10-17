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

from .wpmdata_inproc import WpmDataInProc
from .wpmdata_redis import WpmDataRedis

wpm_dumps = {}


def init_datasource(wpm_languages):
    """Set the datasource and init it"""
    for langcode, langconfig in wpm_languages.iteritems():
        load_wpm_dump(langconfig['source'], langcode, **langconfig['initparams'])

def load_wpm_dump(datasource, langcode, **kwargs):
    # XXX These things should really have better names like just "redis".
    if datasource == "WpmDataInProc":
        cls = WpmDataInProc
    elif datasource == "WpmDataRedis":
        cls = WpmDataRedis
    else:
        raise ValueError("Unknown backend {}".format(datasource))

    wpm_dumps[langcode] = cls(langcode, **kwargs)
