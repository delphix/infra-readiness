#!/usr/bin/env python

"""
#
# Copyright (c) 2017, 2018, 2019 by Delphix. All rights reserved.
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Copyright (c) 2015,2016 by Delphix. All rights reserved.
#
# Program Name : chk_esxi_settings.py
# Description  : Check settings of ESXI with respect to delphix
# Author       : Ajay Thotangare
# Created      : 10/17/2017 (v1.0.0)
#
Code    : chk_esxi_settings.py
Syntax  :
Usage   : chk_esxi_settings.py [-h] -s HOST [-o PORT] -u USER [-p PASSWORD] -e VM -t DISK_TYPE [-d]

Process args for retrieving all the Virtual Machines

optional arguments:
  -h, --help                           show this help message and exit
  -s HOST, --host HOST                 Remote host to connect to
  -o PORT, --port PORT                 Port to connect on
  -u USER, --user USER                 User name to use when connecting to host
  -p PASSWORD, --password PASSWORD     Password to use when connecting to host
  -e VM, --vm VM                       One or more Virtual Machines to report on
  -t DISK_TYPE, --disk_type DISK_TYPE  Disk Storage Type (non_ssd (default) | ssd
  -c, --cert_check_skip                skip ssl certificate check
  -d, --debug                          generate debug info

############################################################################
# Modified: Ajay Thotangare
# Modified: 11/15/2017
# Purpose : (1) Marked cert_check_skip as default option
#           (2) Added feature to detect storage path policy for vmdk's
#           (3) Modified format with sections number to reduce column width
############################################################################
# Modified: Ajay Thotangare
# Modified: 12/01/2017
# Purpose : (1) Check if 10% Memory is free for ESXI host
#           (2) Check if 4 CPU's are free for ESXI host
#           (3) Modified format with sections number to reduce column width
############################################################################

Comments: The code is a fork from py-vminfo.py
          [ https://github.com/lgeeklee/python-vmstats/blob/master/py-vminfo.py]
          which can be downloaded from github. It was modified to fit Delphix
          Infrastructure checklist script.
"""
import argparse
import atexit
import getpass
import logging.handlers
import math
import os
import os.path
import re
import ssl
import sys
from collections import defaultdict
from operator import itemgetter
from os import path

# from __future__ import print_function
# from pyVim.connect import SmartConnect, Disconnect
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vmodl, vim

# from ConfigParser import SafeConfigParser

parser = argparse.ArgumentParser(description='Process args for retrieving all the Virtual Machines')
parser.add_argument('-s', '--host', required=True, action='store', help='Remote host to connect to')
parser.add_argument('-o', '--port', type=int, default=443, action='store', help='Port to connect on')
parser.add_argument('-u', '--user', required=True, action='store', help='User name to use when connecting to host')
parser.add_argument('-p', '--password', required=False, action='store', help='Password to use when connecting to host')
parser.add_argument('-e', '--vm', required=True, action='store', help='One or more Virtual Machines to report on')
parser.add_argument('-c', '--cert_check_skip', default=True, required=False, action='store_true', help='skip ssl certificate check')
parser.add_argument('-t', '--disk_type', default='non_ssd', action='store', help='Disk Storage Type (non_ssd (default) | ssd')
parser.add_argument('-d', '--debug', default=False, required=False, action='store_true', help='debug info')
parser.add_argument('-v', '--verbose', action="store", help="verbose level... repeat up to three times.")

logger = logging.getLogger('Global')
logger.setLevel(logging.DEBUG)

if not os.path.exists('logs'): os.mkdir('logs')
if path.exists("logs/chk_esxi_settings_debug.log"): os.remove("logs/chk_esxi_settings_debug.log") 
if path.exists("logs/chk_esxi_settings_debug.txt"): os.remove("logs/chk_esxi_settings_debug.txt") 
if path.exists("logs/vm_stats.csv"): os.remove("logs/vm_stats.csv") 
if path.exists("logs/esx_global.csv"): os.remove("logs/esx_global.csv") 

f = open("logs/esx_global.csv", "w")
f.write("{}, {}, {}, {}, {}, {}, {}, {}, {}\n".format("esx_version", "esx_build", "esx_update", "cpus", "cores", "core_threads", "ht_active", "ht_enabled", "ht_best_practice"))
f.close()

f = open("logs/vm_stats.csv", "w")
f.write("{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}\n".format("guest_name", "cpus", "cpu_cores", "cpu_reserved", "cpu_best_practice", "memoryGB", "memory_reserved", "memory_best_practice", "memory_reserved_needed", "ht_sharing", "ht_best_practice", "controller / LUN count", "storage_best_practice"))
f.close()


log_file_handler = logging.handlers.TimedRotatingFileHandler('logs/chk_esxi_settings_debug.log', when='M', interval=1440)
log_file_handler.setFormatter( logging.Formatter('%(asctime)s [%(levelname)s](%(name)s:%(funcName)s:%(lineno)d): %(message)s') )
log_file_handler.setLevel(logging.DEBUG)
logger.addHandler(log_file_handler)

## also log to the console at a level determined by the --verbose flag
#console_handler = logging.StreamHandler() # sys.stderr
#console_handler.setLevel(logging.CRITICAL) # set later by set_log_level_from_verbose() in interactive sessions
#console_handler.setFormatter( logging.Formatter('[%(levelname)s](%(name)s): %(message)s') )
#logger.addHandler(console_handler)

class multifile(object):
    def __init__(self, files):
        self._files = files
    def __getattr__(self, attr, *args):
        return self._wrap(attr, *args)
    def _wrap(self, attr, *args):
        def g(*a, **kw):
            for f in self._files:
                res = getattr(f, attr, *args)(*a, **kw)
            return res
        return g

