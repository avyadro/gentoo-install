from __future__ import print_function
import subprocess
import argparse
import requests
import multiprocessing
from collections import OrderedDict
import pprint

class TMap(object):
	def __init__(self,key,value):
		 self.key=key
		 self.value=value
class Map(object):
	def __init__(self):        
			self.list = []
	def put(self,key,value):
			self.list.append(TMap(key,value))
	def get(self,key):
		for e in self.list:
			if e.key == key:
				return e                  
	def list(self):
		return self.list     

class List(object):
     def __init__(self):
         """
         """ 
         self.list = []  
     def put(self,key,value):
         self.list.append(TMap(key,value))
     def get(self,key):
         for e in self.list:
            if e.key == key:
              return e                  
     def list(self):
         return self.list
class TLV(object):
    def __init__(self,name,size,fs):
        self.name=name
        self.size=size
        self.fs=fs
        
class GentooInstall(object):

	def __init__(self):		 
		self.version = "1.0.0"
		self.dummy = True
		self.rootdir = "/mnt/gentoo"
		self.arch = "amd64"
		self.cpus = multiprocessing.cpu_count()
		self.repo="http://distfiles.gentoo.org/releases/"+self.arch+"/autobuilds/"
		self.url_stage3 = self.repo+"latest-stage3-"+self.arch+".txt"
		#################
		# Disk  		#
		#################
		self.disk="/dev/sda"
		self.p_efi=1
		self.p_boot=2
		self.p_lvm=3
		#################
		# Partition		#
		#################
		_partitions = List()
		_partitions.put('efi','1 129 set 1 boot on')
		_partitions.put('boot','129 1153')
		_partitions.put('lvm','1153 100% set 3 lvm on')
		self.partitions = _partitions.list
		##############
		# LVM Schema #
		##############
		# Volume group
		self.lvm_vg="gentoo"
		# Logical volume
		#self.lvms = List()
		self.lvms = Map()
		self.lvms.put('swap', TLV('swapfs','-L 8G','swap') )
		self.lvms.put('home', TLV('homefs','-L 8G','fs.ext4') )
		self.lvms.put('root', TLV('rootfs','-l 100%VG','fs.ext4') )
		
		
	def shell(self,cmd):
		print(cmd)
		if not self.dummy:
			subprocess.run(cmd, shell=True, executable='/bin/bash')

def preparing_disk_revert(option, opt, value, parser):
	print("=> Reverting preparing disk")
	print("=> Unmounting the root partition")
	e = gentoo.lvms.get('root')
	cmd = "umount /dev/"+gentoo.lvm_vg+"/"+e.value.name
	gentoo.shell(cmd)
	print("=> Removing the logical and group volumes")
	cmd = "vgremove -y "+gentoo.lvm_vg
	gentoo.shell(cmd)
	print("=> Removing the physical volume")
	cmd = "pvremove -y "+gentoo.disk+str(gentoo.p_lvm)
	gentoo.shell(cmd)

def preparing_disk(option, opt, value, parser):
	print("#######################")
	print("# Preparing the disks #")
	print("#######################")
	print("=> Creating new disklabel (partition table) GPT")
	cmd = "parted -s -a optimal "+gentoo.disk+" mklabel gpt"
	gentoo.shell(cmd)
	for e in gentoo.partitions:
		cmd = "parted -s -a optimal "+gentoo.disk+" mkpart "+e.key+" "+e.value
		gentoo.shell(cmd)
	print("=> Starting LVM monitoring")
	cmd = "/etc/init.d/lvm-monitoring start"
	gentoo.shell(cmd)
	cmd = "vgchange -an"
	gentoo.shell(cmd)

	print("=> Creating the physical volume")
	cmd = "pvcreate -y "+gentoo.disk+str(gentoo.p_lvm)
	gentoo.shell(cmd)
	print("=> Creating the volume group")
	cmd = "vgcreate -y "+gentoo.lvm_vg+" "+gentoo.disk+str(gentoo.p_lvm)
	gentoo.shell(cmd)
	cmd = "vgchange -ay"
	gentoo.shell(cmd)
	print("=> Creating the logical volumes")
	for e in gentoo.lvms.list:
		print("+ "+e.value.name)    
		cmd = "lvcreate -y "+e.value.size+" -n "+e.value.name+" "+gentoo.lvm_vg
		gentoo.shell(cmd)
	print("=> Creating the filesystems")
	print("** EFI filesystem")
	cmd = "mkfs.fat -F 32 "+gentoo.disk+str(gentoo.p_efi)
	gentoo.shell(cmd)
	print("** BOOT filesystem")
	cmd = "mkfs.ext2 -F "+gentoo.disk+str(gentoo.p_boot)
	gentoo.shell(cmd)
	for e in gentoo.lvms.list:
		print("** "+e.key.upper()+" filesystem")
		cmd = "mk"+e.value.fs+" -F /dev/"+gentoo.lvm_vg+"/"+e.value.name
		gentoo.shell(cmd)
		if e.value.fs == 'swap':
			print("** Activating SWAP partition")
			cmd = "swapon /dev/"+gentoo.lvm_vg+"/"+e.value.name
			gentoo.shell(cmd)
	print("=> Mounting the root partition")
	e = gentoo.lvms.get('root')
	cmd = "mount /dev/"+gentoo.lvm_vg+"/"+e.value.name+" /mnt/gentoo"
	gentoo.shell(cmd)
