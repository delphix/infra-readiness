#! /usr/bin/env python
#================================================================================
# File:     exec_network_test
# Type:     python script
# Author:   Delphix Professional Services
# Date:     10/10/2017
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
#       Copyright (c) 2017 by Delphix.  All rights reserved.
#
# Description:
#
#   Python script to conduct network latency and throughput test on a
#   specified Delphix virtualization engine.
#
#

"""
Code    : exec_network_test
Syntax  :
Usage   : exec_network_test [-h] -e DLPX_ENG_HOST [-o PORT] -u DLPX_ADMIN_USER [-p PASSWORD] [-t DLPX_TARGET_HOSTS] 
                            [-l logfilename] [-v] [-f]

Process args for executing network tests

optional arguments:
  -h, --help                                                show this help message and exit
  -e DLPX_ENG_HOST,--dlpxengine DLPX_ENG_HOST               Remote delphix engine host to connect
  -o PORT, --port PORT                                      Port to connect on
  -u USER, --dlpxuser USER                                  User name to use when connecting to delphix engine
  -p PASSWORD, --dlpxpwd PASSWORD                           Password to use when connecting to delphix engine
  -t DLPX_TARGET_HOSTS, --tgtlist DLPX_TARGET_HOSTS         Comma seperated One or more Target Hosts to conduct network test
  -l LOGFILE, --logfile                                     Name of custom logfile
  -f , --force                                              Force to mark target host(s) healthy for test
  -v , --verbose                                            Verbose execution

# Modifications:
#   Ajay Thotangare     10/10/17    1st Version
#================================================================================
"""

import argparse
import getpass
import os
import time
import signal
import sys
#import getopt
#import logging


from delphixpy.delphix_engine import DelphixEngine
from delphixpy.web.network.test import latency, throughput
from delphixpy.web import host
from delphixpy import job_context
from delphixpy.exceptions import HttpError, JobError
from delphixpy.web.vo import NetworkLatencyTestParameters, NetworkThroughputTestParameters

