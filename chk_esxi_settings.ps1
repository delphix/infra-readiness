#================================================================================
# File:		chk_esxi_settings.ps1
# Type:		powershell script
# Author:	Delphix Professional Services
# Date:		08/16/2017
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
#	Powershell script to enable or disable all vFile dSources and VDBs on a
#	specified Delphix virtualization engine.
#
#
# Command-line parameters:
#
#	$dlpx_eng_name(n)	IP hostname or address of the Delphix virtualization engine
#	$disktype(t)		Disk Type [ SSD | NONSSD ]
#	$odir(o)		    Custom output directory for files.
#	$debug(d)		    debugging info
#	$showhelp(h)		help
#
# Modifications:
#	Ajay Thotangare		08/16/17	1st Version	
#================================================================================
[CmdletBinding(SupportsShouldProcess=$true)]
Param(
    [parameter(Mandatory=$false)]
    [alias("v")]
    $dlpx_eng_name,

    [parameter(Mandatory=$false)]
    [alias("t")]
    $disktype,

    [parameter(Mandatory=$false)]
    [alias("o")]
    $outputdir,

    [parameter(Mandatory=$false)]
    [alias("s")]
    $esxihost,

    [parameter(Mandatory=$false)]
    [alias("u")]
    $esxuser,

    [parameter(Mandatory=$false)]
    [alias("p")]
    $esxpwd,

    [parameter(Mandatory=$false)]
    [alias("d")]
    [switch]$debug1,

    [parameter(Mandatory=$false)]
    [alias("h")]
    [switch]$showhelp
)

#Variables ...
#$global:esxihost = "192.168.116.195"
$global:PROCID = $pid
$global:OUTPUTFILE = "$env:temp/chk_esxi_settings.${PROCID}.out"
$nl = [Environment]::NewLine

$wpref = $WarningPreference
$WarningPreference ="SilentlyContinue"
disconnect-viserver $esxihost -confirm:$false > $null
Connect-VIServer $esxihost -User "${esxuser}" -Password "${esxpwd}" > $null
$WarningPreference = $wpref

if (!$outputdir) { $global:odir = "$env:temp/${PROCID}" } else { $global:odir = $outputdir }

if ( -Not (Test-Path ${odir})) {
	mkdir -p ${odir}
	if ( -Not (Test-Path ${odir})) {
		echo "Unable to create output directory ${odir}!"
		exit;
	}
}

# Help Menu
function usage {
	echo " "
	echo "./chk_esxi_settings.ps1 [ -n <VM name> ] [ -h ] [ -d ] [ -t ] [-o <output dir>]"
	echo "	-n <VM name>: Name of Delphix Engine VM"
	echo "	-d: Leave output files behind"
	echo "	-h: This help text"
	echo "	-t: Y|y|SSD|ssd|n|N [ If disk type is SSD, input Y or y or SSD or ssd. For non-ssd input N or n]"
	echo "	-o <output dir>: Where output files should be placed (default: /tmp/$$)"
	echo " "
	echo "Examples"
	echo "========"
	echo "./chk_esxi_settings.ps1 -n dlpxvm01 -t SSD"
	echo "./chk_esxi_settings.ps1 -n dlpxvm01 -t NONSSD"
	exit 1
}

if ($showhelp)
{
	usage
	exit 1
}

function cleanup () {
	if (!${debug})
	{
		rm -rf ${odir}
	}
}

if (Test-Path $OUTPUTFILE) {
  Clear-Content ${OUTPUTFILE}
}


if (!$dlpx_eng_name) {
	echo "VM List:" | Tee-Object -Append "${OUTPUTFILE}"
	#Start-Job -Name Job1 -ScriptBlock {(Get-VM | Select Name) }
	#Wait-Job -Name Job1
	Get-VM | Select Name 
    Start-Sleep -s 10
}


if (!$dlpx_eng_name) {
	do {
		$dlpx_eng_name = Read-Host "Enter name of delphix engine from the above list, 'quit' to exit > "
	} # End of 'Do'
	while (!$dlpx_eng_name)

	if ($dlpx_eng_name -eq "quit") 	{ exit 3 }
	else {
		echo "You entered: $dlpx_eng_name"
		echo $nl
	}
}


if (!$disktype)
{
	do {
		$disktype = Read-Host "Enter Disk Type ( SSD | NONSSD ), 'quit' to exit > " | Tee-Object -Append "${OUTPUTFILE}"
		if ($disktype -eq "quit") { 
			exit 3 
		}
		else {
			if ( $disktype -ne "SSD" -AND $disktype -ne "NONSSD" -AND $disktype -ne "ssd" -AND $disktype -ne "nonssd") {
				echo "Valid Options for disktype are :  (SSD | NONSSD) "
				$disktype = $null
			}
			else { 
				echo "You entered: $disktype"
				echo $nl
			}
		}
	} # End of 'Do'
	while (!$disktype)
}

