#!/usr/bin/env python

"""

Code    : chk_esxi_settings.py
Syntax  :
Usage   : chk_esxi_settings.py [-h] -s HOST [-o PORT] -u USER [-p PASSWORD] -m VM
                            [-c] [-t DISK_TYPE]

Process args for retrieving all the Virtual Machines

optional arguments:
  -h, --help            show this help message and exit
  -s HOST, --host HOST  Remote host to connect to
  -o PORT, --port PORT  Port to connect on
  -u USER, --user USER  User name to use when connecting to host
  -p PASSWORD, --password PASSWORD
                        Password to use when connecting to host
  -m VM, --vm VM        On eor more Virtual Machines to report on
  -c, --cert_check_skip
                        skip ssl certificate check
  -t DISK_TYPE, --disk_type DISK_TYPE
                        Disk Storage Type (non_ssd (default) | ssd

Sample Output:

python chk_esxi_settings.py -s 192.168.1.76 -u root -p password -m illium1  -c

Settings/Parameters/Version                        Current Value                                                          Recommended Value              Result
================================================== ====================================================================== ============================== ==========
ESXI Hostname                                      optimus                                                                N/A                            N/A
ESXI Version                                       6.0.0                                                                  5.5                            Pass
ESXI CPU Type                                      Intel(R) Xeon(R) CPU X5690 @ 3.47GHz                                   N/A                            N/A
ESXI CPU Sockets                                   2                                                                      N/A                            N/A
ESXI Cores Per Socket                              6                                                                      N/A                            N/A
ESXI Hyperthreading Active                         TBD                                                                    false                          N/A
ESXI Physical Memory                               95 GB                                                                  N/A                            N/A
ESXI Memory Reservation                            76 GB (Usage)                                                          10 GB (10% Reserved)           Pass
ESXI HA                                            TBD                                                                    enabled                        TBD
ESXI DRS                                           TBD                                                                    disabled                       TBD

Delphix VM [illium1] Number of vCPUs               4                                                                      8                              Fail
Delphix VM [illium1] CPU Reservation               None                                                                   13828 Mhz                      Fail

Delphix VM [illium1] Memory                        24 GB                                                                  64 GB                          Fail
Delphix VM [illium1] Memory Reservation            0 GB                                                                   24 GB                          Fail

Delphix VM [illium1] Disk Controllers              ['0:0', '1:0', '2:0', '3:0', '0:1', '0:2']                             Distribute VMDKs               Pass
Delphix VM [illium1] SCSI Controllers              SCSI controller 0 | LSI Logic                                          LSI Logic                      Pass
Delphix VM [illium1] SCSI Controllers              SCSI controller 1 | LSI Logic                                          LSI Logic                      Pass
Delphix VM [illium1] SCSI Controllers              SCSI controller 2 | LSI Logic                                          LSI Logic                      Pass
Delphix VM [illium1] SCSI Controllers              SCSI controller 3 | LSI Logic                                          LSI Logic                      Pass

Delphix VM [illium1] NIC                           Network adapter 1 | VM Network | VirtualVmxnet3                        vmxnet3                        Pass
Delphix VM [illium1] NIC                           Network adapter 2 | VM Network | VirtualE1000                          vmxnet3                        Fail

Delphix VM [illium1] Hard disk 1                   Thick Prov:false, EagerZero:NA   , Ctrl: 0:0, Size: 300 GB             Thick,Eager-Zero               Fail
Delphix VM [illium1] Hard disk 3                   Thick Prov:false, EagerZero:NA   , Ctrl: 2:0, Size: 8 GB               Thick,Eager-Zero               Fail
Delphix VM [illium1] Hard disk 2                   Thick Prov:false, EagerZero:NA   , Ctrl: 1:0, Size: 8 GB               Thick,Eager-Zero               Fail
Delphix VM [illium1] Hard disk 5                   Thick Prov:false, EagerZero:NA   , Ctrl: 0:1, Size: 8 GB               Thick,Eager-Zero               Fail
Delphix VM [illium1] Hard disk 4                   Thick Prov:false, EagerZero:NA   , Ctrl: 3:0, Size: 8 GB               Thick,Eager-Zero               Fail
Delphix VM [illium1] Hard disk 6                   Thick Prov:true , EagerZero:true , Ctrl: 0:2, Size: 8 GB               Thick,Eager-Zero               Pass

Comments: The code is a fork from py-vminfo.py which can be downloaded from github.
          It was modified to fit Delphix Infrastructure checklist script.
"""