class dlpxSession:

    def __init__(self, dlpxengine,dlpxuser,dlpxpwd,verbose):
        self.dlpxengine = dlpxengine
        self.dlpxuser = dlpxuser
        self.dlpxpwd = dlpxpwd

        self.version = "v.0.0.001"
        self.verbose = verbose

        self.mylist = []
        self.mydict = {}

        self.engine = None
        try:
            self.engine = DelphixEngine(self.dlpxengine, self.dlpxuser, self.dlpxpwd, "DOMAIN")
        except IOError as e:
            pass

        if not self.engine:
            print('Could not connect to the specified delphix engine using specified username and password')
            return -1

        self.logfile = "exec_network_test_" + time.strftime("%m%d%Y_%H%M%S") + ".log"
        self.f = open(self.logfile,"w")

    def closeLogFile(self):
        self.f.close()

    def printMsg (self,print_obj, verboseoutput, level, msgtype, hidemsgtype ):
        if ( verboseoutput ):
            if (msgtype == "I"):
                msghdr = "INFO  : "
            elif (msgtype == "W"):
                msghdr = "WARN  : "
            elif (msgtype == "E"):
                msghdr = "ERROR : "
            elif (msgtype == "G"):
                msghdr = "GOOD  : "
            else:
                msghdr = "INFO  : "

            if (level == "L0"):
                indentparam = ""
            elif (level == "L1"):
                indentparam = ">>> "
            elif (level == "L2"):
                indentparam = "    >>> "
            elif (level == "L3"):
                indentparam = "        >>> "
            else:
                indentparam = ">>> "

            if (hidemsgtype == "Y"):
                msghdr = ""
       
            self.f.write(msghdr + indentparam + print_obj + "\n") 
            print (msghdr + indentparam + print_obj)

    def check_ping(self,x):
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

    def genHostLists(self,tgthostlist=False,force=False):
        self.printMsg (" ","True","L0","I","Y")
        self.printMsg("Generating list of environments to conduct Network Tests. Please wait ...........",self.verbose,"L1","I","N")
        self.printMsg (" ","True","L0","I","Y")

        self.printMsg ("{0:28} {1:20} {2:15} {3:6}".format("EnvironmentName", "EnvironmentReference", "IP Address", "Ping"),True,"L0","I","Y")
        self.printMsg ("{0:28} {1:20} {2:15} {3:6}".format("-"*28, "-"*20,"-"*15,"-"*6),True,"L0","I","Y")
        for obj in host.get_all(self.engine):
            if not tgthostlist:
                if force == True:
                    status = "Active"
                else:
                    status = self.check_ping(obj.address)

                sep = ","
                if status == "Active":
                    if obj.type == 'WindowsHost':
                        activehost = {'keyname': obj.name, 'keyreference': obj.reference, 'keyaddress': obj.address, 'keyhostype': obj.type, 'keyconnectorport': obj.connector_port}
                    else:
                        activehost = {'keyname': obj.name, 'keyreference': obj.reference, 'keyaddress': obj.address, 'keyhostype': obj.type, 'keyconnectorport': "0"}

                    activehost_list.append(activehost)
                    self.printMsg ("{0:28} {1:20} {2:15} {3:6}".format(obj.name, obj.reference, obj.address, "Force OK" if force else "OK"),True,"L0","I","Y")                       

                else:
                    inactivehost = {'keyname': obj.name, 'keyreference': obj.reference, 'keyaddress': obj.address}
                    inactivehost_list.append(inactivehost)
                    self.printMsg ("{0:28} {1:20} {2:15} {3:6}".format(obj.name, obj.reference, obj.address, "NOT OK"),True,"L0","I","Y")

            else:
                if obj.name in tgthostlist:
                    if force == True:
                        status = "Active"
                    else:
                        status = self.check_ping(obj.address)

                    sep = ","
                    if status == "Active":
                        if obj.type == 'WindowsHost':
                            activehost = {'keyname': obj.name, 'keyreference': obj.reference, 'keyaddress': obj.address, 'keyhostype': obj.type, 'keyconnectorport': obj.connector_port}
                        else:
                            activehost = {'keyname': obj.name, 'keyreference': obj.reference, 'keyaddress': obj.address, 'keyhostype': obj.type, 'keyconnectorport': "0"}

                        activehost_list.append(activehost)
                        self.printMsg ("{0:28} {1:20} {2:15} {3:6}".format(obj.name, obj.reference, obj.address, "Force OK" if force else "OK"),True,"L0","I","Y")

                    else:
                        inactivehost = {'keyname': obj.name, 'keyreference': obj.reference, 'keyaddress': obj.address}
                        inactivehost_list.append(inactivehost)
                        self.printMsg ("{0:28} {1:20} {2:15} {3:6}".format(obj.name, obj.reference, obj.address, "NOT OK"),True,"L0","I","Y")


        self.printMsg (" ","True","L0","I","Y")
        self.printMsg("Environment list generated.",self.verbose,"L1","I","N")
        self.printMsg (" ","True","L0","I","Y")

    def estimateTestDuration(self):
        #------------------------------------------------------------------------
        # Calculate counts and durations for the upcoming test jobs...
        #------------------------------------------------------------------------
        ahcount = len(activehost_list)
        latencyTestTime = ahcount * 20
        throughputTestTime = ahcount * 75 * 2
        totalTestTime = latencyTestTime + throughputTestTime
        self.printMsg ("Running {} network latency tests, {} network throughput tests (in both directions)".format(ahcount, ahcount * 2 ),True,"L1","I","N")
        self.printMsg ("Estimated duration to complete all tests is about {} seconds".format(totalTestTime),True,"L1","I","N")
        self.printMsg (" ","True","L0","I","Y")

    def defineGlobals(self):
        global jobRefDict
        global jobRefList
        jobRefDict = {}
        jobRefList = []

        global jobRefErrDict
        global jobRefErrList
        jobRefErrDict = {}
        jobRefErrList = []

        global activehost
        global activehost_list
        activehost = {}
        activehost_list = []

        global inactivehost
        global inactivehost_list
        inactivehost = {}
        inactivehost_list = []


    def runNetworkLatencyTest(self):
        if len(activehost_list) > 0:
            for each_host in activehost_list:
                self.printMsg ("Processing Network Latency Test for: " + each_host['keyname'] + "(" + each_host['keyaddress'] + ")" + ". Please wait ...........",self.verbose,"L1","I","N")
                params = NetworkLatencyTestParameters()
                params.type = "NetworkLatencyTestParameters"
                params.remote_host = each_host['keyreference']

                try:
                    jobRef = latency.create(self.engine,params)
                    jobRefDict = {'job_type':'Latency', 'job_ref':jobRef}
                    jobRefList.append(jobRefDict)
                    self.printMsg ("Successfully completed Network Latency Test for: " + each_host['keyname'] + "(" + each_host['keyaddress'] + ")" ,self.verbose,"L1","I","N")
                    self.printMsg (" ","True","L0","I","Y")
                except JobError as e:
                    self.printMsg ("Failed Network Latency Test for: " + each_host['keyname'] + "(" + each_host['keyaddress'] + ")" ,self.verbose,"L1","E","N")
                    self.printMsg (" ",self.verbose,"L0","I","Y")
                    jobRefErrDict = {'job_type':'Latency', 'job_hostaddr':each_host['keyaddress'], 'job_hostname':each_host['keyname'], 'job_status' : 'Failed'}
                    jobRefErrList.append(jobRefErrDict)

    def runNetworkThroughputTest(self):
        if len(activehost_list) > 0:
            directions = ['TRANSMIT',  'RECEIVE']
            for each_host in activehost_list:
                for testdirection in directions:
                    self.printMsg ("Processing Network Throughput " + testdirection + " Test for: " + each_host['keyname'] + "(" + each_host['keyaddress'] + ")" + ". Please wait ........... ",self.verbose,"L1","I","N")
                    if each_host['keyhostype'] == "WindowsHost" and int(each_host['keyconnectorport']) == 0 :
                            self.printMsg ("Network Throughput (TRANSMIT/RECEIVE) Test NOT SUPPORTED for Windows Source Environment: " + each_host['keyname'] + "(" + each_host['keyaddress'] + ")" ,self.verbose,"L1","W","N")
                            jobRefErrDict = {'job_type':'Throughput', 'job_hostaddr':each_host['keyaddress'], 'job_hostname':each_host['keyname'], 'job_direction':'Throughput Test', 'job_status' : 'Not Supported'}
                            jobRefErrList.append(jobRefErrDict)
                            break
                    else:
                        params = NetworkThroughputTestParameters()
                        params.type = "NetworkThroughputTestParameters"
                        params.remote_host = each_host['keyreference']
                        params.direction = testdirection
                        try:
                            jobRef = throughput.create(self.engine,params)
                            jobRefDict = {'job_type' : 'Throughput' , 'job_ref' : jobRef , 'job_direction' : testdirection }
                            jobRefList.append(jobRefDict)
                            self.printMsg ("Successfully completed Network Throughput " + testdirection + " Test for: " + each_host['keyname'] + "(" + each_host['keyaddress'] + ")" ,self.verbose,"L1","I","N")
                        except JobError as e:
                            self.printMsg ("Failed Network Throughput " + testdirection + " Test for: " + each_host['keyname'] + "(" + each_host['keyaddress'] + ")",self.verbose,"L1","E","N")
                            jobRefErrDict = {'job_type':'Throughput', 'job_hostaddr':each_host['keyaddress'], 'job_hostname':each_host['keyname'], 'job_direction':testdirection, 'job_status' : 'Failed'}
                            jobRefErrList.append(jobRefErrDict)
                self.printMsg (" ","True","L0","I","Y")

    def jobExecCount(self,jobtype):
        cr = 0
        for jobRefRec in jobRefList:
            if jobRefRec['job_type'] == jobtype:
                cr = cr + 1
        return cr

    def genLatencyTestResults(self,tgtlist=False):
        if self.jobExecCount('Latency') > 0:
            tmpDict={}
            AllUnsortedLatencyTest=[]
            self.printMsg (" ","True","L0","I","Y")
            self.printMsg ("=======================================================================================================",self.verbose,"L0","I","Y")
            self.printMsg ("List of latest Network Latency Test Results <<<",self.verbose,"L0","I","Y")
            self.printMsg ("=======================================================================================================",self.verbose,"L0","I","Y")
            self.printMsg ("{0:55} {1:15} {2:<15} {3:>13}".format("Latency Test Name", "Remote Address", "Status", "Avg. Latency"),"True","L0","I","Y")
            self.printMsg ("{0:55} {1:15} {2:<15} {3:>13}".format("-"*55, "-"*15,"-"*15,"-"*13), "True","L0","I","Y")

            if tgtlist:
                for jobRefRec in jobRefList:
                    if jobRefRec['job_type'] == 'Latency':
                        NetworkLatencyTest  = latency.get(self.engine,jobRefRec['job_ref'])
                        if NetworkLatencyTest.average > 100:
                            lunit="msec"
                            avgLatency = "%.3f %s" % ((float(NetworkLatencyTest.average)/1000), lunit)
                        else:
                            lunit="usec"
                            avgLatency = "%.3f %s" % ((float(NetworkLatencyTest.average)/1), lunit)
                        self.printMsg ("{0:55} {1:15} {2:<15} {3:>13}".format(NetworkLatencyTest.name, NetworkLatencyTest.remote_address, NetworkLatencyTest.state,avgLatency), "True","L0","I","Y")
                for jobRefErrRec in jobRefErrList:
                    if jobRefErrRec['job_type'] == 'Latency':
                        self.printMsg ("{0:55} {1:15} {2:<15} {3:>13}".format(jobRefErrRec['job_hostname'] + "(" + jobRefErrRec['job_hostaddr'] + ")", jobRefErrRec['job_hostaddr'], jobRefErrRec['job_status'],"-"), "True","L0","I","Y")
            else:
                i = 1
                LatencyTestResults = latency.get_all(self.engine)
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
                            self.printMsg ("{0:55} {1:15} {2:<15} {3:>13}".format(thiselem['name'], thiselem['remote_address'], thiselem['state'], avgLatency), "True","L0","I","Y")
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
                                self.printMsg ("{0:55} {1:15} {2:<15} {3:>13}".format(thiselem['name'], thiselem['remote_address'], thiselem['state'], avgLatency), "True","L0","I","Y")                    
                        i = i + 1

                for jobRefErrRec in jobRefErrList:
                    if jobRefErrRec['job_type'] == 'Latency':
                        self.printMsg ("{0:55} {1:15} {2:<15} {3:>13}".format(jobRefErrRec['job_hostname'] + "(" + jobRefErrRec['job_hostaddr'] + ")", jobRefErrRec['job_hostaddr'], jobRefErrRec['job_status'],"-"), "True","L0","I","Y")  

    def genThroughputTestResults(self,tgtlist):
        if self.jobExecCount('Throughput') > 0:
            tmpDict={}
            AllUnsortedThroughputTest=[]
            self.printMsg (" ","True","L0","I","Y")
            self.printMsg ("=======================================================================================================",self.verbose,"L0","I","Y")
            self.printMsg ("# >>> List of latest Network Throughput Test Results <<<",self.verbose,"L0","I","Y")
            self.printMsg ("=======================================================================================================",self.verbose,"L0","I","Y")

            self.printMsg ("{0:55} {1:15} {2:<15} {3:>15}".format("Throughput Test Name", "Direction", "Status", "Avg. Throughput"),True,"L0","I","Y")
            self.printMsg ("{0:55} {1:15} {2:<15} {3:>15}".format("-"*55, "-"*15,"-"*15,"-"*15),True,"L0","I","Y")

            if tgtlist:
                for jobRefRec in jobRefList:
                    if jobRefRec['job_type'] == 'Throughput':
                        NetworkThroughputTest  = throughput.get(self.engine,jobRefRec['job_ref'])
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
                        self.printMsg ("{0:55} {1:15} {2:<15} {3:>15}".format(NetworkThroughputTest.name, NetworkThroughputTest.parameters.direction, NetworkThroughputTest.state,avgThroughput),True,"L0","I","Y")
                for jobRefErrRec in jobRefErrList:
                    if jobRefErrRec['job_type'] == 'Throughput':
                        self.printMsg ("{0:55} {1:15} {2:<15} {3:>13}".format(jobRefErrRec['job_hostname'] + "(" + jobRefErrRec['job_hostaddr'] + ")", jobRefErrRec['job_direction'], jobRefErrRec['job_status'],"-"),True,"L0","I","Y")
            else:
                i = 1
                ThroughputTestResults = throughput.get_all(self.engine)
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
                            self.printMsg ("{0:55} {1:15} {2:<15} {3:>13}".format(thiselem['name'], thiselem['direction'], thiselem['state'], avgThroughput),True,"L0","I","Y")
                        
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
                                self.printMsg ("{0:55} {1:15} {2:<15} {3:>13}".format(thiselem['name'], thiselem['direction'], thiselem['state'], avgThroughput),True,"L0","I","Y")                                                                                                
                        i = i + 1            
                
                for jobRefErrRec in jobRefErrList:
                    if jobRefErrRec['job_type'] == 'Throughput':
                        self.printMsg ("{0:55} {1:15} {2:<15} {3:>13}".format(jobRefErrRec['job_hostname'] + "(" + jobRefErrRec['job_hostaddr'] + ")", jobRefErrRec['job_direction'], jobRefErrRec['job_status'],"-"),True,"L0","I","Y")     

    def genHostNotPingedResults(self):
        if len(inactivehost_list) > 0:
            self.printMsg (" ","True","L0","I","Y")
            self.printMsg ("=======================================================================================================",self.verbose,"L0","I","Y")
            self.printMsg ("List of Hosts/Environments (Unable to ping from localhost) ",self.verbose,"L0","I","Y")
            self.printMsg ("=======================================================================================================",self.verbose,"L0","I","Y")
            self.printMsg  ("{0:25} {1:25}".format("Host Name","IP Address"),True,"L0","I","Y")
            self.printMsg  ("{0:25} {1:25}".format("-"*25, "-"*25),True,"L0","I","Y")

            for each_host in inactivehost_list:
                self.printMsg  ("{0:25} {1:25}".format(each_host['keyname'],each_host['keyaddress']),True,"L0","I","Y")
            self.printMsg (" ","True","L0","I","Y")