$esxcli = Get-EsxCli -VMhost $esxihost

#VMIDS=`vim-cmd vmsvc/getallvms | sed -e '1d' -e 's/ \[.*$//' | awk '$1 ~ /^[0-9]+$/ {print $1}'`
$VMIDS = Get-VM | Select ID | ft -hidetableheaders




if((Get-VM "${dlpx_eng_name}").PowerState -ne "PoweredOn")
{
	echo " "| Tee-Object -Append "${OUTPUTFILE}"
	echo "VM ${dlpx_eng_name} is not currently powered on"| Tee-Object -Append "${OUTPUTFILE}"
	echo "Please power on VM ${dlpx_eng_name} and try again"| Tee-Object -Append "${OUTPUTFILE}"
	echo " "| Tee-Object -Append "${OUTPUTFILE}"
	exit 1
}

# Get Host and Version information
$esxcli.system.version.get() | Out-File "${odir}/esxi_system_version.txt"
$esx_version = Get-Content ${odir}/esxi_system_version.txt|select-string "Version"|%{$_.Line.Split(":")[1]}
$esx_build = Get-Content ${odir}/esxi_system_version.txt|select-string "Build"|%{$_.Line.Split(":")[1]}
$esx_update = Get-Content ${odir}/esxi_system_version.txt|select-string "Update"|%{$_.Line.Split(":")[1]}
$esx_patch = Get-Content ${odir}/esxi_system_version.txt|select-string "Patch"|%{$_.Line.Split(":")[1]}
if($esx_patch) { $esx_patch = "/" + $esx_patch }
$esx_hostname = $esxcli.system.hostname.get().FullyQualifiedDomainName

echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Setting/Parameters/Version" ,"Current Value", "Recommended Value", "Result") | Tee-Object -Append "${OUTPUTFILE}"
echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "==========================","===============","==================","=======") | Tee-Object -Append "${OUTPUTFILE}"
echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi HostName","$esx_hostname","N/A","N/A") | Tee-Object -Append "${OUTPUTFILE}"

if ( $esx_version.Split('.')[0] -ge 5 ) {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi Version", $esx_version.trim(), "ESXi 5.0 and Higher", "Pass") | Tee-Object -Append "${OUTPUTFILE}"
} else {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi Version", $esx_version.trim(), "ESXi 5.0 and Higher", "Fail") | Tee-Object -Append "${OUTPUTFILE}"
}

##### Get CPU Information
####$esxcli.hardware.cpu.global.get() | Out-File "${odir}/esxi_hardware_cpu_global.txt"
####$esx_cpu_packages = Get-Content ${odir}/esxi_hardware_cpu_global.txt|select-string "CPUPackages"|%{$_.Line.Split(":")[1]}
#####$esx_cpu_threads = Get-Content ${odir}/esxi_hardware_cpu_global.txt|select-string "CPUThreads"|%{$_.Line.Split(":")[1]}
####$esx_cpu_cores = Get-Content ${odir}/esxi_hardware_cpu_global.txt|select-string "CPUCores"|%{$_.Line.Split(":")[1]}
####$esx_total_cpu = $esx_cpu_cores
####$esx_hyperthreading_active = Get-Content ${odir}/esxi_hardware_cpu_global.txt|select-string "HyperthreadingActive"|%{$_.Line.Split(":")[1]}
####$esx_hyperthreading_supported = Get-Content ${odir}/esxi_hardware_cpu_global.txt|select-string "HyperthreadingSupported"|%{$_.Line.Split(":")[1]}
####$esx_hyperthreading_enabled = Get-Content ${odir}/esxi_hardware_cpu_global.txt|select-string "HyperthreadingEnabled"|%{$_.Line.Split(":")[1]}
####$server = get-VMHost $esxihost
####$cpu_type = $server.ExtensionData.summary.hardware.CPuModel

