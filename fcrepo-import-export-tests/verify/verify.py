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
import argparse
import sys
import hashlib
import os
import logging

from source import HttpSource
from source import FileSource

if sys.version_info[0] < 3:
    from ConfigParser import SafeConfigParser
else:
    from configparser import SafeConfigParser

CONFIG = 'config.ini'
REPORT_FILE = 'verification_report.txt'


def getKey(item):
    return item[0]

def check_sources(origSource, newSource):
    num_missing = 0
    num_desc_match_err = 0
    num_bin_match_err = 0
    num_files = 0

    for newResourceName in newSource:
        binary = False

        try:
            # fetch the resource triples from new place & sort it
            newTriplesStr = newSource.fetchResourceTriples(newResourceName)
            newTriples = sorted(newTriplesStr.strip().split('\n'))

            # fetch the resource from original place
            origResourceName = translate_to_desc(newSource, origSource, newTriples[0][1:newTriples[0].find('> <')])

            origTriples = origSource.fetchResourceTriples(origResourceName)

            # was the resource there?
            if origTriples is None:
                logger.error('ERR: Resource Missing: Resource not found in original system:\n\t{0}'.format(newResourceName))
                num_missing += 1
                continue

            logger.info('Looking at: {}...'.format(newResourceName))

            # sort the triples
            origTriples = sorted(origTriples.strip().split('\n'))

            if settings.FCREPO_BINARY_URI in newTriplesStr:
                binary = True

            # test if they are eqivalent
            if set(origTriples) != set(newTriples):
                logger.error('ERR: Resource Mismatch: {0}'.format(newResourceName))
                num_desc_match_err += 1

            if binary is True:
                origSHA1 = [x for x in origTriples if 'http://www.loc.gov/premis/rdf/v1#hasMessageDigest' in x]
                if len(origSHA1) != 1:
                   logger.error('Couldn\'t find SHA1 for binary: {0}\n'.format(newResourceName))

                origSHA1 = origSHA1[0][origSHA1[0].rfind('> <') + 3:-3]
                if not check_binaries(origSource, newSource, origResourceName, newResourceName,
                        origSHA1.replace('urn:sha1:', '')):
                    num_bin_match_err += 1

            num_files += 1

        except IOError as err:
            logger.error('Unable to access resource: {0}\nError: {1}\n'.format(newResourceName, err))

    logger.info('\nDone checking objects. Looked at {0} objects in {1}.\n'.format(num_files, newSource))

    return {'rec_count':num_files, 'missing':num_missing, 'desc_mismatch':num_desc_match_err,
            'bin_mismatch':num_bin_match_err}

def check_binaries(origSource, newSource, origResourceName, newResourceName, origResourceSHA1):

    origSHA1 = hashlib.sha1()
    newSHA1 = hashlib.sha1()

    origSHA1.update(origSource.fetchBinaryResource(origResourceName))
    newSHA1.update(newSource.fetchBinaryResource(newResourceName))

    logger.debug('SHA1:\n\tresource: {0}\n\torig sha1: {1}\n\tnew sha1: {2}'.format(
          origResourceSHA1, origSHA1.hexdigest(), newSHA1.hexdigest()))

    # logic: compare what the original description file says to what was computed.
    # then compare the two newly computed values, if all is well, they should all be equal
    if origResourceSHA1 != origSHA1.hexdigest() or origSHA1.hexdigest() != newSHA1.hexdigest():
        logger.debug('SHA1:\n\tfrom resource: {0}\n\torig sha1: {1}\n\tnew sha1: {2}'.format(
            origResourceSHA1, origSHA1.hexdigest(), newSHA1.hexdigest()))
        logger.error('ERR: Binary Mismatch: Binary resources do not match for resource: {}'.format(
            origResourceName))
        logger.error('\tSHA1:\n\t\tresource: {0}\n\t\torig sha1: {1}\n\t\tnew sha1: {2}'.format(
            origResourceSHA1, origSHA1.hexdigest(), newSHA1.hexdigest()))
        return False

    return True

