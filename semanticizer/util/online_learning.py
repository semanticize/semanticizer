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

import os, re, argparse, urllib, urllib2, json
from collections import defaultdict
from timer import Timer
from random import choice, shuffle
        
def parse_args():
    parser = argparse.ArgumentParser(
                description='Online learn a classifier.',
                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
                                     
    parser.add_argument('classifier', metavar='classifier', 
                   help='a classifier to train')
    parser.add_argument('datafiles', metavar='file', nargs='+',
                   help='a set of datafiles to process')
                   
    group = parser.add_argument_group('Semanticizer')
    group.add_argument('--url', default='http://localhost:5000/',
                   help='URL where the semanticizer webservice is running')

    group = parser.add_argument_group('Learning')
    group.add_argument('--learn', nargs=2, action='append',
                       metavar=('setting', 'value'), 
                       default=[('context', 'EMPTY')],
                       help='Setting for the learn call')
    group.add_argument('--model-prefix', metavar='prefix', 
                       default='Online.',
                       help='Prefix to add to the modelname')
    group.add_argument('--iterations', metavar='number', 
                       default=50, type=int,
                       help='Number of iterations for learning.f')

    group = parser.add_argument_group('Context')
    group.add_argument('--context-pattern', nargs=2,
                   metavar=('pattern', 'replacement'),
                   default=('^(?:.*/)*(.*?)(?:\.txt)?$', '\g<1>'),
                   help='Pattern to generate context from filename')
    group.add_argument('--context-prefix', 
                   metavar='prefix', default='',
                   help='Prefix to add to the context')

    group = parser.add_argument_group('Output')
    group.add_argument('--output', default=None,
                   help='Filename for the output')
    
    args = parser.parse_args()
    args.learn.append(('classifier', args.classifier))
    return args

def online_learning(args):
    results = defaultdict(list)
    
    shuffle(args.datafiles)
    for filename in args.datafiles:
        assert os.path.exists(filename)
        context = args.context_prefix + re.sub(args.context_pattern[0], \
                                               args.context_pattern[1], \
                                               filename)
        
        modelname = args.model_prefix + context.replace('/', '.')
        learn_url = args.url + 'learn/' + modelname
        url_data = urllib.urlencode(args.learn)
        
        print "Initializing model", modelname,
        print urllib2.urlopen(learn_url, url_data).read()

        train_files = [f for f in args.datafiles if f != filename]
        for i in range(args.iterations):
            print "%03d/%03d" % (i+1, args.iterations),
            train_filename = choice(train_files)
            #with Timer("Learning for %s" % train_filename, 'timer'):
            train_context = args.context_prefix + \
                            re.sub(args.context_pattern[0], \
                                   args.context_pattern[1], train_filename)

            url_data = urllib.urlencode({"context": train_context})
            print "Training model", modelname, "on", train_context,
            print urllib2.urlopen(learn_url, url_data).read()

            evaluate_url = args.url + 'evaluate/' + context
            url_data = urllib.urlencode({"model": modelname})
            result = json.loads(urllib2.urlopen(evaluate_url, url_data).read())
            print "%.4f %.4f %.4f" % \
                (result["macro_metrics"]["accuracy"],
                 result["macro_metrics"]["averagePrecision"],
                 result["macro_metrics"]["rPrecision"])
            results[filename].append(result)

    if args.output:
        with open(args.output, 'w') as out:
            out.write(json.dumps(results))

if __name__ == '__main__':
    args = parse_args()
    
    with Timer("Online learning %d files" % len(args.datafiles), 'timer'):
        online_learning(args)
