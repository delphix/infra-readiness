#! /usr/bin/env python
#================================================================================
# File:     exec_network_test.ps1
# Type:     powershell script
# Author:   Delphix Professional Services
# Date:     08/16/2017
#
# Copyright and license:
#
#       Licensed under the Apache License, Version 2.0 (the "License"); you may
#       not use this file except in compliance with the License.
#
#       You may obtain a copy of the License at
#     
#               http://www.apache.org/licenses/LICENSE-2.0
#
#       Unless required by applicable law or agreed to in writing, software
#       distributed under the License is distributed on an "AS IS" basis,
#       WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#
#       See the License for the specific language governing permissions and
#       limitations under the License.
#     
#       Copyright (c) 2015 by Delphix.  All rights reserved.
#
# Description:
#
#   Powershell script to conduct network latency and throughput test on a
#   specified Delphix virtualization engine.
#
#
# Command-line parameters:
#
#   dlpxengine     IP hostname or address of the Delphix virtualization engine
#   dlpxuser       Delphix Admin username
#   dlpxpwd        Delphix Admin password
#   tgtlist        Run test on single host
#   logfile        Custome logfile name
#   debug          Debug Mode
#   verbose        Verbose Mode
#
# Modifications:
#   Ajay Thotangare     08/16/17    1st Version 
#================================================================================

import signal
import time
import sys
import getopt
import getpass
import os
import logging

from delphixpy.delphix_engine import DelphixEngine
from delphixpy.web.network.test import latency, throughput
from delphixpy.web import host
from delphixpy import job_context
from delphixpy.exceptions import HttpError, JobError
from delphixpy.web.vo import NetworkLatencyTestParameters, NetworkThroughputTestParameters

VERSION="v.0.0.001"
global logfile
logfile = 'exec_network_test.log'
try:
    os.remove(logfile)
except OSError:
    pass

#def create_logger():
global fh1, fh2, ch1
# create file handler which logs even debug messages
fh1 = logging.FileHandler(logfile, mode='a')
fh1.setLevel(10)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)-8s: %(message)s' , datefmt='%m/%d/%Y %I:%M:%S %p')
fh1.setFormatter(formatter)

# create file handler which logs even debug messages
fh2 = logging.FileHandler(logfile, mode='a')
fh2.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)-8s: %(message)s')
fh2.setFormatter(formatter)

# create file handler which logs even debug messages
fh3 = logging.FileHandler(logfile, mode='a')
fh3.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
fh3.setFormatter(formatter)

# create console handler with a higher log level
ch1 = logging.StreamHandler()
ch1.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)-8s: %(message)s')
ch1.setFormatter(formatter)

# create logger with 'ent'
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

    #return logger