from __future__ import print_function
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vmodl, vim
from datetime import timedelta, datetime
from collections import defaultdict
from ConfigParser import SafeConfigParser

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
    parser = argparse.ArgumentParser(description='Process args for retrieving all the Virtual Machines')
    parser.add_argument('-s', '--host', required=True, action='store', help='Remote host to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store', help='Port to connect on')
    parser.add_argument('-u', '--user', required=True, action='store', help='User name to use when connecting to host')
    parser.add_argument('-p', '--password', required=False, action='store',
                        help='Password to use when connecting to host')
    parser.add_argument('-m', '--vm', required=True, action='store', help='On eor more Virtual Machines to report on')
    parser.add_argument('-c', '--cert_check_skip', required=False, action='store_true', help='skip ssl certificate check')
    parser.add_argument('-t', '--disk_type', default='non_ssd', action='store', help='Disk Storage Type (non_ssd (default) | ssd')
    args = parser.parse_args()
    return args


def GetParserInfo():
    parser = SafeConfigParser()
    parser.read("delphix_recommended.ini")
    section_name = "dx_settings"
    dx_setting = {}
    for name, value in parser.items(section_name):
       dx_setting[name] = value

    return (dx_setting)


def PrintVmInfo(vm, content, vchtime):

    dx_setting = GetParserInfo()

    tbd = "TBD"
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
            network_list.append('{} | {} | {}'.format(each_vm_hardware.deviceInfo.label,
                                                         each_vm_hardware.deviceInfo.summary,
                                                         device_name))

    if ( esxi_info_stat == 1 ):
        print("")
        print("{0:50} {1:70} {2:30} {3:10}".format("Settings/Parameters/Version","Current Value", "Recommended Value", "Result"))
        print("{0:50} {1:70} {2:30} {3:10}".format(sep * 50, sep * 70, sep * 30, sep * 10))
        print("{0:50} {1:70} {2:30} {3:10}".format("ESXI Hostname",summary.runtime.host.name, nav, nav))

        esxi_version_result = "Pass" if esxi_version >= dx_setting['esxi_version'] else "Fail"
        print("{0:50} {1:70} {2:30} {3:10}".format("ESXI Version",esxi_version, dx_setting['esxi_version'], esxi_version_result))

        cpu_type = re.sub('\s+', ' ',summary.runtime.host.summary.hardware.cpuModel)
        print("{0:50} {1:70} {2:30} {3:10}".format("ESXI CPU Type", cpu_type, nav, nav))
        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI CPU Sockets", summary.runtime.host.summary.hardware.numCpuPkgs, nav, nav))
        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI Cores Per Socket", (summary.runtime.host.summary.hardware.numCpuCores / summary.runtime.host.summary.hardware.numCpuPkgs), nav, nav))
        print("{0:50} {1:70} {2:30} {3:10}".format("ESXI Hyperthreading Active",tbd, dx_setting['hyperthreading'], nav))

        esxi_memory = "{:.0f}".format(float((summary.runtime.host.summary.hardware.memorySize) / 1024 / 1024 / 1024))
        esxi_memory_used = "{:.0f}".format(float(summary.runtime.host.summary.quickStats.overallMemoryUsage) / 1024)
        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI Physical Memory",str(esxi_memory) + " GB", nav, nav))

        esxi_memory_free = float(esxi_memory) - float(esxi_memory_used)

        esxi_memory_reserved = "{:.0f}".format(float(esxi_memory) * 0.10)

        esxi_memory_reserved_result = "Pass" if esxi_memory_reserved >= float(esxi_memory_free) else "Fail"

        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI Memory Reservation ",str(esxi_memory_used) + " GB (Usage)", str(esxi_memory_reserved) + " GB (10% Reserved)", esxi_memory_reserved_result))

        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI HA",tbd, dx_setting['esxi_ha'],tbd ))
        print("{0:50} {1:<70} {2:30} {3:10}".format("ESXI DRS",tbd, dx_setting['esxi_drs'],tbd))

    if (esxi_info_stat >= 2 ):
        print("")
        print("{0:140}".format('-' * 160))

    print("")
    vm_name = summary.config.name
    vm_name_fmt = "Delphix VM [" + vm_name + "]" + " Number of vCPUs"
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

    
    vm_cpu_res_fmt = "Delphix VM [" + vm_name + "]" + " CPU Reservation"
    print("{0:50} {1:<70} {2:30} {3:10}".format(vm_cpu_res_fmt,vmcpures, str(vmcpu_rec) + " Mhz" , vmcpures_result))
    print("")



    vm_memory = "{:.0f}".format((float(summary.config.memorySizeMB) / 1024))
    vm_memory_fmt = "Delphix VM [" + vm_name + "]" + " Memory"
    vm_memory_res_result = "Pass" if summary.config.numCpu >= float(dx_setting['minimum_cpu']) else "Fail"
    print("{0:50} {1:<70} {2:30} {3:10}".format(vm_memory_fmt, str(vm_memory) + " GB", dx_setting['minimum_memory'] + " GB",
                                                "Pass" if float(vm_memory) >= float(dx_setting['minimum_memory']) else "Fail"))

    vm_memory_res_fmt = "Delphix VM [" + vm_name + "]" + " Memory Reservation"
    vm_memory_res_result = "Pass" if summary.config.numCpu >= float(dx_setting['minimum_cpu']) else "Fail"

    vm_memres = 0 if vmmemres == "None" else vmmemres.split(" ")[-1]

    if vmmemres == "None":
        vm_memres = 0
    else:
        vm_memres,filler1 = str(vmmemres).split(" ")

        if (filler1 == "MB"):
            vm_memres = int(vm_memres)/1024

    print("{0:50} {1:<70} {2:30} {3:10}".format(vm_memory_res_fmt, str(vm_memres) + " GB", str(vm_memory) + " GB", "Pass" if float(vm_memres) >= float(vm_memory) else "Fail" ))

    print("")



    vm_disk_ctrl_fmt = "Delphix VM [" + vm_name + "]" + " Disk Controllers"

    ctrl = {}

    for c in controller_units:
        (ctrl_no, unit) = c.split(":")
        ctrl[ctrl_no] = int(ctrl_no)

    ctrl_result =  "Pass" if (0 in ctrl.values()) and (1 in ctrl.values()) and (2 in ctrl.values()) and (3 in ctrl.values())  else "Fail"
    print("{0:50} {1:<70} {2:30} {3:10}".format(vm_disk_ctrl_fmt, controller_units, dx_setting['disk_controllers'], ctrl_result))

    vm_scsi_ctrl_fmt = "Delphix VM [" + vm_name + "]" + " SCSI Controllers"

    if len(scsi_contr_list) > 0:
        for each_scsi in scsi_contr_list:
            print("{0:50} {1:70} {2:30} {3:10}".format(vm_scsi_ctrl_fmt, each_scsi, dx_setting['scsi_controller_type'], ctrl_result))

    

    print("")
    vm_vnic_fmt = "Delphix VM [" + vm_name + "]" + " NIC"
    if len(network_list) > 0:
        for each_vnic in network_list:
            vnic_result = "Pass" if dx_setting['vnic'] in each_vnic.lower() else "Fail"
            print("{0:50} {1:70} {2:30} {3:10}".format(vm_vnic_fmt, each_vnic, dx_setting['vnic'], vnic_result))

    # display disks properties
    print("")
    vm_hdd_rec_res = ""
    for hdd_label in hdd.keys():
        vm_hdd_fmt = "Delphix VM [" + vm_name + "] " + hdd_label
        vm_hdd_cur_value = "Thick Prov:" + "{0:5}".format(hdd[hdd_label]['thickProvisioned']) + ", EagerZero:" + "{0:5}".format(hdd[hdd_label]['eagerZero']) + ", Ctrl: " \
                + hdd[hdd_label]['controller_unit'] + ", Size: " + str(hdd[hdd_label]['sizeGB']) + " GB"

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

        retProps = GetProperties(content, [vim.VirtualMachine], ['name', 'runtime.powerState'], vim.VirtualMachine)

        #Find VM supplied as arg and use Managed Object Reference (moref) for the PrintVmInfo
        for vm in retProps:
            if (vm['name'] in vmnames) and (vm['runtime.powerState'] == "poweredOn"):
                esxi_info_stat += 1
                PrintVmInfo(vm['moref'], content, vchtime)
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