# normalize the resource string for the different systems.
# this will return the translation for getting the description data for an object.
def translate_to_desc(origin, recipient, resource):
    logger.debug("translate: resource is: {0}\n\tfrom:{1}\n\tto:{2}".format(resource, origin, recipient))

    if isinstance(origin, FileSource):
        res = resource.replace(origin.getBaseUri(), recipient.getBaseUri())

        if isinstance(recipient, FileSource):
            return resource

        if isinstance(recipient, HttpSource):
            if settings.FILE_FCR_METADATA in resource:
                return res.replace(settings.FILE_FCR_METADATA, 'fcr:metadata')
            else:
                return res + '/fcr:metadata'

    elif isinstance(origin, HttpSource):
        if isinstance(recipient, HttpSource):
            return resource

        if isinstance(recipient, FileSource):
            if origin.is_binary(resource):

                if 'fcr:metadata' in resource:
                    res = resource.replace('fcr:metadata', settings.FILE_FCR_METADATA)
                    return res.replace(origin.baseUri, recipient.desc_dir)
                else:
                    res = resource + '/' + settings.FILE_FCR_METADATA
                    return res.replace(origin.baseUri, recipient.desc_dir)

            else:
                res = resource
                if res.endswith('/'):
                    res = res[:-1]
                res += recipient.getFileExt()
                return res.replace(origin.baseUri, recipient.desc_dir)

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--loglevel', 
                        help='''Level of output into log [DEBUG, INFO, WARN, 
                                ERROR], default is WARN. To list the records 
                                being looked at, set this to INFO''',
                        default='WARN')
    parser.add_argument('--config', '-c', help='Path to import/export config')
    parser.add_argument('--user', '-u', help='''Server credentials in the form
                                                user:password''')
                        
    args = parser.parse_args()

    settings.init()

    if not args.config:
        cfgParser = SafeConfigParser()
        cfgParser.read(CONFIG)
        test_mode = cfgParser.get('general', 'test_mode')

        fedoraUrl = cfgParser.get('fedora1', 'baseUri')
        auth = tuple(cfgParser.get('fedora1', 'auth').split(':'))

        fileDir = cfgParser.get('file1', 'baseUri')
        if not fileDir.endswith('/'):
            fileDir += '/'

        fileExt = cfgParser.get('file1', 'ext')

        binDir = (fileDir + 
                  cfgParser.get('file1', 'bin_path') + 
                  cfgParser.get('file1', 'prefix')
                  )
        descDir = (fileDir + 
                   cfgParser.get('file1', 'desc_path') + 
                   cfgParser.get('file1', 'prefix')
                   )
        out_file = cfgParser.get('general', 'report_dir') + REPORT_FILE
        
    else:
        print("loading opts from import/export config file")
        with open(args.config, 'r') as f:
            opts = [line for line in f.read().split('\n')]

        for line in range(len(opts)):
            if opts[line] == '-m':
                test_mode = opts[line + 1]
            elif opts[line] == '-r':
                fedoraUrl = opts[line + 1]
            elif opts[line] == '-d':
                descPath = opts[line + 1]
            elif opts[line] == '-b':
                binPath = opts[line + 1]
            elif opts[line] == '-x':
                fileExt = opts[line + 1]
            elif opts[line] == '-l':
                pass
            else:
                pass
        
        fileDir = os.path.commonprefix([descPath, binPath])
        descDir = fileDir + os.path.relpath(descPath, fileDir) + "/rest"
        binDir = fileDir + os.path.relpath(binPath, fileDir) + "/rest"
        out_file = './verification_report.txt'
        auth = tuple(args.user.split(':'))

    loglevel = args.loglevel
    numeric_level = getattr(logging, loglevel.upper(), None)
    logger = logging.getLogger('output')
    filehandler = logging.FileHandler(filename=out_file, mode='w')
    filehandler.setLevel(numeric_level)
    logger.addHandler(filehandler)
    logger.setLevel(numeric_level)

    logger.debug('bin_dir = {0}\ndesc_dir = {1}'.format(binDir, descDir))

    if (binDir is None or descDir is None) or (binDir == descDir):
        logger.error('Unable to run: the export must be in two separate directories.')
        exit()

    httpSource = HttpSource(fedoraUrl, auth)
    fileSource = FileSource(fileDir, descDir, binDir, fileExt)

    logger.warn('Checking differences between two systems:');
    logger.warn('\tSource One: {0}\n\tSource Two: {1}\n'.format(fedoraUrl, fileDir))

    import_stats = {}
    export_stats = {}

    if test_mode == 'export' or test_mode == 'both':
        logger.warn('------- Export test: walking the files comparing them to Fedora ---------\n')
        export_stats = check_sources(origSource=httpSource, newSource=fileSource)

    if test_mode == 'import' or test_mode == 'both':
        logger.warn('------- Import test: walking Fedora comparing that to the files ---------\n')
        import_stats = check_sources(origSource=fileSource, newSource=httpSource)

    total_objects = 0
    if len(export_stats):
        logger.warn('Export test results:\n\tMissing Records: {}'.format(export_stats['missing']))
        logger.warn('\tRDF Resource Mismatch: {}'.format(export_stats['desc_mismatch']))
        logger.warn('\tNon RDF Resource Mismatch: {}'.format(export_stats['bin_mismatch']))
        total_objects = export_stats['rec_count']

    if len(import_stats):
        logger.warn('Import test results:\n\tMissing Records: {}'.format(import_stats['missing']))
        logger.warn('\tRDF Resource Mismatch: {}'.format(import_stats['desc_mismatch']))
        logger.warn('\tNon RDF Resource Mismatch: {}'.format(import_stats['bin_mismatch']))
        total_objects += import_stats['rec_count']

    logger.warn('*'*100)
    logger.warn('\nFinished verifying systems. Looked at {0} total objects.\n'.format(total_objects))