# Get CPU Information
$server = get-VMHost $esxihost
$esx_cpu_packages = $server.ExtensionData.Summary.Hardware.NumCpuPkgs
#$server.ExtensionData.Summary.Hardware.NumCpuCores
#$server.ExtensionData.Summary.Hardware.NumCpuCores
$esx_total_cpu = $server.NumCpu
$esx_hyperthreading_active = $server.ExtensionData.Config.HyperThread.Active
$esx_hyperthreading_supported = $server.ExtensionData.Config.HyperThread.Active
$esx_hyperthreading_enabled = $server.ExtensionData.Config.HyperThread.Active
$cpu_type = $server.ExtensionData.summary.hardware.CPuModel
$vmotion = $server.ExtensionData.Summary.Config.VmotionEnabled
echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi CPU Type", "$cpu_type", "N/A", "N/A") | Tee-Object -Append "${OUTPUTFILE}"
echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi CPU Sockets", $esx_cpu_packages, "N/A", "N/A") | Tee-Object -Append "${OUTPUTFILE}"
echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi Total CPU", $esx_total_cpu, "N/A", "N/A") | Tee-Object -Append "${OUTPUTFILE}"

# Get Allocated CPU Count
$allocated_cpus = 0
$vms = Get-view  -ViewType VirtualMachine
foreach ($vm in $vms) {
	if ($vm.Runtime.PowerState -eq "poweredon")
	{
		$allocated_cpus = $allocated_cpus + $vm.config.hardware.NumCPU
	}
}
$esx_cpu_cores_10pct = $esx_cpu_cores/10
if (( $esx_total_cpu - $esx_cpu_cores_10pct ) -ge  $allocated_cpus ) {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi Allocated CPU", "$allocated_cpus" ,"Keep 10% for O/S" ,"Pass") | Tee-Object -Append "${OUTPUTFILE}"
} else {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi Allocated CPU", "$allocated_cpus" ,"Keep 10% for O/S" ,"Fail") | Tee-Object -Append "${OUTPUTFILE}"
}


# Get Esx_hyperthreading_active
if ( $esx_hyperthreading_active = "true" ) {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi Hyperthreading Active", "$esx_hyperthreading_active" ,"false" ,"Fail") | Tee-Object -Append "${OUTPUTFILE}"
} else {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi Hyperthreading Active", "$esx_hyperthreading_active" ,"false" ,"Pass") | Tee-Object -Append "${OUTPUTFILE}"
}

# Get Nic List
$i=1
$niclist = $esxcli.network.nic.list()
forEach ($nic in $niclist) {
	$nicname = "ESXi NIC ( " + ${nic}.Name + " )"
	$nicstatus = ${nic}.LinkStatus + ",Spd=" + ${nic}.Speed + ",Dup=" + ${nic}.Duplex + ",MTU=" + ${nic}.MTU
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f $nicname, "$nicstatus" , "N/A", "N/A") | Tee-Object -Append "${OUTPUTFILE}"
	$i++
}


# Memory Information
#$esx_memory = [math]::Round($esxcli.hardware.memory.get().PhysicalMemory/ (1024*1024*1024),2)
$esx_memory = $server.MemoryTotalGB
echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi Physical Memory(GB)", $esx_memory, "N/A", "N/A") | Tee-Object -Append "${OUTPUTFILE}"

# Esx PowerPolicy
$esx_powerpolicy = (Get-VMHost | Sort | Select @{ N="CurrentPolicy"; E={$_.ExtensionData.config.PowerSystemInfo.CurrentPolicy.ShortName}})| ft -hidetableheaders
if ( ${esx_powerpolicy} = "static" ) {	
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi BIOS Power Management", "High Performance" ,"High Performance(static)", "Pass") | Tee-Object -Append "${OUTPUTFILE}"
} else {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi BIOS Power Management", "High Performance" ,"High Performance(static)", "Fail") | Tee-Object -Append "${OUTPUTFILE}"
}

# Esx StoragePath Policy
$esx_storagepathpolicy = ($esxcli.storage.nmp.satp.list()|where {$_.name -eq "VMW_SATP_SYMM"}).defaultpsp
if ( ${esx_storagepathpolicy} -eq "VMW_PSP_RR" ) {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi Storage Path Policy", "Round Robin", "Round Robin(VMW_PSP_RR)", "Pass") | Tee-Object -Append "${OUTPUTFILE}"
} else {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi Storage Path Policy", "Round Robin", "Round Robin(VMW_PSP_RR)", "Fail") | Tee-Object -Append "${OUTPUTFILE}"
}

echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi HA", "Manually Check from vCenter", "Enabled", "-") | Tee-Object -Append "${OUTPUTFILE}"
echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "ESXi DRA", "Manually Check from vCenter", "Disabled", "-") | Tee-Object -Append "${OUTPUTFILE}"


# VM Information
echo "$nl" | Tee-Object -Append "${OUTPUTFILE}"


# Get VM CPU, Socket Info
$vm = Get-VM ${dlpx_eng_name}
$numsockets = ($vm.ExtensionData.Config.Hardware.NumCPU/$vm.ExtensionData.Config.Hardware.NumCoresPerSocket)

echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) CPU Sockets", $numsockets, "N/A", "N/A") | Tee-Object -Append "${OUTPUTFILE}"

if ( $vm.ExtensionData.Config.Hardware.NumCoresPerSocket -eq 1 ) {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) CPU Cores/Socket", $vm.ExtensionData.Config.Hardware.NumCoresPerSocket, 1, "Pass") | Tee-Object -Append "${OUTPUTFILE}"
} else {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) CPU Cores/Socket", $vm.ExtensionData.Config.Hardware.NumCoresPerSocket, 1, "Fail") | Tee-Object -Append "${OUTPUTFILE}"
}

if ( $vm.ExtensionData.Config.Hardware.NumCPU -ge 8 ) {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) Total vCPU", $vm.ExtensionData.Config.Hardware.NumCPU, 8, "Pass") | Tee-Object -Append "${OUTPUTFILE}"
} else {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) Total vCPU", $vm.ExtensionData.Config.Hardware.NumCPU, 8, "Fail") | Tee-Object -Append "${OUTPUTFILE}"
}

if ( $vm.ExtensionData.ResourceConfig.CpuAllocation.Reservation -gt 0 ) {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) CPU Reservation", $vm.ExtensionData.ResourceConfig.CpuAllocation.Reservation, "All CPU Reservation", "Pass") | Tee-Object -Append "${OUTPUTFILE}"
} else {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) CPU Reservation", $vm.ExtensionData.ResourceConfig.CpuAllocation.Reservation, "All CPU Reservation", "Fail") | Tee-Object -Append "${OUTPUTFILE}"
}

$vmrc = Get-VMResourceConfiguration $dlpx_eng_name
if ( $vmrc.HTCoreSharing -eq "none" ) {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) HT Sharing", $vmrc.HTCoreSharing, "none", "Pass") | Tee-Object -Append "${OUTPUTFILE}"
} else {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) HT Sharing", $vmrc.HTCoreSharing, "none", "Fail") | Tee-Object -Append "${OUTPUTFILE}"
}

$vm_memoryGB = [math]::Round($vm.ExtensionData.Config.Hardware.MemoryMB/1024,0)
if ( $vm_memoryGB -ge 64 ) {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) Total Memory", $vm_memoryGB, ">=64 GB", "Pass") | Tee-Object -Append "${OUTPUTFILE}"
} else {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) Total Memory", $vm_memoryGB, ">=64 GB", "Fail") | Tee-Object -Append "${OUTPUTFILE}"
}

if ( $vm.ExtensionData.ResourceConfig.MemoryAllocation.Reservation -ge $vm.ExtensionData.Config.Hardware.MemoryMB ) {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) Memory Reservation", $vm.ExtensionData.ResourceConfig.MemoryAllocation.Reservation, ">=64 GB", "Pass") | Tee-Object -Append "${OUTPUTFILE}"
} else {
	echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) Memory Reservation", $vm.ExtensionData.ResourceConfig.MemoryAllocation.Reservation, ">=64 GB", "Fail") | Tee-Object -Append "${OUTPUTFILE}"
}

# VM Nic Information
$vmadaptors = Get-NetworkAdapter -vm ${dlpx_eng_name}
forEach ( $vmnic in $vmadaptors ) {
	$nicname= "Dlpx VM (" + $dlpx_eng_name + ") " + $vmnic.Name
	$nictype = $vmnic.NetworkName + " | Type : " + $vmnic.Type
	if ( $vmnic.Type -eq "vmxnet3" ) {
		echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "$nicname", "$nictype", "vmxnet3", "Pass") | Tee-Object -Append "${OUTPUTFILE}"
	} else {
		echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "$nicname", "$nictype", "vmxnet3", "Fail") | Tee-Object -Append "${OUTPUTFILE}"
	}
}

