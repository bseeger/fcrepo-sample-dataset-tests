#!/usr/bin/python
#
# Licensed to DuraSpace under one or more contributor license agreements.
# See the NOTICE file distributed with this work for additional information
# regarding copyright ownership.
#
# DuraSpace licenses this file to you under the Apache License,
# Version 2.0 (the "License"); you may not use this file except in
# compliance with the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# Author:  Bethany Seeger <bseeger@amherst.edu>
# Date Created: September 2016
#

from ConfigParser import SafeConfigParser
import argparse
import os
import json
from source import HttpSource
from source import FileSource
import settings

CONFIG = 'config.ini'
REPORT_FILE = 'verification_report.txt'


settings.init()
g_interactive = False

def getKey(item):
    return item[0]

def check_sources(origOne, newOne, output):
    num_files = 0
    i = 0
    print('checks_sources')
    output.write('Checking differences between {0} and {1}\n'.format(origOne, newOne))

    try:
        for newObj in newOne.next():
            if settings.g_verbose:
                print('Looking at {0}'.format(newObj))
            # fetch the new object's triples
            newJson = newOne.fetchResourceTriples(newObj)
            # fetch the original triples
            origJson = origOne.fetchResourceTriples(newJson[0]['@id'])
            if origJson is None:
                print("RESOURCE MISSING from original system: {0}".format(newObj))
                output.write('RESOURCE MISSING: Resource not found in original system:\n\t{0}'.format(newObj))
                if g_interactive and raw_input('RESOURCE MISSING. Keep going? Y, n: ').lower() != 'y':
                    output.write('Stopping at user\'s request\n')
                    break
                else:
                    continue

            # get a list of sorted tuples for each thing.
            newJsonTuples = sorted(newJson[0].items(), key=getKey)
            origJsonTuples = sorted(origJson[0].items(), key=getKey)

            temp = [x for x in newJsonTuples if x not in origJsonTuples]
            if len(temp) > 0:
                # they don't match!!! Ooops!
                print ("RESOURCE MISMATCH: {0}".format(newObj))
                output.write('RESOURCE MISMATCH: {0} \n'.format(newObj))
                # TODO - include temp list in output
                if g_interactive and raw_input('Resource Mismatch. Keep going? Y, n: ').lower() != 'y':
                    output.write('Stopping at user\'s request\n')
                    break

            num_files += 1

    except IOError as err:
        # TODO - make better, clearer error message
        print ("IO Error received!")
        output.write('Resource not processed {0}\nError: {1}\n'.format(newOne, err))

    output.write('Done checking objects. Looked at {0} objects in {1}.\n'.format(num_files, newOne))
    print('Done checking objects. Looked at {0} objects in {1}.'.format(num_files, newOne))
    return num_files

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', help='interactive mode', action='store_true')
    parser.add_argument('-v', help='verbose', action='store_true')
    args = parser.parse_args()

    if args.i:
        g_interactive = True
        print ("INTERACTIVE")
    if args.v:
        settings.g_verbose = True
        print ("VERBOSE")

    cfgParser = SafeConfigParser()
    cfgParser.read(CONFIG)

    mode = cfgParser.get('general', 'testing')
    out_file = cfgParser.get('general', 'report_dir') + REPORT_FILE

    fedoraUrl = cfgParser.get('fedora1', 'baseUri')
    fedoraPrefix = cfgParser.get('fedora1', 'prefix')
    user = cfgParser.get('fedora1', 'user')
    passwd = cfgParser.get('fedora1', 'password')

    fileDir = cfgParser.get('file1', 'baseUri') 
    filePrefix = cfgParser.get('file1', 'prefix')
    if not fileDir.endswith('/'):
        fileDir += '/'

    binDir = fileDir + cfgParser.get('file1', 'bin_path')
    descDir = fileDir + cfgParser.get('file1', 'desc_path')

    if binDir is None or descDir is None:
        print "Unable to run: the export must be in two separate directories."
        exit()

    # mode dictates order of arguments passed in.
    # if mode == import, pass in file1, then fedora1
    # if mode == export, pass in fedora1, then file1
    # in the future one may be able to test fedora against fedora, but that's down
    # the road. But that's why there's a number after 'file' and 'fedora'

    httpSource = HttpSource(fedoraUrl, fedoraPrefix, user, passwd)
    fileSourceBin = FileSource(binDir, filePrefix)
    fileSourceDesc = FileSource(descDir, filePrefix)

    total_objects = 0
    with open(out_file, 'w') as of:
        if mode.lower() == 'export':
            total_objects = check_sources(origOne=httpSource, newOne=fileSourceBin, output=of)
            total_objects += check_sources(origOne=httpSource, newOne=fileSourceDesc, output=of)
        elif mode.lower() == 'import':
            total_objects = check_sources(origOne=fileSourceBin, newOne=httpSource, output=of)
            total_objects += check_sources(origOne=fileSourceDesc, newOne=httpSource, output=of)

        of.write('Finished verifying systems. Looked at {0} total objects.'.format(total_objects))