# Installing a stage tarball
def installing_stage(option, opt, value, parser):
	print("##############################")
	print("# Installing a stage tarball #")
	print("##############################")
	print("=> Setting the date and time")
	cmd="ntpd -q -g"
	gentoo.shell(cmd)	
	print("=> Downloading stage")
	response = requests.get(gentoo.url_stage3).text.splitlines()	
	cmd = "wget -P "+gentoo.rootdir+" -c "+gentoo.repo+response[-1].split(" ")[0]
	gentoo.shell(cmd)	
	print("=> Unpacking the stage tarball")
	cmd = "tar xpvf "+gentoo.rootdir+"/stage3-*.tar.xz --xattrs-include='*.*' --numeric-owner -C "+gentoo.rootdir
	gentoo.shell(cmd)

gentoo = GentooInstall()

from optparse import OptionParser


usage = "usage: %prog [options] arg"
parser = OptionParser(usage)
#parser.add_option("-f", "--file", dest="filename",
#					help="read data from FILENAME")
#parser.add_option("-v", "--verbose",
#					action="store_true", dest="verbose")
#parser.add_option("-q", "--quiet",
#					action="store_false", dest="verbose")
parser.add_option("-d", "--preparing-disk",
					help="make partitions according to schema.",
					action="callback",
					callback=preparing_disk)
parser.add_option("-D", "--preparing-disk-revert",
					help="revert partitions created.",
					action="callback",
					callback=preparing_disk_revert)
parser.add_option("-i", "--install-stage",
					help="installing stage3.",
					action="callback",
					callback=installing_stage)
					
(options, args) = parser.parse_args()



#parser = argparse.ArgumentParser(description='Gentoo AMD64 Handbook :: Basic Install Process')

#parser.add_argument('--preparing-disk',
#					default='10', type=int, nargs=1,
#                    help='To be able to install Gentoo, the necessary partitions need to be created.')
#parser.add_argument('--preparing-disk',
#					'-pdsk',
#					help='To be able to install Gentoo, the necessary partitions need to be created.',
#					action="count")
#parser.add_argument('--verbose', '-v', action='count')
#
#args = parser.parse_args()


# preparing_disk()
# installing_satage()


def cpuinfo():
 cpuinfo=OrderedDict()
 procinfo=OrderedDict()
 nprocs = 0
 with open('/proc/cpuinfo') as f:
  for line in f:
   if not line.strip():
    cpuinfo['proc%s' % nprocs] = procinfo
    nprocs=nprocs+1
    procinfo=OrderedDict()
   else:
    if len(line.split(':')) == 2:
     procinfo[line.split(':')[0].strip()] = line.split(':')[1].strip()
    else:
     procinfo[line.split(':')[0].strip()] = ''
 return cpuinfo

cpuinfo = cpuinfo()['proc0']
print(cpuinfo)


print("Vendor ID: "+cpuinfo['vendor_id']) 
print("CPU family: "+cpuinfo['cpu family']) 
print("Model: "+cpuinfo['model']) 
print("Model name: "+cpuinfo['model name']) 
