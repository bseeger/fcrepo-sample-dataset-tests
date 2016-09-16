
def init():
    global verbose
    global FCREPO_BINARY_URI
    global BINARY_EXT
    global FILE_FCR_METADATA

    verbose = False
    FCREPO_BINARY_URI = 'http://www.w3.org/ns/ldp#NonRDFSource'
    BINARY_EXT = '.binary'
    FILE_FCR_METADATA = 'fcr%3Ametadata.nt'