def exit_gracefully(signum, frame):
    # put back the original signal handler when when CTRL+C is pressed
    signal.signal(signal.SIGINT, original_sigint)

    try:
        if raw_input("\nReally quit? (y/n)> ").lower().startswith('y'):
            sys.exit(1)

    except KeyboardInterrupt:
        print("quitting....")
        sys.exit(1)

    # restore the exit gracefully handler here    
    signal.signal(signal.SIGINT, exit_gracefully)

    

def GetArgs():
    """
    Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(description='Process args for executing network tests')
    parser.add_argument('-e', '--dlpxengine', required=True, action='store', help='Remote delphix engine host to connect')
    parser.add_argument('-o', '--port', type=int, default=443, action='store', help='Port to connect on')
    parser.add_argument('-u', '--dlpxuser', required=True, action='store', help='User name to use when connecting to delphix engine')
    parser.add_argument('-p', '--dlpxpwd', required=False, action='store',help='Password to use when connecting to host')
    parser.add_argument('-t', '--tgtlist', required=False, action='store', help='Comma seperated One or more Target Hosts to conduct network test')
    parser.add_argument('-l', '--logfile', required=False, action='store', help='Name of custom logfile')
    parser.add_argument('-f', '--force', required=False, action='store_true', help='Force to mark target host(s) healthy for test')
    parser.add_argument('-v', '--verbose', required=False, action='store_true', help='Verbose Mode of execution')
    args = parser.parse_args()
    return args

def main():
    try:
        tgthostlist = []
        args = GetArgs()

        dlpxengine = args.dlpxengine
        dlpxuser = args.dlpxuser
        if args.dlpxpwd:
            dlpxpwd = args.dlpxpwd
        else:
            dlpxpwd = getpass.getpass(prompt="Enter password for host {} and user {}: ".format(args.dlpxengine, args.dlpxuser))

        if args.tgtlist:        
            [tgthostlist.strip() for tgthostlist in args.tgtlist.split(",")]             
            tgthostlist = [x.strip() for x in args.tgtlist.split(",")]
        
        verbose = args.verbose
        verbose = True
        force = args.force

        dlpxSess = dlpxSession(dlpxengine,dlpxuser,dlpxpwd,verbose)

        dlpxSess.printMsg (" ","True","L0","I","Y")
        dlpxSess.printMsg ("INFRASTRUCTURE READINESS REPORT (IRR) - Network Tests",verbose,"L0","I","Y")
        dlpxSess.printMsg ("=====================================================",verbose,"L0","I","Y")
        dlpxSess.printMsg (time.strftime("%a %b %d %H:%M:%S %Z %Y") + " : Start Time",verbose,"L0","I","Y")
        dlpxSess.defineGlobals()
        dlpxSess.genHostLists(tgthostlist=tgthostlist,force=force)
        dlpxSess.estimateTestDuration()
        dlpxSess.runNetworkLatencyTest()
        dlpxSess.runNetworkThroughputTest()
        dlpxSess.genLatencyTestResults(tgtlist=tgthostlist)
        dlpxSess.genThroughputTestResults(tgtlist=tgthostlist)
        dlpxSess.genHostNotPingedResults()
        dlpxSess.printMsg (time.strftime("%a %b %d %H:%M:%S %Z %Y") + " : End Time",verbose,"L0","I","Y")
        dlpxSess.printMsg (" ","True","L0","I","Y")
        dlpxSess.printMsg ("Logfile : " + dlpxSess.logfile + " generated for this run",True,"L0","I","Y")
        dlpxSess.closeLogFile ()

    except SystemExit as e:
        """
        This is to handle sys.exit(#)
        """
        sys.exit(e)
    except HttpError as e:
        """
        This is to handle connection failure to Delphix
        """
        dlpxSess.printMsg ("Connection failed to the Delphix Engine","True","L1","E","N")
        dlpxSess.printMsg ("Please check the ERROR message below","True","L1","E","N")
        dlpxSess.printMsg (e.message,"True","L1","E","N")
        sys.exit(2)
    except JobError as e:
        """
        This is to handle job failure in Delphix
        """
        dlpxSess.printMsg ("A job failed in the Delphix Engine","True","L1","E","N")
        dlpxSess.printMsg (e.job,"True","L1","E","N")
        elapsed_minutes = time_elapsed()
        dlpxSess.printMsg (basename(__file__) + " took " + str(elapsed_minutes) + " minutes to get this far.","True","L1","E","N")
        sys.exit(3)

    except KeyboardInterrupt:
        """
        This is to gracefully handle ctrl+c exits
        """
        dlpxSess.printMsg ("You sent a CTRL+C to interrupt the process","True","L0","I","Y")
        elapsed_minutes = time_elapsed()
        dlpxSess.printMsg (basename(__file__) + " took " + str(elapsed_minutes) + " minutes to get this far.","True","L1","E","N")
    except:
        """
        All other exceptions are handled here
        """
        dlpxSess.printMsg ("Error::","True","L0","E","Y")
        dlpxSess.printMsg (sys.exc_info()[0],"True","L0","E","Y")
        dlpxSess.printMsg (traceback.format_exc(),"True","L0","E","Y")
        elapsed_minutes = time_elapsed()
        dlpxSess.printMsg (basename(__file__) + " took " + str(elapsed_minutes) + " minutes to get this far.","True","L1","E","N")
        sys.exit(1)

# Start program
if __name__ == "__main__":
    # store the original SIGINT handler
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)
    main()