def exit_gracefully(signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    signal.signal(signal.SIGINT, original_sigint)

    try:
        if raw_input("\nReally quit? (y/n)> ").lower().startswith('y'):
            sys.exit(1)

    except KeyboardInterrupt:
        print("Ok ok, quitting")
        sys.exit(1)

    # restore the exit gracefully handler here    
    signal.signal(signal.SIGINT, exit_gracefully)

def print_debug(print_obj, debug=False):
    """
    Call this function with a log message to prefix the message with DEBUG
    print_obj: Object to print to logfile and stdout
    debug: Flag to enable debug logging. Default: False
    :rtype: None
    """
    try:
        if debug is True:
            print 'DEBUG: {}'.format(str(print_obj))
            logger.debug(str(print_obj))
    except:
        pass

def print_info(print_obj, verbose=False):
    """
    Call this function with a log message to prefix the message with INFO
    """
    try:
        if verbose is True:
            print 'INFO : {}'.format(str(print_obj))
            logger.info(str(print_obj))
            #write_log('INFO : {}'.format(str(print_obj)))
    except:
        pass

def print_raw(print_obj, verbose=False):
    """
    Call this function with a log message to prefix the message with INFO
    """
    try:
        if verbose is True:
            print '{}'.format(str(print_obj))
            for handler in logger.handlers:
                logger.removeHandler(handler)
            logger.addHandler(fh3)
            logger.info(str(print_obj))
            logger.removeHandler(fh3)
            if debug is True:
                logger.addHandler(fh1)
            else:
                logger.addHandler(fh2)
    except:
        pass

def print_warning(print_obj, verbose=False):
    """
    Call this function with a log message to prefix the message with INFO
    """
    try:
        if verbose is True:
            print 'WARN : %s' % (str(print_obj))
            logger.warning(str(print_obj))
    except:
        pass

def print_error(print_obj, verbose=False):
    """
    Call this function with a log message to prefix the message with INFO
    """
    try:
        if verbose is True:
            print 'ERROR : %s' % (str(print_obj))
            logger.error(str(print_obj))
    except:
        pass

def check_ping(x):
    hostname = x
    if (os.name == "posix"):
        response = os.system("ping -c 1 " + hostname + " > /dev/null 2>&1" )
    elif (os.name == "nt"):
        response = os.system('PING ' + hostname + ' -n 1 | FIND /I /V "unreachable" | FIND /I "Reply from"  > NUL' )
    else:
        print "OS Not supported"
    # and then check the response...
    if response == 0:
        pingstatus = "Active"
    else:
        pingstatus = "InActive"
    return pingstatus

def genHostListsTesting():
    print ""
    del activehost_list[:]
    activehost = {'keyname': '192.168.116.141', 'keyreference': 'UNIX_HOST-27' , 'keyaddress': '192.168.116.141', 'keyhostype': 'UnixHost', 'keyconnectorport': '0'}
    activehost_list.append(activehost)
    activehost = {'keyname': '192.168.116.217', 'keyreference': 'WINDOWS_HOST-30' , 'keyaddress': '192.168.116.217', 'keyhostype': 'WindowsHost', 'keyconnectorport': '0'}
    activehost_list.append(activehost)
    activehost = {'keyname': '192.168.116.134', 'keyreference': 'WINDOWS_HOST-29' , 'keyaddress': '192.168.116.134', 'keyhostype': 'WindowsHost', 'keyconnectorport': '9100'}
    activehost_list.append(activehost)

def genHostLists(tgtlist,force):
    print_raw("",verbose)
    print_info("# >>> Generating list of environments to conduct Network Tests. Please wait ........... <<< ",verbose)
    print_raw("",verbose)

    print_raw ("{0:28} {1:20} {2:15} {3:6}".format("EnvironmentName", "EnvironmentReference", "IP Address", "Ping"),verbose=True)
    print_raw ("{0:28} {1:20} {2:15} {3:6}".format("-"*28, "-"*20,"-"*15,"-"*6),verbose=True)
    #host.get_all(engine)
    for obj in host.get_all(engine):
        if not tgtlist:
            if force == True:
                status = "Active"
            else:
                status = check_ping(obj.address)
                #status = "Active"
            sep = ","
            if status == "Active":
                if obj.type == 'WindowsHost':
                    activehost = {'keyname': obj.name, 'keyreference': obj.reference, 'keyaddress': obj.address, 'keyhostype': obj.type, 'keyconnectorport': obj.connector_port}
                    activehost_list.append(activehost)
                    print_raw ("{0:28} {1:20} {2:15} {3:6}".format(obj.name, obj.reference, obj.address, "Force OK" if force else "OK"),verbose=True)
                else:
                    activehost = {'keyname': obj.name, 'keyreference': obj.reference, 'keyaddress': obj.address, 'keyhostype': obj.type, 'keyconnectorport': "0"}
                    activehost_list.append(activehost)
                    print_raw ("{0:28} {1:20} {2:15} {3:6}".format(obj.name, obj.reference, obj.address, "Force OK" if force else "OK"),verbose=True)
            else:
                inactivehost = {'keyname': obj.name, 'keyreference': obj.reference, 'keyaddress': obj.address}
                inactivehost_list.append(inactivehost)
                print_raw ("{0:28} {1:20} {2:15} {3:6}".format(obj.name, obj.reference, obj.address, "NOT OK"),verbose=True)
        else:
            if obj.name in tgthostlist:
                if force == True:
                    status = "Active"
                else:
                    status = check_ping(obj.address)
                #status = "Active"
                sep = ","
                if status == "Active":
                    if obj.type == 'WindowsHost':
                        activehost = {'keyname': obj.name, 'keyreference': obj.reference, 'keyaddress': obj.address, 'keyhostype': obj.type, 'keyconnectorport': obj.connector_port}
                        activehost_list.append(activehost)
                        print_raw ("{0:28} {1:20} {2:15} {3:6}".format(obj.name, obj.reference, obj.address, "Force OK" if force else "OK"),verbose=True)
                    else:
                        activehost = {'keyname': obj.name, 'keyreference': obj.reference, 'keyaddress': obj.address, 'keyhostype': obj.type, 'keyconnectorport': "0"}
                        activehost_list.append(activehost)
                        print_raw ("{0:28} {1:20} {2:15} {3:6}".format(obj.name, obj.reference, obj.address, "Force OK" if force else "OK"),verbose=True)
                else:
                    inactivehost = {'keyname': obj.name, 'keyreference': obj.reference, 'keyaddress': obj.address}
                    inactivehost_list.append(inactivehost)
                    print_raw ("{0:28} {1:20} {2:15} {3:6}".format(obj.name, obj.reference, obj.address, "NOT OK"),verbose=True)

    print_raw("",verbose)
    print_info("# >>> Environment list generated. <<< ",verbose)
    print_raw("", verbose=True)

def estimateTestDuration():
    #------------------------------------------------------------------------
    # Calculate counts and durations for the upcoming test jobs...
    #------------------------------------------------------------------------
    ahcount = len(activehost_list)
    latencyTestTime = ahcount * 20
    throughputTestTime = ahcount * 75 * 2
    totalTestTime = latencyTestTime + throughputTestTime
    print_info("# >>> Running {} network latency tests, {} network throughput tests (in both directions) <<< ".format(ahcount, ahcount * 2 ), verbose=True)
    print_info("# >>> Estimated duration to complete all tests is about {} seconds  <<< ".format(totalTestTime), verbose=True)
    print_raw("", verbose=True)

def runNetworkLatencyTest():
    #device_name = type(each_vm_hardware).__name__.split(".")[-1]  
    if len(activehost_list) > 0:
        for each_host in activehost_list:
            print_info("# >>> Processing Network Latency Test for: " + each_host['keyname'] + "(" + each_host['keyaddress'] + ")" + ". Please wait ........... <<< ",verbose)
            params = NetworkLatencyTestParameters()
            params.type = "NetworkLatencyTestParameters"
            params.remote_host = each_host['keyreference']

            try:
                jobRef = latency.create(engine,params)
                #print "jobRef = " + jobRef
                jobRefDict = {'job_type':'Latency', 'job_ref':jobRef}
                jobRefList.append(jobRefDict)
                #print (jobRefList)
                #jobName=engine.last_job
                print_info("# >>> Successfully completed Network Latency Test for: " + each_host['keyname'] + "(" + each_host['keyaddress'] + ")" + " <<< ",verbose)
                print_raw("",verbose)
            except JobError as e:
                #print_error("# >>> Failed Network Latency Test for: " + each_host['keyname'] + "(" + each_host['keyaddress'] + ")" + " <<< ",verbose=True)
                print_error("# >>> Failed Network Latency Test for: " + each_host['keyname'] + "(" + each_host['keyaddress'] + ")" + " <<< ",verbose)
                print_raw("",verbose)
                jobRefErrDict = {'job_type':'Latency', 'job_hostaddr':each_host['keyaddress'], 'job_hostname':each_host['keyname'], 'job_status' : 'Failed'}
                jobRefErrList.append(jobRefErrDict)
        #print_raw("", verbose=True)

def runNetworkThroughputTest():
    #print_raw("", verbose=True)
    if len(activehost_list) > 0:
        directions = ['TRANSMIT',  'RECEIVE']
        for each_host in activehost_list:
            for testdirection in directions:
                print_info("# >>> Processing Network Throughput " + testdirection + " Test for: " + each_host['keyname'] + "(" + each_host['keyaddress'] + ")" + ". Please wait ........... <<< ",verbose)
                if each_host['keyhostype'] == "WindowsHost" and int(each_host['keyconnectorport']) == 0 :
                        print_warning("# >>> Network Throughput (TRANSMIT/RECEIVE) Test NOT SUPPORTED for Windows Source Environment: " + each_host['keyname'] + "(" + each_host['keyaddress'] + ")" + ". <<<",verbose)
                        jobRefErrDict = {'job_type':'Throughput', 'job_hostaddr':each_host['keyaddress'], 'job_hostname':each_host['keyname'], 'job_direction':'Throughput Test', 'job_status' : 'Not Supported'}
                        jobRefErrList.append(jobRefErrDict)
                        break
                else:
                    params = NetworkThroughputTestParameters()
                    params.type = "NetworkThroughputTestParameters"
                    params.remote_host = each_host['keyreference']
                    params.direction = testdirection
                    try:
                        jobRef = throughput.create(engine,params)
                        #print "jobRef = " + jobRef
                        jobRefDict = {'job_type' : 'Throughput' , 'job_ref' : jobRef , 'job_direction' : testdirection }
                        jobRefList.append(jobRefDict)
                        #print (jobRefList)
                        #jobName=engine.last_job
                        print_info("# >>> Successfully completed Network Throughput " + testdirection + " Test for: " + each_host['keyname'] + "(" + each_host['keyaddress'] + ")" + " <<< ",verbose)
                    except JobError as e:
                        #print_error("# >>> ERROR : Failed Network Throughput " + testdirection + " Test for: " + each_host['keyname'] + "(" + each_host['keyaddress'] + ")" + " <<< ",verbose=True)
                        print_error("# >>> Failed Network Throughput " + testdirection + " Test for: " + each_host['keyname'] + "(" + each_host['keyaddress'] + ")" + " <<< ",verbose)
                        jobRefErrDict = {'job_type':'Throughput', 'job_hostaddr':each_host['keyaddress'], 'job_hostname':each_host['keyname'], 'job_direction':testdirection, 'job_status' : 'Failed'}
                        jobRefErrList.append(jobRefErrDict)
            print_raw("",verbose)


def jobExecCount(jobtype):
    cr = 0
    for jobRefRec in jobRefList:
        if jobRefRec['job_type'] == jobtype:
            cr = cr + 1
    return cr


def genLatencyTestResults(tgtlist):
    #if len(jobRefList) > 0:
    #if jobExecCount('Latency') > 0:
        tmpDict={}
        AllUnsortedLatencyTest=[]
        print_raw("", verbose=True)
        print_raw("=======================================================================================================",verbose)
        print_raw("# >>> List of latest Network Latency Test Results <<<",verbose)
        print_raw("=======================================================================================================",verbose)
        print_raw ("{0:55} {1:15} {2:<15} {3:>13}".format("Latency Test Name", "Remote Address", "Status", "Avg. Latency"), verbose=True)
        print_raw ("{0:55} {1:15} {2:<15} {3:>13}".format("-"*55, "-"*15,"-"*15,"-"*13), verbose=True)
        #print "-"*55, "-"*15,"-"*15,"-"*13
        if tgtlist:
            for jobRefRec in jobRefList:
                if jobRefRec['job_type'] == 'Latency':
                    NetworkLatencyTest  = latency.get(engine,jobRefRec['job_ref'])
                    if NetworkLatencyTest.average > 100:
                        lunit="msec"
                        avgLatency = "%.3f %s" % ((float(NetworkLatencyTest.average)/1000), lunit)
                    else:
                        lunit="usec"
                        avgLatency = "%.3f %s" % ((float(NetworkLatencyTest.average)/1), lunit)
                    print_raw ("{0:55} {1:15} {2:<15} {3:>13}".format(NetworkLatencyTest.name, NetworkLatencyTest.remote_address, NetworkLatencyTest.state,avgLatency), verbose=True)
            for jobRefErrRec in jobRefErrList:
                if jobRefErrRec['job_type'] == 'Latency':
                    print_raw ("{0:55} {1:15} {2:<15} {3:>13}".format(jobRefErrRec['job_hostname'] + "(" + jobRefErrRec['job_hostaddr'] + ")", jobRefErrRec['job_hostaddr'], jobRefErrRec['job_status'],"-"), verbose=True)
        else:
            i = 1
            LatencyTestResults = latency.get_all(engine)
            for LTR in LatencyTestResults:
                tmpDict = { "name" : LTR.name , "remote_address" : LTR.remote_address , "state" : LTR.state, "end_time" : LTR.end_time, "average" : LTR.average }
                AllUnsortedLatencyTest.append(tmpDict)

            AllNetworkLatencyTest = sorted(AllUnsortedLatencyTest, key=lambda k: (k['remote_address'],k['end_time']), reverse=True) 
            for elem in AllNetworkLatencyTest:
                if (AllNetworkLatencyTest.index(elem))+1 <= len(AllNetworkLatencyTest):
                    if ( i == 1):
                        thiselem = elem
                        prevelem = elem
                        if thiselem['average'] > 100:
                            lunit="msec"
                            avgLatency = "%.3f %s" % ((float(thiselem['average'])/1000), lunit)
                        else:
                            lunit="usec"
                            avgLatency = "%.3f %s" % ((float(thiselem['average'])/1), lunit)
                        print_raw ("{0:55} {1:15} {2:<15} {3:>13}".format(thiselem['name'], thiselem['remote_address'], thiselem['state'], avgLatency), verbose=True)
                    else:
                        thiselem = elem
                        prevelem = AllNetworkLatencyTest[AllNetworkLatencyTest.index(elem)-1] 
                        if ( thiselem['remote_address'] != prevelem['remote_address']):
                            if thiselem['average'] > 100:
                                lunit="msec"
                                avgLatency = "%.3f %s" % ((float(thiselem['average'])/1000), lunit)
                            else:
                                lunit="usec"
                                avgLatency = "%.3f %s" % ((float(thiselem['average'])/1), lunit)
                            print_raw ("{0:55} {1:15} {2:<15} {3:>13}".format(thiselem['name'], thiselem['remote_address'], thiselem['state'], avgLatency), verbose=True)                        
                    i = i + 1

            for jobRefErrRec in jobRefErrList:
                if jobRefErrRec['job_type'] == 'Latency':
                    print_raw ("{0:55} {1:15} {2:<15} {3:>13}".format(jobRefErrRec['job_hostname'] + "(" + jobRefErrRec['job_hostaddr'] + ")", jobRefErrRec['job_hostaddr'], jobRefErrRec['job_status'],"-"), verbose=True)

def genThroughputTestResults(tgtlist):
    #if len(jobRefList) > 0:
    #if jobExecCount('Throughput') > 0:
        tmpDict={}
        AllUnsortedThroughputTest=[]
        print_raw("", verbose=True)
        print_raw("=======================================================================================================",verbose)
        print_raw("# >>> List of latest Network Throughput Test Results <<<",verbose)
        print_raw("=======================================================================================================",verbose)

        print_raw ("{0:55} {1:15} {2:<15} {3:>15}".format("Throughput Test Name", "Direction", "Status", "Avg. Throughput"), verbose=True)
        print_raw ("{0:55} {1:15} {2:<15} {3:>15}".format("-"*55, "-"*15,"-"*15,"-"*15), verbose=True)
        #print "-"*55, "-"*15,"-"*15,"-"*15
        if tgtlist:
            for jobRefRec in jobRefList:
                if jobRefRec['job_type'] == 'Throughput':
                    NetworkThroughputTest  = throughput.get(engine,jobRefRec['job_ref'])
                    throughputval=NetworkThroughputTest.throughput
                    if throughputval > 0:
                        if (float(throughputval)/1073741824) > 0.975:
                            tunit="Gbps"
                            avgThroughput = "%.2f %s" % ((float(throughputval)/1073741824), tunit)
                        else:
                            tunit="Mbps"
                            avgThroughput = "%.2f %s" % ((float(throughputval)/1048576), tunit)
                    else:
                        lunit=" bps"
                        avgThroughput=str(throughputval) + " " + lunit
                    print_raw ("{0:55} {1:15} {2:<15} {3:>15}".format(NetworkThroughputTest.name, NetworkThroughputTest.parameters.direction, NetworkThroughputTest.state,avgThroughput), verbose=True)
            for jobRefErrRec in jobRefErrList:
                if jobRefErrRec['job_type'] == 'Throughput':
                    print_raw ("{0:55} {1:15} {2:<15} {3:>13}".format(jobRefErrRec['job_hostname'] + "(" + jobRefErrRec['job_hostaddr'] + ")", jobRefErrRec['job_direction'], jobRefErrRec['job_status'],"-"), verbose=True)
        else:
            i = 1
            ThroughputTestResults = throughput.get_all(engine)
            for TTR in ThroughputTestResults:
                tmpDict = { "name" : TTR.name , "remote_address" : TTR.remote_address , "direction" : TTR.parameters.direction, "state" : TTR.state, "end_time" : TTR.end_time, "throughput" : TTR.throughput }
                AllUnsortedThroughputTest.append(tmpDict)

            AllNetworkThroughputTest = sorted(AllUnsortedThroughputTest, key=lambda k: (k['remote_address'],k['direction'],k['end_time']), reverse=True) 
            for elem in AllNetworkThroughputTest:
                if (AllNetworkThroughputTest.index(elem))+1 <= len(AllNetworkThroughputTest):
                    if ( i == 1):
                        thiselem = elem
                        prevelem = elem
                        throughputval = thiselem['throughput']

                        if throughputval > 0:
                            if (float(throughputval)/1073741824) > 0.975:
                                tunit="Gbps"
                                avgThroughput = "%.2f %s" % ((float(throughputval)/1073741824), tunit)
                            else:
                                tunit="Mbps"
                                avgThroughput = "%.2f %s" % ((float(throughputval)/1048576), tunit)
                        else:
                            lunit=" bps"
                            avgThroughput=str(throughputval) + " " + lunit
                        print_raw ("{0:55} {1:15} {2:<15} {3:>13}".format(thiselem['name'], thiselem['direction'], thiselem['state'], avgThroughput), verbose=True)
                    
                    else:
                        thiselem = elem
                        prevelem = AllNetworkThroughputTest[AllNetworkThroughputTest.index(elem)-1] 
                        throughputval = thiselem['throughput']
                        if  not ( thiselem['remote_address'] == prevelem['remote_address'] and thiselem['direction'] == prevelem['direction'] ):
                            if throughputval > 0:
                                if (float(throughputval)/1073741824) > 0.975:
                                    tunit="Gbps"
                                    avgThroughput = "%.2f %s" % ((float(throughputval)/1073741824), tunit)
                                else:
                                    tunit="Mbps"
                                    avgThroughput = "%.2f %s" % ((float(throughputval)/1048576), tunit)
                            else:
                                lunit=" bps"
                                avgThroughput=str(throughputval) + " " + lunit
                            print_raw ("{0:55} {1:15} {2:<15} {3:>13}".format(thiselem['name'], thiselem['direction'], thiselem['state'], avgThroughput), verbose=True)                                                                                                    
                    i = i + 1            
            
            for jobRefErrRec in jobRefErrList:
                if jobRefErrRec['job_type'] == 'Throughput':
                    print_raw ("{0:55} {1:15} {2:<15} {3:>13}".format(jobRefErrRec['job_hostname'] + "(" + jobRefErrRec['job_hostaddr'] + ")", jobRefErrRec['job_direction'], jobRefErrRec['job_status'],"-"), verbose=True)

def genHostNotPingedResults():
    if len(inactivehost_list) > 0:
        print_raw("", verbose=True)
        print_raw("=======================================================================================================",verbose)
        print_raw("# >>> List of Hosts/Environments those are not reachable <<< ",verbose)
        print_raw("=======================================================================================================",verbose)
        print_raw ("{0:25} {1:25}".format("Host Name","IP Address"), verbose=True)
        print_raw ("{0:25} {1:25}".format("-"*25, "-"*25), verbose=True)
        #print "-"*25, "-"*25
        for each_host in inactivehost_list:
            print_raw ("{0:25} {1:25}".format(each_host['keyname'],each_host['keyaddress']), verbose=True)
        print_raw("", verbose=True)

def usage():
    print ( "Usage: " + sys.argv[0] + " [ [-h] | [-e][-u][-p][-t][-v][-d][-l][-f] ]" )
    print ( "Execute Network Latency/Throughput Tests and display results." )
    print ( " " )
    print ( "  -e    Delphix engine IP address or host name" )
    print ( "Optional Arguments:" )
    print ( "  -h    Show this message and exit" )
    print ( "  -u    Delphix Admin Username" )
    print ( "  -p    Delphix Admin Password" )
    print ( "  -t    Single OR comma seperated list of Host Names in quotes to run Network Tests" )
    print ( "  -v    Verbose Mode" )
    print ( "  -d    debug Mode" )
    print ( "  -f    force network tests even if host cannot be pinged from localhost" )
    print ( " " )
    print ( "Examples" )
    print ( "========" )
    print ( sys.argv[0] + " -d 192.168.116.131" )
    print ( sys.argv[0] + " -d 192.168.116.131 -u delphix_admin" )
    print ( sys.argv[0] + " -d 192.168.116.131 -u delphix_admin -p delphix" )
    print ( sys.argv[0] + " -d 192.168.116.131 -u delphix_admin -p delphix -t <target_host_ip/name>" )
    print ( sys.argv[0] + " -e 192.168.116.131 -u delphix_admin -p delphix -t 192.168.116.141" )
    print ( sys.argv[0] + " -e 192.168.116.131 -u delphix_admin -p delphix -t <target_host_ip/name list>" )
    print ( sys.argv[0] + " -e 192.168.116.131 -u delphix_admin -p delphix -t '192.168.116.141,192.168.116.217,192.168.116.134'" )
    print ( sys.argv[0] + " -e 192.168.116.131 -u delphix_admin -p delphix -t '192.168.116.141,192.168.116.217,192.168.116.134' -v" )
    print ( sys.argv[0] + " -e 192.168.116.131 -u delphix_admin -p delphix -t '192.168.116.141,192.168.116.140' -f" )

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "e:u:p:t:l:dvhf", ["dlpxengine=", "dlpxuser=","dlpxpwd=","tgtlist=","logfile=", "debug","verbose","help", "force"])

        global engine
        global activehost
        global activehost_list
        global inactivehost
        global inactivehost_list
        global jobRefDict
        global jobRefList
        global jobRefErrDict
        global jobRefErrList
        global verbose
        global debug
        global force
        global tgthostlist

        #logfile = ""
        dlpxengine = ""
        dlpxuser = ""
        dlpxpwd = ""
        tgtlist= ""
        debug = False
        force = False
        verbose = False

        for o, a in opts:
            if o == "-v":
                verbose = True
            elif o == "-d":
                debug = True
            elif o == "-f":
                force = True
            elif o in ("-h", "--help"):
                usage()
                sys.exit()
            elif o in ("-e", "--dlpxengine"):
                dlpxengine = a
            elif o in ("-u", "--dlpxuser"):
                dlpxuser = a
            elif o in ("-p", "--dlpxpwd"):
                dlpxpwd = a
            elif o in ("-t", "--tgtlist"):
                tgtlist = a
            elif o in ("-l", "--logfile"):
                logfile = a
            else:
                assert False, "unhandled option"
     
        if not dlpxengine:
            print "Option -e not specified"
            usage()
            sys.exit()

        if not dlpxuser:
            while not dlpxuser:
                dlpxuser = raw_input("Enter Delphix Admin Username (e.g. delphix_admin), 'quit' to exit > ")
                if dlpxuser == "quit":
                    sys.exit();

        if not dlpxpwd:
            while not dlpxpwd:
                dlpxpwd = getpass.getpass()

        if tgtlist:            
            [tgthostlist.strip() for tgthostlist in tgtlist.split(",")]             
            tgthostlist = [x.strip() for x in tgtlist.split(",")]
        
        if debug is True:
            verbose = True
            logger.addHandler(fh1)
            print_info('Debug Logging is enabled.',verbose)
        else:
            logger.addHandler(fh2)
            #print_info('Debug Logging is NOT enabled.',verbose)
        
        activehost = {}
        activehost_list = []
        inactivehost = {}
        inactivehost_list = []
        jobRefDict = {}
        jobRefList = []
        jobRefErrDict = {}
        jobRefErrList = []


        engine = DelphixEngine(dlpxengine, dlpxuser, dlpxpwd, "DOMAIN")
        
        print_raw("",verbose)
        print_raw("INFRASTRUCTURE READINESS REPORT (IRR) - Network Tests",verbose)
        print_raw("=====================================================",verbose)
        print_raw(time.strftime("%a %b %d %H:%M:%S %Z %Y") + " : Start Time",verbose)
        
        #genHostListsTesting(tgtlist)
        genHostLists(tgtlist, force)
        estimateTestDuration()
        #sys.exit()
        runNetworkLatencyTest()
        runNetworkThroughputTest()
        genLatencyTestResults(tgtlist)
        genThroughputTestResults(tgtlist)
        genHostNotPingedResults()
        print_info(time.strftime("%a %b %d %H:%M:%S %Z %Y") + " : End Time",verbose)
        print_raw("",verbose=True)
        print_info("Logfile : exec_network_test.log generated for this run",verbose=True)
        print_raw("",verbose=True)

    except getopt.GetoptError as err:
        # print help information and exit:
        print(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    #Here we handle what we do when the unexpected happens
    except SystemExit as e:
        """
        This is what we use to handle our sys.exit(#)
        """
        sys.exit(e)
    except HttpError as e:
        """
        We use this exception handler when our connection to Delphix fails
        """
        print_error("Connection failed to the Delphix Engine")
        print_error( "Please check the ERROR message below")
        print_error(e.message)
        sys.exit(2)
    except JobError as e:
        """
        We use this exception handler when a job fails in Delphix so that we have actionable data
        """
        print_error("A job failed in the Delphix Engine")
        print_error(e.job)
        #elapsed_minutes = time_elapsed()
        #print_info(basename(__file__) + " took " + str(elapsed_minutes) + " minutes to get this far.")
        sys.exit(3)
    except KeyboardInterrupt:
        """
        We use this exception handler to gracefully handle ctrl+c exits
        """
        print_debug("You sent a CTRL+C to interrupt the process")
        #elapsed_minutes = time_elapsed()
        #print_info(basename(__file__) + " took " + str(elapsed_minutes) + " minutes to get this far.")
    except:
        """
        Everything else gets caught here
        """
        print "I am here unhandled"
        print_error(sys.exc_info()[0])
        print_error(traceback.format_exc())
        #elapsed_minutes = time_elapsed()
        #print_info(basename(__file__) + " took " + str(elapsed_minutes) + " minutes to get this far.")
        sys.exit(1)

if __name__ == "__main__":
    # store the original SIGINT handler
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)
    main()
