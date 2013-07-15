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

from sklearn.externals import joblib

import os, yaml

class ModelStore():
    def __init__(self, model_dir):
        self.model_dir = model_dir
        self.model_cache = {}

    def load_model(self, modelname):
        if modelname.endswith(".pkl"):
            return self.load_model(modelname[:-4])

        if modelname in self.model_cache:
            return self.model_cache[modelname]

        modelfile = os.path.join(self.model_dir, modelname)
        model = joblib.load(modelfile + ".pkl")

        description = {"name": modelname, "source": modelfile + ".pkl"}
        if os.path.exists(modelfile + ".yaml"):
            description.update(yaml.load(file(modelfile + ".yaml")))

        self.model_cache[modelname] = (model, description)
        return (model, description)

    def save_model(self, model, modelname, description=None):
        if modelname.endswith(".pkl"):
            modelname = modelname[:-4]

        modelfile = os.path.join(self.model_dir, modelname)
        model = joblib.dump(model, modelfile + ".pkl")

        if description != None:
            yaml.save(file(modelfile + ".yaml"))
