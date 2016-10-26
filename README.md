# fcrepo-sample-dataset-tests

This repository contains tests that can be performed on a Fedora4 repository. 

## Import / Export tests

This directory contains tests that will verify and validate that the
fcrepo-import-export client can successfully import data to or export data from a
Fedora4 server.

### Resources: 
* [Fedora4](http://github.com/fcrepo4/fcrepo4)
* [Fedora4 Import Export Client](http://github.com/fcrepo4-labs/fcrepo-import-export)
* [Import Export Datasets](http://github.com/fcrepo4-labs/fcrepo-sample-dataset)

Many of these tests assume that you've either already exported or imported data from/to a
Fedora4 system.  To learn how to export or import data, please visit the 
Fedora4 Import Export Client page, linked to above.


Below are the tests and their specific usage.
---

## Verify

This script has been run in python 2.7.11, but should, in theory, work in python 3.

This tool has the following modes:
* `export` : it will verify everything in the specified export directory is in Fedora4
* `import` : it will verify that everything in Fedora4 is located on the file system in the export directory
* `both` : runs both export and import mode on the sources.  This is the most comprehensive way to check the sources, but it may be slow.


How to use this in testing:
* Load a data set from [Import Export Datasets](http://github.com/fcrepo4-labs/fcrepo-sample-dataset), or use your own.
* Export data from a Fedora4 system in **n-triples** format, using the [Fedora4 Import Export Client](http://github.com/fcrepo4-labs/fcrepo-import-export)
* Configure this verification tool to point to both your Fedora4 server and the disk location where the files are.
* Run this tool and check the 'verification-report.txt' file that was created. It will report information on errors, if any are found. 

To run the verify test, first edit the configuration file ```config.ini``` (details below) and
then run:

    $> python ./verify.py

This will create a report file that's at the location specified in the configuration file.
To include more detailed information (including all the records being looked at), change loglevel to INFO:

    $> python ./verify.py --loglevel INFO


### Config

The configuration variables can be configured in the ```config.ini```, which should be
located in the same directory as the python script.

#### Config: ```general``` section
Which mode are you testing?  Values: import export both

    test_mode = export

Location of resulting report:

    report_dir = ./

#### Config:  ```file1``` section

The large assumption here is that the binary and description directories are
located in the same root directory.  This may or may not change in the future.

Currently the binary and description directories must be separate directories.  The tool has only
been tested with two separate directories.

Given the parameters below, the relevant directories would be found at:

    file:///Users/user1/location/of/files/desc_dir/fcrepo/rest
    file:///Users/user1/location/of/files/bin_dir/fcrepo/rest

This should be simplified, but for now this is how it goes.

The location of the root directory of where the export/import directories are located:

    baseUri = file:///Users/user1/location/of/files

The prefix of the fedora system that they data was exported from:

    prefix = /fcrepo/root

The path that contains the description data, subdirectory of the baseUri:

    desc_path = desc_dir

The path that contains the binary data, subdirectory of the baseUri:

    bin_path =  bin_dir

The extention to use in looking for files:

    ext = .nt

#### Config: ```fedora1``` section

The location of the fedora4 server:

    baseUri = http://localhost:8080

For a system with authentication turned on, the following are needed :

    auth = username:password
