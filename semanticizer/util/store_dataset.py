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

import sys, os, re, argparse, urllib, urllib2, json
from collections import defaultdict
from timer import Timer
        
def parse_args():
    parser = argparse.ArgumentParser(
                description='Process and store a dataset.',
                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
                                     
    parser.add_argument('datafiles', metavar='file', nargs='+',
                   help='a set of datafiles to process')
                   
    group = parser.add_argument_group('Semanticizer')
    group.add_argument('--url', default='http://localhost:5000/',
                   help='URL where the semanticizer webservice is running')
    group.add_argument('--language', metavar='langcode',
                   default='en',
                   help='Language of the semanticizer (2 letters, eg. en)')
    group.add_argument('--semanticize', nargs=2, action='append',
                  metavar=('setting', 'value'),
                  default=[('save', "true")],
                  help='Setting for the semanticizer call')

    group = parser.add_argument_group('Feedback')
    group.add_argument('--feedback', nargs=3, action='append',
                   metavar=('type', 'pattern', 'replacement'),
                   help='Pattern to generate feedback filenames '
                        '(default: positive "\\.txt$" ".positives.txt")')
    group.add_argument('--default', 
                   default='negative', metavar='type',
                   help='Default type of feedback')
    group.add_argument('--no-default', action='store_true',
                   help='Do not use default feedback')

    group = parser.add_argument_group('Context')
    group.add_argument('--context-pattern', nargs=2,
                   metavar=('pattern', 'replacement'),
                   default=('^(?:.*/)*(.*?)(?:\.txt)?$', '\g<1>'),
                   help='Pattern to generate context from filename')
    group.add_argument('--context-prefix', 
                   metavar='prefix', default='',
                   help='Prefix to add to the context')
    
    args = parser.parse_args()
    if not args.feedback:
        args.feedback = [('positive', '\.txt$', '.positives.txt')]    
    
    return args

def store_dataset(args):
    semanticize_url = '%ssemanticize/%s' % (args.url, args.language)
    request_ids = defaultdict(list)
    for filename in args.datafiles:
        assert os.path.exists(filename)
        context = args.context_prefix + re.sub(args.context_pattern[0], \
                                               args.context_pattern[1], \
                                               filename)

        with Timer("Semanticizing %s" % filename, 'timer'):
            with open(filename) as file:
                lines = file.readlines()
                print "Read %d lines from %s." % (len(lines), filename)
    
                for line in lines:
                    data = [("context", context), ("text", line.strip())]
                    data.extend(args.semanticize)
                    url_data = urllib.urlencode(data)
                    result = json.loads(urllib2.urlopen(semanticize_url, 
                                                        url_data).read())                
                    print "Request %s: %d links" % \
                            (result["request_id"], len(result["links"]))
                    request_ids[filename].append(result["request_id"])
        
        with Timer("Feedback for %s" % context, 'timer'):
            feedback = []
            for (feedback_type, pattern, replacement) in args.feedback:
                feedback_filename = re.sub(pattern, replacement, filename)
                if not os.path.exists(feedback_filename):
                    print feedback_filename, "does not exist"
                with open(feedback_filename) as file:
                    lines = file.readlines()
                    print "Read %d lines of %s feedback from %s." % \
                            (len(lines), feedback_type, feedback_filename)
                    for line in lines:
                        feedback.append((feedback_type, line.strip()))

            if not args.no_default:
                feedback.append(("default", args.default))
            
            feedback_url = args.url + 'feedback/' + context
            url_data = urllib.urlencode(feedback)
            result = urllib2.urlopen(feedback_url, url_data).read()            
            print "%d items of feedback for %s: %s" % \
                    (len(feedback), context, result)
                
if __name__ == '__main__':
    args = parse_args()
    
    with Timer("Storing %d files" % len(args.datafiles), 'timer'):
        store_dataset(args)
