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
import rdflib
import logging

logger = logging.getLogger('output')

class Source() :
    def __init__ (self, baseUri):
        self.baseUri = baseUri

    def getBaseUri(self):
        return self.baseUri

    def fetchResourceTriples(self, resource):
        raise NotImplementedError('Don\'t call this on the base class!')


class FileSource(Source):

    def __init__(self, baseUri, desc_dir, bin_dir, ext):
        Source.__init__(self, baseUri)

        self.ext = ext  # file extension info
        self.desc_dir = desc_dir.replace('file://', '')
        self.bin_dir = bin_dir.replace('file://', '')

        self.to_check = [self.desc_dir + self.ext]
        for dirpath, dirname, filenames in os.walk(self.desc_dir.replace('file://', ''), onerror=FileSource.walkfailed):
            for name in filenames:
                self.to_check.append(os.path.join(dirpath,name))

    def __str__(self):
        return self.baseUri

    def __iter__(self):
        return self

    def __next__(self):
        if not self.to_check:
            raise StopIteration
        else:
            return self.to_check.pop()

    def getFileExt(self):
        return self.ext

    def fetchBinaryResource(self, aresource):
        resource = aresource
        # just in case they sent in a the fcr:metadata in the uri
        if settings.FILE_FCR_METADATA in resource:
            resource = resource.replace('/' + settings.FILE_FCR_METADATA, settings.BINARY_EXT)
            resource = resource.replace(self.desc_dir, self.bin_dir)

        logger.debug('FileSource.fetchBinaryResource: resource is: {}', resource)

        with open(resource, 'rb') as fp:
            file_content = fp.read()

        return file_content


    def fetchResourceTriples(self, resource):
        logger.debug('FileSource fetching: {}'.format(resource))
        try:
            with open(resource, 'r') as fp:
                data = fp.read()
            return data

        except ValueError:
            logger.error('ValueError on {}'.format(resource))


    @staticmethod
    def walkfailed(err):
        logger.error('Failed to navigate directory {0}'.format(err.filename))
        raise IOError('Directory not found: {0}'.format(err.filename))

class HttpSource(Source):

    def __init__(self, baseUri, auth):
        Source.__init__(self, baseUri)
        self.auth = tuple(auth.split(':'))

        # back up one directory to get the rest.xyz file
        self.to_check = [baseUri]

    def __str__(self):
        return self.baseUri

    def __iter__(self):
        return self

    def fetchBinaryResource(self, aresource):
        resource = aresource
        if 'fcr:metadata' in resource:
            resource = resource.replace('/fcr:metadata', '')

        logger.debug('HttpSource.fetchBinaryResource: resource is: {}', resource)
        r = requests.get(resource, auth=self.auth)
        if r.status_code == 200:
            return r.content

        return None


    def fetchResourceTriples(self, aresource, mime='application/n-triples'):
        resource = aresource

        if self.is_binary(resource) and 'fcr:metadata' not in resource:
            resource += '/fcr:metadata'

        logger.debug('fetching HTTP resource: {0}'.format(resource))

        r = requests.get(resource, auth=self.auth, headers={'Accept': mime});
        if r.status_code == 200:
            if mime == 'application/n-triples':
                return r.text
            else:
                #TODO - make this error msg more robust
                logger.info('Invalid mime type of {0} requested, returning text'.format(mime))
                return r.text
        else:
            logger.error('HttpSource failed to get object: got status: ' + str(r.status_code))

        return None

    # using link headers, determine whether a resource is rdf or non-rdf
    # author: Josh Westgard (jwestgard)
    def is_binary(self, node):
        response = requests.head(url=node, auth=self.auth)
        if response.status_code == 200 and response.links['type']['url'] == settings.FCREPO_BINARY_URI:
            return True
        else:
            return False


    # get the children of a resource based on ldp containment
    # author: Josh Westgard (jwestgard)
    def get_children(self, node):
        logger.debug("checking {}...".format(node))
        if self.is_binary(node):
            return None
        else:
            response = requests.get(node, auth=self.auth)
            graph = rdflib.Graph()
            graph.parse(data=response.text, format="text/turtle")
            predicate = rdflib.URIRef('http://www.w3.org/ns/ldp#contains')
            children = [str(obj) for obj in graph.objects(subject=None,
                                                          predicate=predicate)]
            return children

    # iterate the child nodes
    # author: Josh Westgard (jwestgard)
    def next(self):
       if not self.to_check:
            raise StopIteration
       else:
            current = self.to_check.pop()
            children = self.get_children(current)
            if children:
                self.to_check.extend(children)
            logger.debug('HttpSource:next: {}'.format(current))
            return current