# for a tee-like behavior, use like this:
sys.stdout = multifile([ sys.stdout, open('logs/chk_esxi_settings.txt', 'w') ])

def GetParserInfo():
    dx_setting = {}
    # parser = SafeConfigParser()
    # parser.read("delphix_recommended.ini")
    # section_name = "dx_settings"
    # for name, value in parser.items(section_name):
    #   dx_setting[name] = value
    dx_setting['esxi_version'] = '5.0'
    dx_setting['esxi_hyperthreading'] = 'false'
    dx_setting['esxi_ha'] = 'enabled'
    dx_setting['esxi_drs'] = 'disabled'
    dx_setting['cpu_reservation'] = 'enabled'
    dx_setting['memory_reservation'] = 'enabled'
    dx_setting['minimum_memory'] = '64'
    dx_setting['minimum_cpu'] = '8'
    dx_setting['ht_sharing'] = 'none'
    dx_setting['nic_driver'] = 'vmxnet3'
    dx_setting['non_ssd_disk_provision_type'] = 'Thick'
    dx_setting['non_ssd_disk_provision_format'] = 'Eager-Zero'
    dx_setting['ssd_disk_provision_type'] = 'Thick'
    dx_setting['ssd_disk_provision_format'] = 'Lazy-Zero'
    dx_setting['disk_controllers'] = 'Evenly Distribute VMDKs'
    dx_setting['disk_controllers'] = 'Balance All 4 Controllers'
    dx_setting['scsi_controller_type'] = 'LSI Logic'
    dx_setting['vnic'] = 'vmxnet3'
    dx_setting['vm_htsharing'] = 'none'
    dx_setting['esxi_powermgmt'] = 'High Performance'
    dx_setting['vm_storagepathpolicy'] = 'VMW_PSP_RR'
    return (dx_setting)

def get_lun(scsiLun, key):
    return [x for x in scsiLun if x.key == key]

def get_disk_lun(scsiLun, lun_key, names):
    lun = get_lun(scsiLun, lun_key)
    if len(lun) == 0:
        return False
    return lun[0].lunType == "disk" and lun[0].canonicalName in names

def find_scsictrl_balanced(scsi_hdd_cnt):
    prevVal = 0
    currVal = 0
    ctrl_balanced='Pass'
    i = 0
    #for key, value in sorted(scsi_hdd_cnt.iteritems()): #python 2.7
    for key, value in sorted(scsi_hdd_cnt.items()):
      currVal = value
      if i == 0:
        prevVal = value
        i = i + 1
      if key == 'SCSI controller 0':
        currVal = (value - 1)
        prevVal = (value - 1)
      if currVal != prevVal:
        #print "Controllers are imbalanced",key,scsi_hdd_cnt
        ctrl_balanced='Fail'
        break
    return ctrl_balanced        

