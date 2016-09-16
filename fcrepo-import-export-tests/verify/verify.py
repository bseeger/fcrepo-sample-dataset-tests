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

from __future__ import absolute_import, division, print_function

import settings
settings.init()

import argparse
from ConfigParser import SafeConfigParser
import hashlib
import json
import os

from source import HttpSource
from source import FileSource

CONFIG = 'config.ini'
REPORT_FILE = 'verification_report.txt'
g_interactive = False

def getKey(item):
    return item[0]

def check_sources(origSource, newSource, log):
    num_files = 0

    try:
        for newResourceName in newSource.next():
            binary = False

            if settings.verbose:
                print('Looking at {0}'.format(newResourceName))

            # fetch the new and old object's triples
            newJson = newSource.fetchResourceTriples(newResourceName)
            origResourceName = newJson[0]['@id']
            origJson = origSource.fetchResourceTriples(origResourceName)

            if settings.FCREPO_BINARY_URI in origJson[0]['@type']:
                binary = True


            if origJson is None:
                print('RESOURCE MISSING from original system: {0}'.format(newResourceName))
                log.write('RESOURCE MISSING: Resource not found in original system:\n\t{0}\n'.format(newResourceName))
                if g_interactive and raw_input('RESOURCE MISSING. Keep going? Y, n: ').lower() != 'y':
                    log.write('Stopping at user\'s request\n')
                    break
                else:
                    continue

            # get a list of sorted tuples for each thing.
            newJsonTuples = sorted(newJson[0].items(), key=getKey)
            origJsonTuples = sorted(origJson[0].items(), key=getKey)

            temp = [x for x in newJsonTuples if x not in origJsonTuples]
            # the metadata is not the same!
            if len(temp) > 0:
                # they don't match!!! Ooops!
                print ('ERR: RESOURCE MISMATCH: {0}'.format(newResourceName))
                log.write('ERR: RESOURCE MISMATCH: {0} \n'.format(newResourceName))
                # TODO - include temp list in log
                if g_interactive and raw_input('Resource Mismatch. Keep going? Y, n: ').lower() != 'y':
                    log.write('Stopping at user\'s request\n')
                    break

            if binary is True:
                origSHA1 = origJson[0]['http://www.loc.gov/premis/rdf/v1#hasMessageDigest'][0]['@id']
                check_binaries(origSource, newSource, origResourceName, newResourceName,
                        origSHA1.replace('urn:sha1:', ''), log)

            num_files += 1

    except IOError as err:
        # TODO - make better, clearer error message
        print ('IO Error received!')
        log.write('Resource not processed {0}\nError: {1}\n'.format(newSource, err))

    log.write('Done checking objects. Looked at {0} objects in {1}.\n'.format(num_files, newSource))
    print('Done checking objects. Looked at {0} objects in {1}.'.format(num_files, newSource))
    return num_files

def check_binaries(origSource, newSource, origResourceName, newResourceName, origResourceSHA1, log):

    origSHA1 = hashlib.sha1()
    newSHA1 = hashlib.sha1()

    origSHA1.update(origSource.fetchBinaryResource(origResourceName))
    newSHA1.update(newSource.fetchBinaryResource(newResourceName))

    if settings.verbose:
        print('SHA1:\n\tresource: {0}\n\torig sha1: {1}\n\tnew sha1: {2}'.format(
              origResourceSHA1, origSHA1.hexdigest(), newSHA1.hexdigest()))

    # logic: compare what the description file says to what was computed.
    # then compare the two computed values, if all is well, they should all be equal
    if origResourceSHA1 != origSHA1.hexdigest() or origSHA1.hexdigest() != newSHA1.hexdigest():
        if settings.verbose:
            print('SHA1:\n\tfrom resource: {0}\n\torig sha1: {1}\n\tnew sha1: {2}'.format(origResourceSHA1, origSHA1.hexdigest(), newSHA1.hexdigest()))

        print('ERR: RESOURCE MISMATCH: Binary resources do not match for resource: {}'.format(origResourceName))
        log.write('ERR: RESOURCE MISMATCH: Binary resources do not match for resource: {}\n'.format(origResourceName))
        log.write('\tSHA1:\n\t\tresource: {0}\n\t\torig sha1: {1}\n\t\tnew sha1: {2}\n'.format(origResourceSHA1, origSHA1.hexdigest(), newSHA1.hexdigest()))
        return False

    return True

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', help='interactive mode', action='store_true')
    parser.add_argument('-v', help='verbose', action='store_true')
    args = parser.parse_args()

    if args.i:
        g_interactive = True
    if args.v:
        settings.verbose = True

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

    binDir = cfgParser.get('file1', 'bin_path')
    descDir = cfgParser.get('file1', 'desc_path')

    if binDir is None or descDir is None:
        print('Unable to run: the export must be in two separate directories.')
        exit()

    # mode dictates order of arguments passed in.
    # if mode == import, pass in file1, then fedora1
    # if mode == export, pass in fedora1, then file1
    # in the future one may be able to test fedora against fedora, but that's down
    # the road. But that's why there's a number after 'file' and 'fedora'

    httpSource = HttpSource(fedoraUrl, fedoraPrefix, user, passwd)
    fileSource = FileSource(fileDir, filePrefix, descDir, binDir)


    total_objects = 0
    with open(out_file, 'w') as fp:
        fp.write('Checking differences between two systems:\n\t')
        if mode.lower() == 'export':
            fp.write('{0}\n\t{1}\n\n'.format(httpSource, fileSource))
            total_objects = check_sources(origSource=httpSource, newSource=fileSource, log=fp)
        elif mode.lower() == 'import':
            fp.write('{0}\n\t{1}\n\n'.format(fileSource, httpSource))
            total_objects = check_sources(origSource=fileSource, newSource=httpSource, log=fp)

        fp.write('*'*100)
        fp.write('\nFinished verifying systems. Looked at {0} total objects.\n'.format(total_objects))

