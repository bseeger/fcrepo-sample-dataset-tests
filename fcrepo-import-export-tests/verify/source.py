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
import json
import requests
import os
import settings

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

    def __init__(self, baseUri, prefix):
        Source.__init__(self, baseUri, prefix)
        if prefix.startswith('/'):
            self.prefix = prefix[1:]

        self.num_files = 0
        self.num_dirs = 0

        self.filepath = os.path.join(self.baseUri.replace('file://', ''), self.prefix)

    def __str__(self):
        return self.baseUri

    def fetchResourceTriples(self, resource):
        # read file, return json object
        try:
            with open(resource, 'r') as fp:
                json_data = json.load(fp)
            return json_data

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

    # resource is the full path, so maybe we don't need prefix, though I could see
    # perhaps needing it down the road.
    def fetchResourceTriples(self, resource, mime='application/ld+json'):
        if settings.g_verbose:
            print('fetching HTTP resource: {0}'.format(resource))

        r = requests.get(resource, auth=(self.username, self.password), headers={'Accept': mime});
        if settings.g_verbose:
            print(r)
        if r.status_code == 200:
            if mime == 'application/ld+json':
                return r.json()
            else:
                if settings.g_verbose:
                    print('Invalid mime type of {0} requested, returning text'.format(mime))
                return r.text
        elif settings.g_verbose:
            print('HttpSource failed to get object: got status: ' + str(r.status_code))

        return None

    def next(self):
        # TODO - walk the fedora tree here...
        raise NotImplementedError('Check back soon...')