# VM Disk information
function guest_controllers()
{
	$vscsi_out = "${odir}/vscsi_out.txt"
	$FileContent = (Get-Vm "$dlpx_eng_name"| Get-HardDisk |
		Select @{N='VM';E={$_.Parent.Name}},Name,
		@{N='DevNode';E={'{0}:{1}' -f ((Get-ScsiController -HardDisk $_).ExtensionData.BusNumber),$_.ExtensionData.UnitNumber}}|select devnode| ft -hidetableheaders)| where {$_ -ne ""}
	$FileContent|out-file $vscsi_out
	( Get-Content $vscsi_out ) | Where { $_ } | Set-Content $vscsi_out
	$c0 = 0 ; $c1 = 0; $c2 = 0; $c3 = 0; $ce = 0;
	Get-Content $vscsi_out | foreach {
		$pos = $_.IndexOf(":")
		$leftPart = $_.Substring(0, $pos)
		$rightPart = $_.Substring($pos+1)
		if ( $leftPart -eq 0 ) { $c0++ }
		elseif ( $leftPart -eq 1 ) { $c1++ }
		elseif ( $leftPart -eq 2 ) { $c2++ }
		elseif ( $leftPart -eq 3 ) { $c3++ }
		else { $ce++ }
	}
	#echo "c0 = $c0 ; c1 = $c1 ; c2 = $c2 ; c3 = $c3 ; ce = $ce "

	if (( $c0 -gt 0 ) -And ( $c1 -gt 0 ) -And ( $c2 -gt 0 ) -And ( $c3 -gt 0 )) {
		echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) Disks/Controllers" ,"scsi0=$c0;scsi1=$c1;scsi2=$c2;scsi3=$c3", "Distribute VMDKs", "Pass") | Tee-Object -Append "${OUTPUTFILE}"
	} else {                                                                                                             
		echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) Disks/Controllers" ,"scsi0=$c0;scsi1=$c1;scsi2=$c2;scsi3=$c3", "Distribute VMDKs", "Fail") | Tee-Object -Append "${OUTPUTFILE}"
	}

	$c0=0
	$c1=0
	$c2=0
	$c3=0
}

$controllerList=Get-Vm "$dlpx_eng_name"| get-scsicontroller
forEach ($controllerTypeRec in $controllerList) {
	$controllerType = $controllerTypeRec.Type
    $controllerName = "SCSI controller " + $controllerTypeRec.ExtensionData.BusNumber + " | " + $controllerTypeRec.Type
 	if ( $controllerType -eq "VirtualLsiLogic") {
	    echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) SCSI Controllers Type" ,"$controllerName", "VirtualLsiLogic", "Pass") | Tee-Object -Append "${OUTPUTFILE}"
	} else {
        echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "Dlpx VM ($dlpx_eng_name) SCSI Controllers Type" ,"$controllerName", "VirtualLsiLogic", "Fail") | Tee-Object -Append "${OUTPUTFILE}"
    }
}
guest_controllers

$vmstoragedisks = Get-VM ${dlpx_eng_name}| Get-HardDisk
forEach ( $vmdisk in $vmstoragedisks ) {
    $vmdiskName="Dlpx VM (" + $dlpx_eng_name + ") " + $vmdisk.Name + " (" + $disktype + ")"
    if ( $vmdisk.StorageFormat -eq "Thick" ) {
        $vmdiskProp = "Thick Prov:true |EagerZero:false|SCSI:" + ( $vmdisk.ExtensionData.ControllerKey - 1000 ) + ":" + $vmdisk.ExtensionData.UnitNumber + "|Size:" + $vmdisk.CapacityGB + " GB"
    } elseif ( $vmdisk.StorageFormat -eq "EagerZeroedThick" ) {
        $vmdiskProp = "Thick Prov:true |EagerZero:true |SCSI:" + ( $vmdisk.ExtensionData.ControllerKey - 1000 ) + ":" + $vmdisk.ExtensionData.UnitNumber + "|Size:" + $vmdisk.CapacityGB + " GB"
    } elseif ( $vmdisk.StorageFormat -eq "Thin" ) {
        $vmdiskProp = "Thick Prov:false|EagerZero:N/A  |SCSI:" + ( $vmdisk.ExtensionData.ControllerKey - 1000 ) + ":" + $vmdisk.ExtensionData.UnitNumber + "|Size:" + $vmdisk.CapacityGB + " GB"
    }

    if ( $disktype -eq "SSD" ) { $Recommendation = "Thick" } else { $Recommendation = "EagerZeroedThick" }
    if ( $vmdisk.Name -eq "Hard disk 1" ) { 
        $Recommendation = "N/A"
        $status = "Pass"
    } else {
        if ( $vmdisk.StorageFormat -eq "$Recommendation" ) { 
            $status = "Pass"
        } else {
            $status = "Fail"
        }
    }
    if ( $disktype -eq "SSD" ) { 
        $Recommendation = "Thick Prov:true , EagerZero:false" 
    } else {
        $Recommendation = "Thick Prov:true , EagerZero:true" 
    }
    echo ("{0,-45} {1,-55} {2,-32} {3, -7}" -f "$vmdiskName", "$vmdiskProp", "$Recommendation", "$status") | Tee-Object -Append "${OUTPUTFILE}"
}

disconnect-viserver $esxihost -confirm:$false > $null
#Remove-Item ${odir}/*