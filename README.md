# Infra-Readiness

## Purpose
Infra-readiness  is a set of scripts, which are delivered by Delphix professional services team. Scripts are written in Python and compiled to run from windows and linux machines.

No prior knowledge of Python is required. In fact, no programming experience whatsoever is required to use these scripts. These scripts are useful for
  - gathering the ESX & VM settings of the Delphix engine and check best practices.
  - run automated network tests

Check  [documentation](https://github.com/delphix/infra-readiness/wiki) for more details

## Usage

*Check ESXI Settings*
```sh
chk_esxi_settings --help
Script Version : 3.0
usage: chk_esxi_settings [-h] -s HOST [-o PORT] -u USER [-p PASSWORD] -e VM -t DISK_TYPE [-c] [-v] [-d]

Process args for retrieving all the Virtual Machines

optional arguments:
  -h, --help                               show this help message and exit
  -s HOST, --host HOST                     Remote host to connect to
  -o PORT, --port PORT                     Port to connect on
  -u USER, --user USER                     User name to use when connecting to host
  -p PASSWORD, --password PASSWORD         Password to use when connecting to host
  -e VM, --vm VM                           comma seperated One or more Virtual Machines to report on
  -c, --cert_check_skip                    skip ssl certificate check
  -t DISK_TYPE, --disk_type DISK_TYPE      Disk Storage Type (non_ssd (default) | ssd
  -d, --debug                              debug info
  -v VERBOSE, --verbose VERBOSE            verbose level... repeat up to three times.
```


*Exec Network Tests*
```sh
exec_network_test --help
Script Version : 3.0
usage: exec_network_test [-h] -e DLPXENGINE [-o PORT] -u DLPXUSER [-p DLPXPWD] [-t TGTLIST] [-l LOGFILE] [-f] [-v]

Process args for executing network tests

optional arguments:
  -h, --help                                show this help message and exit
  -e DLPXENGINE, --dlpxengine DLPXENGINE    Remote delphix engine host to connect
  -o PORT, --port PORT                      Port to connect on 
  -u DLPXUSER, --dlpxuser DLPXUSER          User name to use when connecting to delphix engine
  -p DLPXPWD, --dlpxpwd DLPXPWD             Password to use when connecting to host
  -t TGTLIST, --tgtlist TGTLIST             Comma seperated One or more Target Hosts to conduct network test
  -l LOGFILE, --logfile LOGFILE             Name of custom logfile
  -f, --force                               Force to mark target host(s) healthy for test
  -v, --verbose                             Verbose Mode of execution
```

## Contributing

All contributors are required to sign the Delphix Contributor Agreement prior to contributing code to an open source
repository. This process is handled automatically by [cla-assistant](https://cla-assistant.io/). Simply open a pull
request and a bot will automatically check to see if you have signed the latest agreement. If not, you will be prompted
to do so as part of the pull request process.

This project operates under the [Delphix Code of Conduct](https://delphix.github.io/code-of-conduct.html). By
participating in this project you agree to abide by its terms.

## Statement of Support

This software is provided as-is, without warranty of any kind or commercial support through Delphix. See the associated
license for additional details. Questions, issues, feature requests, and contributions should be directed to the
community as outlined in the [Delphix Community Guidelines](https://delphix.github.io/community-guidelines.html).

## License

This is code is licensed under the Apache License 2.0. Full license is available [here](./LICENSE).
