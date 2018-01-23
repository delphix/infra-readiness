#!/usr/bin/env python

"""
#
# Copyright (c) 2017, 2018 by Delphix. All rights reserved.
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
# Author       : Ajay Thotangare / Vikram Kulkarni
# Created      : 10/17/2017 (v1.0.0)
#

Code    : chk_esxi_settings.py
Syntax  :
Usage   : chk_esxi_settings.py [-h] -s HOST [-o PORT] -u USER [-p PASSWORD] -e VM [-t DISK_TYPE] [-c]

Process args for retrieving all the Virtual Machines

optional arguments:
  -h, --help                           show this help message and exit
  -s HOST, --host HOST                 Remote host to connect to
  -o PORT, --port PORT                 Port to connect on
  -u USER, --user USER                 User name to use when connecting to host
  -p PASSWORD, --password PASSWORD     Password to use when connecting to host
  -e VM, --vm VM                       One or more Virtual Machines to report on
  -c, --cert_check_skip                skip ssl certificate check
  -t DISK_TYPE, --disk_type DISK_TYPE  Disk Storage Type (non_ssd (default) | ssd

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

from __future__ import print_function
from pyvim.connect import SmartConnect, Disconnect
from pyVmomi import vmodl, vim
from datetime import timedelta, datetime
from collections import defaultdict
#from ConfigParser import SafeConfigParser

import re
import argparse
import atexit
import getpass
import json
import ssl
import os
import json


def GetArgs():
    """
    Supports the command-line arguments listed below.
    """
    global args
    parser = argparse.ArgumentParser(description='Process args for retrieving all the Virtual Machines')
    parser.add_argument('-s', '--host', required=True, action='store', help='Remote host to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store', help='Port to connect on')
    parser.add_argument('-u', '--user', required=True, action='store', help='User name to use when connecting to host')
    parser.add_argument('-p', '--password', required=False, action='store',
                        help='Password to use when connecting to host')
    parser.add_argument('-e', '--vm', required=True, action='store', help='One or more Virtual Machines to report on')
    parser.add_argument('-c', '--cert_check_skip', default=True, required=False, action='store_true', help='skip ssl certificate check')
    parser.add_argument('-t', '--disk_type', default='non_ssd', action='store', help='Disk Storage Type (non_ssd (default) | ssd')
    args = parser.parse_args()
    return args


def GetParserInfo():
    dx_setting = {}
    #parser = SafeConfigParser()
    #parser.read("delphix_recommended.ini")
    #section_name = "dx_settings"
   
    #for name, value in parser.items(section_name):
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
    dx_setting['disk_controllers']  = 'Distribute VMDKs'
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

def PrintVmInfo(vm, content, vchtime, esxiinfo):

    dx_setting = GetParserInfo()

    tbd = "[ Verify Manually ]"
    nav = "N/A"
    sep = "="

    summary = vm.summary

    disk_list = []
    network_list = []
    scsi_contr_list = []

    dict_tree = lambda: defaultdict(dict_tree)
    vm_info = dict_tree()
    hdd = dict_tree()
    controller_units = []

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

    vm_hardware = vm.config.hardware


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
            vm_info['disks'][each_vm_hardware.key]['capacity'] = each_vm_hardware.capacityInKB/1024/1024
            vm_info['disks'][each_vm_hardware.key]['thinProvisioned'] = each_vm_hardware.backing.thinProvisioned
            vm_info['disks'][each_vm_hardware.key]['fileName'] = each_vm_hardware.backing.fileName

            thickProvisioned = ""
            eagerZero = ""

            if ( each_vm_hardware.backing.thinProvisioned is False):
                thickProvisioned = 'true'
                if ( each_vm_hardware.backing.eagerlyScrub is True):
                    eagerZero = 'true'
                else:
                    eagerZero = 'true'
            else:
                thickProvisioned = 'false'
                eagerZero = 'NA'

            hdd[each_vm_hardware.deviceInfo.label]['eagerZero'] = eagerZero
            hdd[each_vm_hardware.deviceInfo.label]['thickProvisioned'] = thickProvisioned
            hdd[each_vm_hardware.deviceInfo.label]['controller_unit'] = str(vm_info['disks'][each_vm_hardware.key]['busNumber']) + ':' + str(each_vm_hardware.unitNumber)
            controller_units.append(str(vm_info['disks'][each_vm_hardware.key]['busNumber']) + ':' + str(each_vm_hardware.unitNumber))

            hdd[each_vm_hardware.deviceInfo.label]['controller'] = str(vm_info['disks'][each_vm_hardware.key]['busNumber'])

            hdd[each_vm_hardware.deviceInfo.label]['sizeGB'] = each_vm_hardware.capacityInKB / 1024 / 1024

            disk_list.append('{} | {:.1f}GB | Thin: {} | {} | Controller: {}:{}'.format(each_vm_hardware.deviceInfo.label,
                                                         each_vm_hardware.capacityInKB/1024/1024,
                                                         each_vm_hardware.backing.thinProvisioned,
                                                         each_vm_hardware.backing.fileName,
                                                         vm_info['disks'][each_vm_hardware.key]['busNumber'],
                                                         each_vm_hardware.unitNumber))
        elif (each_vm_hardware.key >= 4000) and (each_vm_hardware.key < 5000):            
            device_name = type(each_vm_hardware).__name__.split(".")[-1]
            #network_list.append('{} | {} | {}'.format(each_vm_hardware.deviceInfo.label, each_vm_hardware.deviceInfo.summary, device_name))
            network_list.append('{} | {} | {}'.format(each_vm_hardware.deviceInfo.label, each_vm_hardware.macAddress, device_name))

    if ( esxi_info_stat == 1 ):
        print("")
        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("SECTION - I : ESXi Host = " + summary.runtime.host.name)
        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("")
        print("{0:50} {1:70} {2:30} {3:10}".format("Settings/Parameters/Version","Current Value", "Recommended Value", "Result"))
        print("{0:50} {1:70} {2:30} {3:10}".format(sep * 50, sep * 70, sep * 30, sep * 10))
        print("{0:50} {1:70} {2:30} {3:10}".format("ESXI Hostname",summary.runtime.host.name + '(' + args.host + ')', nav, nav))

        esxi_version_result = "Pass" if esxi_version >= dx_setting['esxi_version'] else "Fail"
        print("{0:50} {1:70} {2:30} {3:10}".format("ESXI Version",esxi_version, 'ESXi ' + dx_setting['esxi_version'] + ' and Higher', esxi_version_result))

        cpu_type = re.sub('\s+', ' ',summary.runtime.host.summary.hardware.cpuModel)
        print("{0:50} {1:70} {2:30} {3:10}".format("ESXI CPU Type", cpu_type, nav, nav))
        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI CPU Sockets", summary.runtime.host.summary.hardware.numCpuPkgs, nav, nav))
        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI Cores Per Socket", (summary.runtime.host.summary.hardware.numCpuCores / summary.runtime.host.summary.hardware.numCpuPkgs), nav, nav))
        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXi Total CPU", summary.runtime.host.summary.hardware.numCpuCores, nav, nav))
        #print("{0:50} {1:70} {2:30} {3:10}".format("ESXI Hyperthreading Active",tbd, dx_setting['hyperthreading'], nav))

        esxiAllocCPU = int(esxiinfo['totallocatedCPU'])
        esxiAllocCPU_fmt = "ESXI Total Allocated CPU"
        esxiAllocCPU_result = "Pass" if (int(summary.runtime.host.summary.hardware.numCpuCores) - int(esxiAllocCPU)) >= 4 else "Fail"
        print("{0:50} {1:<70} {2:30} {3:10}".format(esxiAllocCPU_fmt, esxiAllocCPU, "Atleast 4 ESX CPU free" ,esxiAllocCPU_result))

        esxiHTConfig = str(esxiinfo['CPUhyperThreadingConfig'])
        esxiHTConfig_fmt = "ESXI Hyperthreading Enabled"
        esxiHTConfig_result = "Pass" if esxiHTConfig.lower() == dx_setting['esxi_hyperthreading'].lower() else "Fail"
        print("{0:50} {1:<70} {2:30} {3:10}".format(esxiHTConfig_fmt, esxiHTConfig, dx_setting['esxi_hyperthreading'] ,esxiHTConfig_result))

        esxiPowerMgmtPolicy = esxiinfo['PowerMgmtPolicy']
        esxiPowerMgmtPolicy_fmt = "ESXi BIOS Power Management"
        esxiPowerMgmtPolicy_result = "Pass" if esxiPowerMgmtPolicy == dx_setting['esxi_powermgmt'] else "Fail"
        print("{0:50} {1:<70} {2:30} {3:10}".format(esxiPowerMgmtPolicy_fmt, esxiPowerMgmtPolicy, dx_setting['esxi_powermgmt'] ,esxiPowerMgmtPolicy_result))

        #esxi_memory = "{:.0f}".format(float((summary.runtime.host.summary.hardware.memorySize) / 1024 / 1024 / 1024))
        esxi_memory = "%.0f" % (float(summary.runtime.host.summary.hardware.memorySize)/1024 / 1024 / 1024)
        esxi_memory_used = "{:.0f}".format(float(summary.runtime.host.summary.quickStats.overallMemoryUsage) / 1024)
        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI Physical Memory",str(esxi_memory) + " GB", nav, nav))

        esxiAllocMEM = int(esxiinfo['totallocatedMEM'])
        esxiAllocMEM_fmt = "ESXI Total Allocated Memory to all VMs"
        esxiAllocMEM_result = "Pass" if (int(esxiAllocMEM)/1024) <= (int(esxi_memory) * 0.9 ) else "Fail"
        print("{0:50} {1:<70} {2:30} {3:10}".format(esxiAllocMEM_fmt, str(int(esxiAllocMEM)/1024) + " GB", "<=" + str((int(esxi_memory) * 0.9 )) + " [ 10% free for ESXI ]" ,esxiAllocMEM_result))

        esxi_memory_free = float(esxi_memory) - float(esxi_memory_used)
        esxi_memory_reserved = "{:.0f}".format(float(esxi_memory) * 0.10)
        esxi_memory_reserved_result = "Pass" if esxi_memory_reserved >= float(esxi_memory_free) else "Fail"
        #print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI Memory Reservation ",str(esxi_memory_used) + " GB (Usage)", str(esxi_memory_reserved) + " GB (10% Reserved)", esxi_memory_reserved_result))

        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI HA",tbd, dx_setting['esxi_ha'],"N/A" ))
        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI DRS",tbd, dx_setting['esxi_drs'],"N/A"))

    #if (esxi_info_stat >= 2 ):
    #    print("")
    #    print("{0:140}".format('-' * 160))

 
    vm_name = summary.config.name
    print("")
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("SECTION - II : Delphix Engine = " + vm_name)
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("")  
    vm_name_fmt = "[" + vm_name + "]" + " Total vCPUs"
    vm_min_cpu_result = "Pass" if summary.config.numCpu >= float(dx_setting['minimum_cpu']) else "Fail"
    print("{0:50} {1:<70} {2:30} {3:10}".format(vm_name_fmt,summary.config.numCpu, dx_setting['minimum_cpu'], vm_min_cpu_result))

    cpuMhz = summary.runtime.host.summary.hardware.cpuMhz
    numCpu = summary.config.numCpu

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
    print("{0:50} {1:<70} {2:30} {3:10}".format(vm_cpu_res_fmt,vmcpures, str(vmcpu_rec) + " Mhz" , vmcpures_result))

    vm_cpuhtsharing = vm.config.flags.htSharing
    vm_cpuhtsharing_fmt = "[" + vm_name + "]" + " HT Sharing"
    vm_cpuhtsharing_result = "Pass" if vm_cpuhtsharing == dx_setting['vm_htsharing'] else "Fail"
    print("{0:50} {1:<70} {2:30} {3:10}".format(vm_cpuhtsharing_fmt, vm_cpuhtsharing, dx_setting['vm_htsharing'] ,vm_cpuhtsharing_result))

    print("")

    vm_memory = "{:.0f}".format((float(summary.config.memorySizeMB) / 1024))
    vm_memory_fmt = "[" + vm_name + "]" + " Total Memory"
    vm_memory_result = "Pass" if float(summary.config.memorySizeMB/1024) >= float(dx_setting['minimum_memory']) else "Fail"
    print("{0:50} {1:<70} {2:30} {3:10}".format(vm_memory_fmt, str(vm_memory) + " GB", ">=" + dx_setting['minimum_memory'] + " GB",vm_memory_result))

    vm_memres = "{:.0f}".format((float(summary.config.memoryReservation) / 1024))
    vm_memres = 0 if vmmemres == "None" else vmmemres.split(" ")[-1]
    if vmmemres == "None":
        vm_memres = 0
    else:
        vm_memres,filler1 = str(vmmemres).split(" ")
        if (filler1 == "MB"):
            vm_memres = "{:.1f}".format(float(vm_memres)/1024)
            #vm_memres = int(vm_memres)/1024
    vm_memory_res_fmt = "[" + vm_name + "]" + " Memory Reservation"
    vm_memory_res_result = "Pass" if float(vm_memres) >= float(vm_memory) else "Fail"
    print("{0:50} {1:<70} {2:30} {3:10}".format(vm_memory_res_fmt, str(vm_memres) + " GB", str(vm_memory) + " GB", vm_memory_res_result ))
    
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
            print("{0:50} {1:70} {2:30} {3:10}".format(vm_scsi_ctrl_fmt, each_scsi, dx_setting['scsi_controller_type'], vm_scsi_ctrl_result))

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

    scsiCtrlCnt="[ SCSI0:" + str(ctrl0) + " | SCSI1:" + str(ctrl1) + " | SCSI2:" + str(ctrl2) + " | SCSI3:" + str(ctrl3) + " ]"
    ctrl_result =  "Pass" if (0 in ctrl.values()) and (1 in ctrl.values()) and (2 in ctrl.values()) and (3 in ctrl.values())  else "Fail"
    print("{0:50} {1:<70} {2:30} {3:10}".format(vm_disk_ctrl_fmt, scsiCtrlCnt, dx_setting['disk_controllers'], ctrl_result))

    # display disks properties
    #print("")
    vm_hdd_rec_res = ""
    hdd_labellist = []
    for hdd_label in hdd.keys():
        hdd_labellist.append(hdd_label)
    
    hdd_labellist.sort()
    for hdd_label in hdd_labellist:
        vm_hdd_fmt = "[" + vm_name + "] " + hdd_label + " (" + disk_type + ")"
        vm_hdd_cur_value = "Thick Prov:" + "{0:5}".format(hdd[hdd_label]['thickProvisioned']) + " | EagerZero:" + "{0:5}".format(hdd[hdd_label]['eagerZero']) + "| Ctrl: " \
                + hdd[hdd_label]['controller_unit'] + " | Size: " + str(hdd[hdd_label]['sizeGB']) + " GB"

        disk_provision_format = disk_type + '_disk_provision_format'
        disk_provision_type = disk_type + '_disk_provision_type'
        vm_hdd_rec_value = dx_setting[disk_provision_type] + "," + dx_setting[disk_provision_format]

        if hdd[hdd_label]['thickProvisioned'] == 'true' and dx_setting[disk_provision_type] == 'Thick':
            if dx_setting[disk_provision_format] == 'Eager-Zero' and hdd[hdd_label]['eagerZero'] == 'true':
                vm_hdd_rec_res = 'Pass'
            if dx_setting[disk_provision_format] == 'Lazy-Zero' and hdd[hdd_label]['eagerZero'] == 'false':
                vm_hdd_rec_res = 'Pass'
        else:
            vm_hdd_rec_res = 'Fail'

        print("{0:50} {1:70} {2:30} {3:10}".format(vm_hdd_fmt, vm_hdd_cur_value, vm_hdd_rec_value,vm_hdd_rec_res))
    
    print("")    
    #PrintStoragePolicy(vm, content, vchtime, vm_name)
    myconfig = vm.config
    for dev in myconfig.hardware.device:
        #if not isinstance(dev, vim.vm.device.VirtualDisk) or not isinstance(dev.backing, vim.vm.device.VirtualFileBacking):
        if not isinstance(dev, vim.vm.device.VirtualDisk):
            continue # If it isn't a file backing, then it likely isn't on a datastore we can reference
        ds = dev.backing.datastore
        naa = naa = [x.diskName for x in ds.info.vmfs.extent]
        host = vm.runtime.host
        storageDeviceInfo = host.configManager.storageSystem.storageDeviceInfo
        luns = storageDeviceInfo.multipathInfo.lun
        scsiLun = storageDeviceInfo.scsiLun
        policies = [x.policy for x in luns if get_disk_lun(scsiLun, x.lun, naa)]
        for policy in policies:
            #print(dev.deviceInfo.label)
            #print("Disk %s, policy %s" % (dev.backing.fileName, policy.policy))
            vm_storagepathpolicy_fmt = "[" + vm_name + "] " + "StoragePathPolicy" + "( HDD " + (dev.deviceInfo.label).split(" ")[-1] + " )"
            vm_storagepathpolicy =  policy.policy
            vm_storagepathpolicy_result = "Pass" if vm_storagepathpolicy == dx_setting['vm_storagepathpolicy'] else "Fail"
            vm_storagepathpolicy =  policy.policy + " (Round Robin)" if policy.policy == "VMW_PSP_RR" else policy.policy
            print("{0:50} {1:<70} {2:30} {3:10}".format(vm_storagepathpolicy_fmt, vm_storagepathpolicy, dx_setting['vm_storagepathpolicy'] ,vm_storagepathpolicy_result))
    print("")




def GetProperties(content, viewType, props, specType):
    # Build a view and get basic properties for all Virtual Machines
    objView = content.viewManager.CreateContainerView(content.rootFolder, viewType, True)
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

def esxi_info(content, viewType, props,vchtime):
    object_view = content.viewManager.CreateContainerView(content.rootFolder, viewType, True)
    propESXIDic = {}

    totallocatedCPU = 0
    totallocatedMEM = 0
    retProps = GetProperties(content, [vim.VirtualMachine], ['name', 'runtime.powerState'], vim.VirtualMachine)
    for vm in retProps:
        retval = PrintAllocCPUMEM(vm['moref'], content, vchtime)
        totallocatedCPU = int(retval.split(':')[0]) + totallocatedCPU
        totallocatedMEM = int(retval.split(':')[1]) + totallocatedMEM
    for obj in object_view.view:
        # Turn the output in retProps into a usable dictionary of values
        propESXIDic = { 'PowerMgmtPolicy' : obj.hardware.cpuPowerManagementInfo.currentPolicy,
                    'CPUhyperThreadingConfig' : obj.config.hyperThread.config,
                    'CPUhyperThreadingAvailable' : obj.config.hyperThread.available,
                    'CPUhyperThreadingActive' : obj.config.hyperThread.active,
                    'vMotionEnabled' : obj.summary.config.vmotionEnabled,
                    'totallocatedCPU' : totallocatedCPU,
                    'totallocatedMEM' : totallocatedMEM }
    object_view.Destroy()
    return propESXIDic

def PrintAllocCPUMEM(vm, content, vchtime):
        allocatedCPU = 0
        allocatedMEM = 0
        #print("-" * 70)
        #print("Name:                    {0}".format(vm.name))
        #print("CPUs:                    {0}".format(vm.config.hardware.numCPU))
        #print("MemoryMB:                {0}".format(vm.config.hardware.memoryMB))
        #print("Guest PowerState:        {0}".format(vm.guest.guestState))
        #print("Guest PowerState:        {0}".format(vm.summary.runtime.powerState))
        #if vm.guest.guestState == "running" :
        if vm.summary.runtime.powerState == "poweredOn" :
            allocatedCPU = allocatedCPU + vm.config.hardware.numCPU
            allocatedMEM = allocatedMEM + vm.config.hardware.memoryMB
            return str(allocatedCPU) + ":" + str(allocatedMEM)
        else :
            return "0:0"

def main():
    args = GetArgs()
    global disk_type

    try:
        vmnames = args.vm
        si = None

        disk_types = ['ssd', 'non_ssd']

        if args.disk_type.lower() not in disk_types:
            print('Disk Type not valid!', args.disk_type.lower(),'<<')
            return -1
        else:
            disk_type = args.disk_type.lower()

        if args.password:
            password = args.password
        else:
            password = getpass.getpass(prompt="Enter password for host {} and user {}: ".format(args.host, args.user))

        try:
            if args.cert_check_skip:
                context = ssl._create_unverified_context()
                si = SmartConnect(host=args.host,
                                  user=args.user,
                                  pwd=password,
                                  port=int(args.port),
                                  sslContext=context)
            else:
                si = SmartConnect(host=args.host,
                                  user=args.user,
                                  pwd=password,
                                  port=int(args.port))
        except IOError as e:
            pass
        if not si:
            print('Could not connect to the specified host using specified username and password')
            return -1

        atexit.register(Disconnect, si)
        content = si.RetrieveContent()
        # Get vCenter date and time for use as baseline when querying for counters
        vchtime = si.CurrentTime()

        global esxi_version
        global esxi_build
        global  esxi_info_stat
        esxi_version = content.about.version
        esxi_build = content.about.build
        esxi_info_stat = 0

        retESXIProps = esxi_info(content, [vim.HostSystem], ['hyperthreading'],vchtime)
        #print (retESXIProps)

        retProps = GetProperties(content, [vim.VirtualMachine], ['name', 'runtime.powerState'], vim.VirtualMachine)

        #Find VM supplied as arg and use Managed Object Reference (moref) for the PrintVmInfo
        for vm in retProps:
            #retval = PrintVmInfotmp(vm['moref'], content, vchtime)
            #print(retval)
            #print("Total CPU Allocated : {0} , Memory Allocated : {1}".format(allocatedCPU, allocatedMEM))
            if (vm['name'] in vmnames) and (vm['runtime.powerState'] == "poweredOn"):
                esxi_info_stat += 1
                PrintVmInfo(vm['moref'], content, vchtime,retESXIProps)
            elif vm['name'] in vmnames:
                print('ERROR: Problem connecting to Virtual Machine.  {} is likely powered off or suspended'.format(vm['name']))

    except vmodl.MethodFault as e:
        print('Caught vmodl fault : ' + e.msg)
        return -1
    except Exception as e:
        print('Caught exception : ' + str(e))
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