def PrintVmInfo(args, vm, content, vchtime, esxiinfo):
    tbd = "[ Verify Manually on ESXi Host ]"
    nav = "N/A"
    sep = "="
    disk_list = []
    network_list = []
    scsi_contr_list = []
    controller_units = []

    dx_setting = GetParserInfo()
    logger.info("dx_setting: \n{}".format(dx_setting))

    summary = vm.summary
    myconfig = vm.config
    vm_hardware = vm.config.hardware
    logger.info("summary: \n{}".format(summary))

    dict_tree = lambda: defaultdict(dict_tree)
    vm_info = dict_tree()
    hdd = dict_tree()
    logger.info("dict_tree: {}".format(dict_tree))

    # Convert limit and reservation values from -1 to None
    if vm.resourceConfig.cpuAllocation.limit == -1:
        vmcpulimit = "None"
    else:
        vmcpulimit = "{} Mhz".format(vm.resourceConfig.cpuAllocation.limit)

    if vm.resourceConfig.memoryAllocation.limit == -1:
        vmmemlimit = "None"
    else:
        vmmemlimit = "{} MB".format(vm.resourceConfig.cpuAllocation.limit)

    if vm.resourceConfig.cpuAllocation.reservation == 0:
        vmcpures = "None"
    else:
        vmcpures = "{} Mhz".format(vm.resourceConfig.cpuAllocation.reservation)

    if vm.resourceConfig.memoryAllocation.reservation == 0:
        vmmemres = "None"
    else:
        vmmemres = "{} MB".format(vm.resourceConfig.memoryAllocation.reservation)

    
    logger.info("vm_hardware: {}".format(vm_hardware))

    for each_vm_hardware in vm_hardware.device:
        if (each_vm_hardware.key >= 1000) and (each_vm_hardware.key < 2000):
            vm_info['scsi'][each_vm_hardware.key]['label'] = each_vm_hardware.deviceInfo.label
            vm_info['scsi'][each_vm_hardware.key]['summary'] = each_vm_hardware.deviceInfo.summary
            scsi_contr_list.append('{} | {}'.format(each_vm_hardware.deviceInfo.label,
                                                    each_vm_hardware.deviceInfo.summary))
            for device_key in each_vm_hardware.device:
                vm_info['disks'][device_key]['busNumber'] = each_vm_hardware.busNumber

        elif (each_vm_hardware.key >= 2000) and (each_vm_hardware.key < 3000):
            vm_info['disks'][each_vm_hardware.key]['label'] = each_vm_hardware.deviceInfo.label
            vm_info['disks'][each_vm_hardware.key]['unitNumber'] = each_vm_hardware.unitNumber
            vm_info['disks'][each_vm_hardware.key]['capacity'] = each_vm_hardware.capacityInKB / 1024 / 1024
            vm_info['disks'][each_vm_hardware.key]['thinProvisioned'] = each_vm_hardware.backing.thinProvisioned
            vm_info['disks'][each_vm_hardware.key]['fileName'] = each_vm_hardware.backing.fileName

            thickProvisioned = ""
            eagerZero = ""

            if (each_vm_hardware.backing.thinProvisioned is False):
                thickProvisioned = 'true'
                if (each_vm_hardware.backing.eagerlyScrub is True):
                    eagerZero = 'true'
                else:
                    eagerZero = 'true'
            else:
                thickProvisioned = 'false'
                eagerZero = 'NA'

            hdd[each_vm_hardware.deviceInfo.label]['eagerZero'] = eagerZero
            hdd[each_vm_hardware.deviceInfo.label]['thickProvisioned'] = thickProvisioned
            hdd[each_vm_hardware.deviceInfo.label]['controller_unit'] = str(
                vm_info['disks'][each_vm_hardware.key]['busNumber']) + ':' + str(each_vm_hardware.unitNumber)
            controller_units.append(
                str(vm_info['disks'][each_vm_hardware.key]['busNumber']) + ':' + str(each_vm_hardware.unitNumber))

            hdd[each_vm_hardware.deviceInfo.label]['controller'] = str(
                vm_info['disks'][each_vm_hardware.key]['busNumber'])

            hdd[each_vm_hardware.deviceInfo.label]['sizeGB'] = each_vm_hardware.capacityInKB / 1024 / 1024

            disk_list.append(
                '{} | {:.1f}GB | Thin: {} | {} | Controller: {}:{}'.format(each_vm_hardware.deviceInfo.label,
                                                                           each_vm_hardware.capacityInKB / 1024 / 1024,
                                                                           each_vm_hardware.backing.thinProvisioned,
                                                                           each_vm_hardware.backing.fileName,
                                                                           vm_info['disks'][each_vm_hardware.key][
                                                                               'busNumber'],
                                                                           each_vm_hardware.unitNumber))
        elif (each_vm_hardware.key >= 4000) and (each_vm_hardware.key < 5000):
            device_name = type(each_vm_hardware).__name__.split(".")[-1]
            # network_list.append('{} | {} | {}'.format(each_vm_hardware.deviceInfo.label, each_vm_hardware.deviceInfo.summary, device_name))
            network_list.append(
                '{} | {} | {}'.format(each_vm_hardware.deviceInfo.label, each_vm_hardware.macAddress, device_name))

    if (esxi_info_stat == 1):
        print("")
        print(
            "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("SECTION - I : ESXi Host = " + summary.runtime.host.name)
        print(
            "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("")
        print("{0:50} {1:70} {2:30} {3:10}".format("Settings/Parameters/Version", "Current Value", "Recommended Value",
                                                   "Result"))
        print("{0:50} {1:70} {2:30} {3:10}".format(sep * 50, sep * 70, sep * 30, sep * 10))
        print("{0:50} {1:70} {2:30} {3:10}".format("ESXI Hardware", esxiinfo['Hardware'] , nav, nav))
        print("{0:50} {1:70} {2:30} {3:10}".format("ESXI Hostname", summary.runtime.host.name + '(' + args.host + ')',
                                                   nav, nav))
        esxi_version_result = "Pass" if esxi_version >= dx_setting['esxi_version'] else "Fail"
        print("{0:50} {1:70} {2:30} {3:10}".format("ESXI Version", esxi_version,
                                                   'ESXi ' + dx_setting['esxi_version'] + ' and Higher',
                                                   esxi_version_result))

        cpu_type = re.sub('\s+', ' ', summary.runtime.host.summary.hardware.cpuModel)
        print("{0:50} {1:70} {2:30} {3:10}".format("ESXI CPU Type", cpu_type, nav, nav))
        print(
            "{0:50} {1:<70} {2:30} {3:10}".format("ESXI CPU Sockets", summary.runtime.host.summary.hardware.numCpuPkgs,
                                                  nav, nav))
        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI Cores Per Socket", (
                summary.runtime.host.summary.hardware.numCpuCores / summary.runtime.host.summary.hardware.numCpuPkgs),
                                                    nav, nav))
        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXi Total CPU", summary.runtime.host.summary.hardware.numCpuCores,
                                                    nav, nav))
        # print("{0:50} {1:70} {2:30} {3:10}".format("ESXI Hyperthreading Active",tbd, dx_setting['hyperthreading'], nav))

        esxiAllocCPU = int(esxiinfo['totallocatedCPU'])
        esxiAllocCPU_fmt = "ESXI Total Allocated CPU"
        esxiAllocCPU_result = "Pass" if (int(summary.runtime.host.summary.hardware.numCpuCores) - int(
            esxiAllocCPU)) >= 4 else "Fail"
        print("{0:50} {1:<70} {2:30} {3:10}".format(esxiAllocCPU_fmt, esxiAllocCPU, "Atleast 4 ESX CPU free",
                                                    esxiAllocCPU_result))

        esxiHTConfig = str(esxiinfo['CPUhyperThreadingConfig'])
        esxiHTConfig_fmt = "ESXI Hyperthreading Enabled"
        esxiHTConfig_result = "Pass" if esxiHTConfig.lower() == dx_setting['esxi_hyperthreading'].lower() else "Fail"
        print("{0:50} {1:<70} {2:30} {3:10}".format(esxiHTConfig_fmt, esxiHTConfig, dx_setting['esxi_hyperthreading'],
                                                    esxiHTConfig_result))

        esxiPowerMgmtPolicy = esxiinfo['PowerMgmtPolicy']
        esxiPowerMgmtPolicy_fmt = "ESXi BIOS Power Management"
        esxiPowerMgmtPolicy_result = "Pass" if esxiPowerMgmtPolicy == dx_setting['esxi_powermgmt'] else "Fail"
        print("{0:50} {1:<70} {2:30} {3:10}".format(esxiPowerMgmtPolicy_fmt, esxiPowerMgmtPolicy,
                                                    dx_setting['esxi_powermgmt'], esxiPowerMgmtPolicy_result))

        # esxi_memory = "{:.0f}".format(float((summary.runtime.host.summary.hardware.memorySize) / 1024 / 1024 / 1024))
        esxi_memory = "%.0f" % (float(summary.runtime.host.summary.hardware.memorySize) / 1024 / 1024 / 1024)
        esxi_memory_used = "{:.0f}".format(float(summary.runtime.host.summary.quickStats.overallMemoryUsage) / 1024)
        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI Physical Memory", str(esxi_memory) + " GB", nav, nav))

        esxiAllocMEM = int(esxiinfo['totallocatedMEM'])
        esxiAllocMEM_fmt = "ESXI Total Allocated Memory to all VMs"
        esxiAllocMEM_result = "Pass" if (int(esxiAllocMEM) / 1024) <= (int(esxi_memory) * 0.9) else "Fail"
        print("{0:50} {1:<70} {2:30} {3:10}".format(esxiAllocMEM_fmt, str(int(esxiAllocMEM) / 1024) + " GB",
                                                    "<=" + str((int(esxi_memory) * 0.9)) + " [ 10% free for ESXI ]",
                                                    esxiAllocMEM_result))

        esxi_memory_free = float(esxi_memory) - float(esxi_memory_used)
        esxi_memory_reserved = "{:.0f}".format(float(esxi_memory) * 0.10)
        esxi_memory_reserved_result = "Pass" if float(esxi_memory_reserved) >= float(esxi_memory_free) else "Fail"
        # print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI Memory Reservation ",str(esxi_memory_used) + " GB (Usage)", str(esxi_memory_reserved) + " GB (10% Reserved)", esxi_memory_reserved_result))

        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI HA", tbd, dx_setting['esxi_ha'], "N/A"))
        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI DRS", tbd, dx_setting['esxi_drs'], "N/A"))

    # if (esxi_info_stat >= 2 ):
    #    print("")
    #    print("{0:140}".format('-' * 160))

    vm_name = summary.config.name
    vm_ip_addr = summary.guest.ipAddress
    print("")
    print(
        "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("SECTION - II : Delphix Engine = " + vm_name)
    print(
        "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("")
    vm_name_fmt = "[" + vm_name + "]" + " Total vCPUs"
    vm_min_cpu_result = "Pass" if summary.config.numCpu >= float(dx_setting['minimum_cpu']) else "Fail"
    print("{0:50} {1:<70} {2:30} {3:10}".format(vm_name_fmt, summary.config.numCpu, dx_setting['minimum_cpu'],
                                                vm_min_cpu_result))

    cpuMhz = summary.runtime.host.summary.hardware.cpuMhz
    numCpu = summary.config.numCpu
    vm_vcpu_cores = vm_hardware.numCoresPerSocket

    vmcpu_rec = cpuMhz * numCpu

    if vmcpures != "None":
        cpures, filler1 = vmcpures.split(" ")
        if int(cpures) >= int(vmcpu_rec):
            vmcpures_result = "Pass"
        else:
            vmcpures_result = "Fail"
    else:
        vmcpures_result = "Fail"

    vm_cpu_res_fmt = "[" + vm_name + "]" + " CPU Reservation"
    print("{0:50} {1:<70} {2:30} {3:10}".format(vm_cpu_res_fmt, vmcpures, str(vmcpu_rec) + " Mhz", vmcpures_result))

    vm_cpuhtsharing = vm.config.flags.htSharing
    vm_cpuhtsharing_fmt = "[" + vm_name + "]" + " HT Sharing"
    vm_cpuhtsharing_result = "Pass" if vm_cpuhtsharing == dx_setting['vm_htsharing'] else "Fail"
    print("{0:50} {1:<70} {2:30} {3:10}".format(vm_cpuhtsharing_fmt, vm_cpuhtsharing, dx_setting['vm_htsharing'],
                                                vm_cpuhtsharing_result))

    print("")

    vm_memory = "{:.0f}".format((float(summary.config.memorySizeMB) / 1024))
    vm_memory_fmt = "[" + vm_name + "]" + " Total Memory"
    vm_memory_result = "Pass" if float(summary.config.memorySizeMB / 1024) >= float(
        dx_setting['minimum_memory']) else "Fail"
    print("{0:50} {1:<70} {2:30} {3:10}".format(vm_memory_fmt, str(vm_memory) + " GB",
                                                ">=" + dx_setting['minimum_memory'] + " GB", vm_memory_result))

    vm_memres = "{:.0f}".format((float(summary.config.memoryReservation) / 1024))
    vm_memres = 0 if vmmemres == "None" else vmmemres.split(" ")[-1]
    if vmmemres == "None":
        vm_memres = 0
    else:
        vm_memres, filler1 = str(vmmemres).split(" ")
        if (filler1 == "MB"):
            vm_memres = "{:.1f}".format(float(vm_memres) / 1024)
            # vm_memres = int(vm_memres)/1024
    vm_memory_res_fmt = "[" + vm_name + "]" + " Memory Reservation"
    vm_memory_res_result = "Pass" if float(vm_memres) >= float(vm_memory) else "Fail"
    print("{0:50} {1:<70} {2:30} {3:10}".format(vm_memory_res_fmt, str(vm_memres) + " GB", str(vm_memory) + " GB",
                                                vm_memory_res_result))

    print("")

    vm_vnic_fmt = "[" + vm_name + "]" + " NIC"
    if len(network_list) > 0:
        for each_vnic in network_list:
            vnic_result = "Pass" if dx_setting['vnic'] in each_vnic.lower() else "Fail"
            print("{0:50} {1:70} {2:30} {3:10}".format(vm_vnic_fmt, each_vnic, dx_setting['vnic'], vnic_result))

    print("")

    vm_scsi_ctrl_fmt = "[" + vm_name + "]" + " SCSI Controllers Type"
    if len(scsi_contr_list) > 0:
        for each_scsi in scsi_contr_list:
            (ctrlName, ctrlType) = each_scsi.split("|")
            vm_scsi_ctrl_result = "Pass" if ctrlType.strip() == dx_setting['scsi_controller_type'] else "Fail"
            print("{0:50} {1:70} {2:30} {3:10}".format(vm_scsi_ctrl_fmt, each_scsi, dx_setting['scsi_controller_type'],
                                                       vm_scsi_ctrl_result))

    scsi_ctrl_dict = {}
    vmdk_dict = {}
    scsi_hdd_dict = {}
    scsi_hdd_cnt = {}
    scsi_hdd_cnt_base = {'SCSI controller 0': 0, 'SCSI controller 1': 0, 'SCSI controller 2': 0, 'SCSI controller 3': 0}
    for dev in vm.config.hardware.device:
      if isinstance(dev, vim.vm.device.VirtualLsiLogicController):
        scsi_ctrl_dict[dev.key] = dev.deviceInfo.label
      elif isinstance(dev, vim.vm.device.VirtualDisk):
        vmdk_dict[dev.deviceInfo.label] = dev.controllerKey
      else:
        continue

    #for key, value in sorted(vmdk_dict.iteritems()): #python 2.7
    for key, value in sorted(vmdk_dict.items()):
      scsi_hdd_dict.setdefault(value, []).append(key)

    for key in scsi_hdd_dict:
      scsi_hdd_cnt[scsi_ctrl_dict[key]] = len(scsi_hdd_dict[key])

    for scsi_ctrlr in scsi_hdd_cnt_base:
        if scsi_ctrlr not in scsi_hdd_cnt:
            scsi_hdd_cnt[scsi_ctrlr] = 0

    # Sort dict by controller name
    scsi_hdd_cnt = dict( sorted(scsi_hdd_cnt.items(), key=itemgetter(0),reverse=False))

    #controller0=4 controller1=0 controller2=0 controller3=0
    ctrl_string = ""
    for i in scsi_hdd_cnt:
      ctrl_string = (i.replace("SCSI ","")).replace(" ","") + "=" + str(scsi_hdd_cnt[i]) + " " + ctrl_string

    ctrl_string = ctrl_string.strip()
    ctrl_balanced = find_scsictrl_balanced(scsi_hdd_cnt)
    print (" ")

    f = open("logs/vm_stats.csv", "a")
    f.write("{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}\n".format(vm_name, numCpu, vm_vcpu_cores, vmcpures, 'yes' if vmcpures_result == "Pass" else "no", int(math.ceil(float(summary.config.memorySizeMB) / 1024)), int(math.ceil(float(vm_memres))), 'yes' if vm_memory_res_result == "Pass" else "no", vm_memory, vm_cpuhtsharing, 'yes' if vm_cpuhtsharing_result == "Pass" else "no", ctrl_string, 'yes' if ctrl_balanced == "Pass" else "no"))
    f.close()

    # Controller balance information
    vm_disk_ctrl_fmt = "[" + vm_name + "]" + " [<Controller>:<tot_disks>]"
    ctrl = {}
    ctrl0 = ctrl1 = ctrl2 = ctrl3 = 0
    for c in controller_units:
        (ctrl_no, unit) = c.split(":")
        ctrl[ctrl_no] = int(ctrl_no)
        if (int(ctrl_no) == 0):
            ctrl0 += 1
        elif (int(ctrl_no) == 1):
            ctrl1 += 1
        elif (int(ctrl_no) == 2):
            ctrl2 += 1
        elif (int(ctrl_no) == 3):
            ctrl3 += 1

    scsiCtrlCnt = "[ SCSI0:" + str(ctrl0) + " | SCSI1:" + str(ctrl1) + " | SCSI2:" + str(ctrl2) + " | SCSI3:" + str(ctrl3) + " ]"
    #ctrl_result = "Pass" if (0 in ctrl.values()) and (1 in ctrl.values()) and (2 in ctrl.values()) and (3 in ctrl.values()) else "Fail"
    ctrl_result = ctrl_balanced
    print("{0:50} {1:<70} {2:30} {3:10}".format(vm_disk_ctrl_fmt, scsiCtrlCnt, dx_setting['disk_controllers'], ctrl_result))


    # display disks properties
    # print("")
    vm_hdd_rec_res = ""
    hdd_labellist = []
    for hdd_label in hdd.keys():
        hdd_labellist.append(hdd_label)

    hdd_labellist.sort()
    for hdd_label in hdd_labellist:
        vm_hdd_fmt = "[" + vm_name + "] " + hdd_label + " (" + disk_type + ")"
        if hdd[hdd_label]['thickProvisioned'] == 'true':
            #vm_hdd_cur_value = "Thick Prov:" + "{0:5}".format(hdd[hdd_label]['thickProvisioned']) + "| Ctrl: " + hdd[hdd_label]['controller_unit'] + " | Size: " + str(hdd[hdd_label]['sizeGB']) + " GB"
            vm_hdd_cur_value = "Thick Provisioned" + "| Ctrl: " + hdd[hdd_label]['controller_unit'] + " | Size: " + str(hdd[hdd_label]['sizeGB']) + " GB"
        else:
            #vm_hdd_cur_value = "Thick Prov:" + "{0:5}".format(hdd[hdd_label]['thickProvisioned']) + "| Ctrl: " + hdd[hdd_label]['controller_unit'] + " | Size: " + str(hdd[hdd_label]['sizeGB']) + " GB"
            vm_hdd_cur_value = "Thin Provisioned " + "| Ctrl: " + hdd[hdd_label]['controller_unit'] + " | Size: " + str(hdd[hdd_label]['sizeGB']) + " GB"

        disk_provision_format = disk_type + '_disk_provision_format'
        disk_provision_type = disk_type + '_disk_provision_type'
        #vm_hdd_rec_value = dx_setting[disk_provision_type] + "," + dx_setting[disk_provision_format]
        vm_hdd_rec_value = dx_setting[disk_provision_type]

        if hdd[hdd_label]['thickProvisioned'] == 'true' and dx_setting[disk_provision_type] == 'Thick':
                vm_hdd_rec_res = 'Pass'
        else:
            vm_hdd_rec_res = 'Fail'

        print("{0:50} {1:70} {2:30} {3:10}".format(vm_hdd_fmt, vm_hdd_cur_value, vm_hdd_rec_value, vm_hdd_rec_res))

    print("")
    # PrintStoragePolicy(vm, content, vchtime, vm_name)
    #logger.info("myconfig:")
    #logger.info(myconfig)
    for dev in myconfig.hardware.device:
        # if not isinstance(dev, vim.vm.device.VirtualDisk) or not isinstance(dev.backing, vim.vm.device.VirtualFileBacking):
        if not isinstance(dev, vim.vm.device.VirtualDisk):
            continue  # If it isn't a file backing, then it likely isn't on a datastore we can reference
        ds = dev.backing.datastore
        logger.info("ds = \n {}".format(ds))
        logger.info("ds.info = \n {}".format(ds.info))
        if hasattr(ds.info, 'vmfs'):
            logger.info("Datastore Type : VMFS")
            naa = naa = [x.diskName for x in ds.info.vmfs.extent]
            host = vm.runtime.host
            storageDeviceInfo = host.configManager.storageSystem.storageDeviceInfo
            luns = storageDeviceInfo.multipathInfo.lun
            logger.info("============================================================")
            logger.info("ds.info.vmfs:")
            logger.info(ds.info.vmfs)
            logger.info("============================================================")
            logger.info("luns:")
            logger.info(luns)
            scsiLun = storageDeviceInfo.scsiLun
            logger.info("============================================================")
            logger.info("scsiLun:")
            logger.info(scsiLun)
            policies = [x.policy for x in luns if get_disk_lun(scsiLun, x.lun, naa)]
            logger.info("============================================================")
            logger.info("policies:")
            logger.info(policies)
            for policy in policies:
                # print(dev.deviceInfo.label)
                # print("Disk %s, policy %s" % (dev.backing.fileName, policy.policy))
                vm_storagepathpolicy_fmt = "[" + vm_name + "] " + "StoragePathPolicy" + "( HDD " + \
                                           (dev.deviceInfo.label).split(" ")[-1] + " )"
                vm_storagepathpolicy = policy.policy
                vm_storagepathpolicy_result = "Pass" if vm_storagepathpolicy == dx_setting[
                    'vm_storagepathpolicy'] else "Fail"
                vm_storagepathpolicy = policy.policy + " (Round Robin)" if policy.policy == "VMW_PSP_RR" else policy.policy
                print("{0:50} {1:<70} {2:30} {3:10}".format(vm_storagepathpolicy_fmt, vm_storagepathpolicy,
                                                            dx_setting['vm_storagepathpolicy'],
                                                            vm_storagepathpolicy_result))
        elif hasattr(ds.info, 'nas'):
            logger.info("Datastore Type : NFS")
            #naa = naa = [x.diskName for x in ds.info.vmfs.extent]
            naa = ds.info.nas.name
            host = vm.runtime.host
            storageDeviceInfo = host.configManager.storageSystem.storageDeviceInfo
            luns = storageDeviceInfo.multipathInfo.lun
            logger.info("============================================================")
            logger.info("ds.info.nas:")
            logger.info(ds.info.nas)
            logger.info("ds.info.nas.dynamicProperty:")
            logger.info(ds.info.nas.dynamicProperty)
            logger.info("============================================================")
            logger.info("luns:")
            logger.info(luns)
            scsiLun = storageDeviceInfo.scsiLun
            logger.info("============================================================")
            logger.info("scsiLun:")
            logger.info(scsiLun)
            #policies = [x.policy for x in luns if get_disk_lun(scsiLun, x.lun, naa)]
            policiesOuter = [x.policy for x in luns ]
            policies = [x.policy for x in policiesOuter]
            logger.info("============================================================")
            logger.info("policies:")
            logger.info(policies)
            # This is incomplete temporary solution
            vm_storagepathpolicy_fmt = "[" + vm_name + "] " + "StoragePathPolicy" + "( HDD " + (dev.deviceInfo.label).split(" ")[-1] + " )"
            vm_storagepathpolicy = str(policies).strip('[]').replace("'","")
            vm_storagepathpolicy_result = "Pass" if vm_storagepathpolicy == dx_setting['vm_storagepathpolicy'] else "Fail"
            vm_storagepathpolicy = "NAS - " + vm_storagepathpolicy + " (Round Robin)" if vm_storagepathpolicy == "VMW_PSP_RR" else "NAS - " + vm_storagepathpolicy
            print("{0:50} {1:<70} {2:30} {3:10}".format(vm_storagepathpolicy_fmt, vm_storagepathpolicy,
                                                        dx_setting['vm_storagepathpolicy'],
                                                        vm_storagepathpolicy_result))
        else:
            logger.info("Datastore Type : not VMFS/NAS")

def GetProperties(content, viewType, props, specType):
    # Build a view and get basic properties for all Virtual Machines
    recursive = True
    objView = content.viewManager.CreateContainerView(content.rootFolder, viewType, recursive)
    tSpec = vim.PropertyCollector.TraversalSpec(name='tSpecName', path='view', skip=False, type=vim.view.ContainerView)
    pSpec = vim.PropertyCollector.PropertySpec(all=False, pathSet=props, type=specType)
    oSpec = vim.PropertyCollector.ObjectSpec(obj=objView, selectSet=[tSpec], skip=False)
    pfSpec = vim.PropertyCollector.FilterSpec(objectSet=[oSpec], propSet=[pSpec], reportMissingObjectsInResults=False)
    retOptions = vim.PropertyCollector.RetrieveOptions()
    totalProps = []
    retProps = content.propertyCollector.RetrievePropertiesEx(specSet=[pfSpec], options=retOptions)
    totalProps += retProps.objects
    while retProps.token:
        retProps = content.propertyCollector.ContinueRetrievePropertiesEx(token=retProps.token)
        totalProps += retProps.objects
    objView.Destroy()
    # Turn the output in retProps into a usable dictionary of values
    gpOutput = []
    for eachProp in totalProps:
        propDic = {}
        for prop in eachProp.propSet:
            propDic[prop.name] = prop.val
        propDic['moref'] = eachProp.obj
        gpOutput.append(propDic)
    return gpOutput

def esxi_info(content, viewType, props, vchtime):
    object_view = content.viewManager.CreateContainerView(content.rootFolder, viewType, True)
    logger.info(content.rootFolder)
    logger.info(viewType)
    logger.debug(object_view)
    propESXIDic = {}

    totallocatedCPU = 0
    totallocatedMEM = 0
    retProps = GetProperties(content, [vim.VirtualMachine], ['name', 'runtime.powerState'], vim.VirtualMachine)
    logger.debug(retProps)
    for vm in retProps:
        retval = PrintAllocCPUMEM(vm['moref'], content, vchtime)
        totallocatedCPU = int(retval.split(':')[0]) + totallocatedCPU
        totallocatedMEM = int(retval.split(':')[1]) + totallocatedMEM
    for obj in object_view.view:
        # Turn the output in retProps into a usable dictionary of values
        propESXIDic = {
            'PowerMgmtPolicy': obj.hardware.cpuPowerManagementInfo.currentPolicy,
            'CPUhyperThreadingConfig': obj.config.hyperThread.config,
            'CPUhyperThreadingAvailable': obj.config.hyperThread.available,
            'CPUhyperThreadingActive': obj.config.hyperThread.active,
            'vMotionEnabled': obj.summary.config.vmotionEnabled,
            'totallocatedCPU': totallocatedCPU,
            'totallocatedMEM': totallocatedMEM,
            'Hardware': obj.hardware.systemInfo.vendor + " " + obj.hardware.systemInfo.model,
            'esxi_cpus': obj.summary.hardware.numCpuPkgs,
            'esxi_cores': obj.summary.hardware.numCpuCores,
            'esxi_threads': obj.summary.hardware.numCpuThreads
        }
        logger.info("propESXIDic = {}".format(propESXIDic))
    object_view.Destroy()
    return propESXIDic

def PrintAllocCPUMEM(vm, content, vchtime):
    allocatedCPU = 0
    allocatedMEM = 0
    # print("-" * 70)
    # print("Name:                    {0}".format(vm.name))
    # print("CPUs:                    {0}".format(vm.config.hardware.numCPU))
    # print("MemoryMB:                {0}".format(vm.config.hardware.memoryMB))
    # print("Guest PowerState:        {0}".format(vm.guest.guestState))
    # print("Guest PowerState:        {0}".format(vm.summary.runtime.powerState))
    # if vm.guest.guestState == "running" :
    if vm.summary.runtime.powerState == "poweredOn":
        allocatedCPU = allocatedCPU + vm.config.hardware.numCPU
        allocatedMEM = allocatedMEM + vm.config.hardware.memoryMB
        return str(allocatedCPU) + ":" + str(allocatedMEM)
    else:
        return "0:0"

def debug_log(args,str):
    mystr = repr(str)
    #if args.debug:
    f = open("logs/chk_esxi_settings_debug.txt", "a")
    f.write(mystr)
    f.write("\n")
    f.close()
    # print (mystr)

def delete_file(filename):
    if path.exists(filename):
        print("Deleting existing file {}".format(filename))
        os.remove(filename)
    else:
        print("File {} does not exists. skipping...".format(filename))

def set_log_level_from_verbose(args):

    if not args.verbose:
        console_handler.setLevel('ERROR')
    elif args.verbose == 1:
        console_handler.setLevel('WARNING')
    elif args.verbose == 2:
        console_handler.setLevel('INFO')
    elif args.verbose >= 3:
        console_handler.setLevel('DEBUG')
    else:
        logger.critical("UNEXPLAINED NEGATIVE COUNT!")

def main():
    global disk_type
    global esxi_version
    global esxi_build
    global esxi_info_stat

    print("Script Version : 3.0.0")
    logger.info("Script Version : 3.0.0")
    e = None
    
    try:
        args = parser.parse_args()
    except Exception as e:
        logger.error("Could not read arguments :")
        logger.error(str(e))
        print ("Could not read arguments :")
        print(str(e))
        return -1

    #set_log_level_from_verbose(args)
    
    try:
        #vmnames = args.vm
        vmnames = args.vm.split(",")
        si = None
        disk_types = ['ssd', 'non_ssd']

        if args.disk_type.lower() not in disk_types:
            print ('Disk Type (',args.disk_type.lower(),') not valid!.', 'Valid options are : ssd OR non-ssd')
            logger.error("Disk Type ( {} ) not valid!. Valid options are : ssd OR non-ssd".format(args.disk_type.lower()))
            return -1
        else:
            disk_type = args.disk_type.lower()

        logger.info('vmnames : {}'.format(vmnames))
        logger.info("disk_type : {}".format(disk_type))

        if args.password:
            password = args.password
        else:
            try:
                password = getpass.getpass(prompt="Enter password for host {} and user {}: ".format(args.host, args.user))
            except Exception as e:
                print ("Could not read password")
                logger.error("Could not read password")
                print(str(e))
                return -1

        try:
            #logger.info("cert_check_skip : {}".format(args.cert_check_skip))
            if args.cert_check_skip:
                context = ssl._create_unverified_context()
                logger.info("context :")
                logger.info(context)
                si = SmartConnect(host=args.host, user=args.user, pwd=password, port=int(args.port), sslContext=context)

            else:
                si = SmartConnect(host=args.host, user=args.user, pwd=password, port=int(args.port))

            logger.info("si:")
            logger.info(si)
            si_attrs = si.__dict__
            logger.info("si_attrs: {}".format(si_attrs))
        except IOError as e:
            print("IOError.")
            print(str(e))
            logger.error("IOError.")
            logger.error(str(e))
            return -1
        except Exception as e:
            e = sys.exc_info()
            print(str(e))
            print("Other Exceptions:")
            logger.error(str(e))
            return -1

        if not si:
            print('Could not connect to the specified host using specified username and password')
            logger.error('Could not connect to the specified host using specified username and password')
            return -1
        else:
            print("Connected.")
            logger.info("Connected.")

        atexit.register(Disconnect, si)
        content = si.RetrieveContent()
        logger.info("content: {} \n".format(content))

        # Get vCenter date and time for use as baseline when querying for counters
        vchtime = si.CurrentTime()
        logger.info("vchtime: {}".format(vchtime))

        retESXIProps = esxi_info(content, [vim.HostSystem], ['hyperthreading'], vchtime)
        logger.debug("retESXIProps: {}".format(retESXIProps))

        #esx_global.csv
        esxi_info_stat = 0
        esxi_version   = content.about.version
        esxi_build     = content.about.build
        esxi_update    = "."
        esxi_ht_bp     = "False"

        f = open("logs/esx_global.csv", "a")
        f.write("{}, {}, {}, {}, {}, {}, {}, {}, {}\n".format(esxi_version,esxi_build,esxi_update,retESXIProps['esxi_cpus'],retESXIProps['esxi_cores'],retESXIProps['esxi_threads'],retESXIProps['CPUhyperThreadingActive'],retESXIProps['CPUhyperThreadingConfig'],esxi_ht_bp))
        f.close()

        retProps = GetProperties(content, [vim.VirtualMachine], ['name', 'runtime.powerState'], vim.VirtualMachine)
        logger.debug("retProps: {}".format(retProps))

        # Find VM supplied as arg and use Managed Object Reference (moref) for the PrintVmInfo
        vmcount = 0
        allvmlist = []
        for vm in retProps:
            # retval = PrintVmInfotmp(vm['moref'], content, vchtime)
            # print(retval)
            # print("Total CPU Allocated : {0} , Memory Allocated : {1}".format(allocatedCPU, allocatedMEM))
            allvmlist.append(vm['name'])
            if (vm['name'] in vmnames) and (vm['runtime.powerState'] == "poweredOn"):
                logger.info ("VM {} found in {} and powered on".format(vm['name'],args.host ))
                esxi_info_stat += 1
                PrintVmInfo(args, vm['moref'], content, vchtime, retESXIProps)
                vmcount = vmcount + 1
                
            elif (vm['name'] in vmnames) and (vm['runtime.powerState'] != "poweredOn"):
                print('ERROR: Problem connecting to Virtual Machine. {} is likely powered off or suspended'.format(vm['name']))
                logger.error('ERROR: Problem connecting to Virtual Machine. {} is likely powered off or suspended'.format(vm['name']))
                vmcount = vmcount + 1
                logger ("VM {} found in {} and powered off".format(vm['name'],args.host ))
                return -1
        
        allvmlist_lower = map(lambda x:x.lower(),allvmlist)
        for currvm in vmnames:
            if currvm.lower() not in allvmlist_lower:
                logger.error('vm : {} not found on vmware host {}'.format(currvm,args.host))
                print('vm : {} not found on vmware host {}'.format(currvm,args.host))
                return -1
        Disconnect
        print(' ')
        print('Note : Please send following 3 files generated in current folder to delphix professional services team')
        print('       1) logs/esx_global.csv' )
        print('       2) logs/vm_stats.csv' )
        print('       3) logs/chk_esxi_settings.txt' )
        print(' ')
        log_file_handler.close()
        if not args.debug:
            if path.exists("logs/chk_esxi_settings_debug.log"): os.remove("logs/chk_esxi_settings_debug.log") 

    except vmodl.MethodFault as e:
        print('Caught vmodl fault: ' + e.msg)
        logger.error("Caught vmodl fault : {}".format(e.msg))
        return -1
    except Exception as e:
        print('Caught exception: ' + str(e))
        logger.error("Caught exception: {}".format(e))
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
