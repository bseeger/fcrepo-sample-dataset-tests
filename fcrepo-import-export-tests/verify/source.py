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
import requests
import os
import settings



# make the resource string normalized for the systems we're talking to
def translate(recipient, resource):

    if isinstance(recipient, FileSource):
        if 'fcr:metadata' in resource:
            return resource.replace('fcr:metadata', settings.FILE_FCR_METADATA)
        elif resource.endswith('/'):
            return resource[:-1] + settings.BINARY_EXTS

    elif isinstance(recipient, HttpSource):
        if settings.FILE_FCR_METADATA in resource:
            return resource.replace(settings.FILE_FCR_METADATA, 'fcr:metadata')
        if resource.endswith(settings.BINARY_EXT):
            return resource.replace(settings.BINARY_EXT, '')
    else:
        return None

    return resource


class Source() :
    def __init__ (self, baseUri, prefix):
        self.baseUri = baseUri
        self.prefix = prefix

    def getBaseUri(self):
        return self.baseUri

    def getPrefix(self):
        return self.prefix

    def fetchResourceTriples(self, resource):
        raise NotImplementedError('Don\'t call this on the base class!')


class FileSource(Source):

    def __init__(self, baseUri, prefix, desc_dir, bin_dir):
        Source.__init__(self, baseUri, prefix)
        if prefix.startswith('/'):
            self.prefix = prefix[1:]

        self.num_files = 0
        self.num_dirs = 0
        self.desc_dir = desc_dir
        self.bin_dir = bin_dir

        self.filepath = os.path.join(self.baseUri.replace('file://', ''), self.desc_dir + '/' + self.prefix)

    def __str__(self):
        return self.baseUri

    def fetchBinaryResource(self, aresource):
        resource = translate(self, aresource)

        # just in case they sent in a the fcr:metadata in the uri
        if settings.FILE_FCR_METADATA in resource:
            resource = resource.replace('/' + settings.FILE_FCR_METADATA, settings.BINARY_EXT)
            resource = resource.replace(self.desc_dir, self.bin_dir)

        if settings.verbose:
            print('FileSource.fetchBinaryResource: resource is: {}', resource)

        with open(resource, 'rb') as fp:
            file_content = fp.read()

        return file_content


    def fetchResourceTriples(self, aresource):
        resource = translate(self, aresource)
        try:
            with open(resource, 'r') as fp:
                data = fp.read()
            return data

        except ValueError:
            print('ValueError on {}'.format(resource))

    def next(self):
        for dirpath, dirname, filenames in os.walk(self.filepath, onerror=FileSource.walkfailed):
            for name in filenames:
                yield os.path.join(dirpath,name)

    @staticmethod
    def walkfailed(err):
        print('Failed to navigate directory {0}'.format(err.filename))
        raise IOError('Directory not found: {0}'.format(err.filename))

class HttpSource(Source):

    def __init__(self, baseUri, prefix, user, passwd):
        Source.__init__(self, baseUri, prefix)
        self.username = user
        self.password = passwd

    def __str__(self):
        return self.baseUri + self.prefix

    def fetchBinaryResource(self, aresource):
        resource = translate(self, aresource)
        r = requests.get(resource, auth=(self.username, self.password))
        if r.status_code == 200:
            return r.content

        return None


    # resource is the full path, so maybe we don't need prefix, though I could see
    # perhaps needing it down the road.
    def fetchResourceTriples(self, aresource, mime='application/n-triples'):
        resource = translate(self, aresource)
        if settings.verbose:
            print('fetching HTTP resource: {0}'.format(resource))

        r = requests.head(resource, auth=(self.username, self.password))

        if settings.FCREPO_BINARY_URI in r.headers['link']:
            if 'fcr:metadata' not in resource:
                resource += '/fcr:metadata'

        r = requests.get(resource, auth=(self.username, self.password), headers={'Accept': mime});
        if settings.verbose:
            print(r)
        if r.status_code == 200:
            if mime == 'application/n-triples':
                return r.text
            else:
                #TODO - make this error msg more robust
                if settings.verbose:
                    print('Invalid mime type of {0} requested, returning text'.format(mime))
                return r.text
        elif settings.verbose:
            print('HttpSource failed to get object: got status: ' + str(r.status_code))

        return None

    def next(self):
        # TODO - walk the fedora tree here...
        # TODO TODO TODO
        raise NotImplementedError('Check back soon...')


