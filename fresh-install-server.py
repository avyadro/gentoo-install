from __future__ import print_function
import argparse
import requests
import multiprocessing
from collections import OrderedDict
import pprint
from optparse import OptionParser
import os, sys

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
		self.timezone="US/Central"
		self.locale="en_US.UTF-8 UTF-8"
		self.rootdir = "/mnt/gentoo"
		self.hostname = "gentoo"
		self.domain = "mudnetworks.net"
		self.arch = "amd64"
		self.cpuinfo = Map()
		self.cpuinfo.put('cpus', multiprocessing.cpu_count())
		self.cpuinfo.put('march', 'ivybridge')
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
	def chroot(self):
		print("=> Entering the new environment")	
		if not self.dummy:
			self.real_root = os.open("/mnt/gentoo", os.O_RDONLY)
			os.chroot("/mnt/gentoo")
			# Chrooted environment
			# Put statements to be executed as chroot here
			os.fchdir(self.real_root)
			os.chroot(".")
	def close_chroot(self):
		print("=> Leaving the new environment")	
		if not self.dummy:			
			os.close(self.real_root)
	def awk_add_update(self,key,value,filename):
		print("=> Adding and/or replacing value into file "+filename)		
		cmd = "awk -v s="+key+"="+value+" '/^"+key+"=/{$0=s;f=1} {a[++n]=$0} END{if(!f)a[++n]=s;for(i=1;i<=n;i++)print a[i]>ARGV[1]}' "+filename
		self.shell(cmd)

	def shell(self,cmd):
		print(cmd)
		if not self.dummy:
			os.system(cmd)

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
	print("=> Updating parameter make.conf")
	gentoo.awk_add_update(
		"COMMON_FLAGS",
		"\\\"-march="+gentoo.cpuinfo.get('march').value+" -02 -pipe \\\"",
		"/mnt/gentoo/etc/portage/make.conf")
	gentoo.awk_add_update(
		"MAKEOPTS",
		"\\\"-j"+str(gentoo.cpuinfo.get('cpus').value+1)+"\\\"",
		"/mnt/gentoo/etc/portage/make.conf")
	gentoo.awk_add_update(
		"GRUB_PLATFORMS",
		"\\\"efi-64\\\"",
		"/mnt/gentoo/etc/portage/make.conf")
def installing_base(option, opt, value, parser):
	print("#####################################")
	print("# Installing the Gentoo base system #")
	print("#####################################")
	print("=> Configuring the Gentoo ebuild repository")
	print("** Creating the repos.conf directory")
	cmd = "mkdir --parents /mnt/gentoo/etc/portage/repos.conf"
	gentoo.shell(cmd)
	print("** Copying the Gentoo repository configuration file provided by Portage")
	cmd = "\\cp -lrv /mnt/gentoo/usr/share/portage/config/repos.conf /mnt/gentoo/etc/portage/repos.conf/gentoo.conf"
	gentoo.shell(cmd)
	print("** Copying DNS info")
	cmd = "cp --dereference /etc/resolv.conf /mnt/gentoo/etc/"
	gentoo.shell(cmd)
	print("** Mounting the necessary filesystems")
	cmd = "mount --types proc /proc /mnt/gentoo/proc"
	gentoo.shell(cmd)
	cmd = "mount --rbind /sys /mnt/gentoo/sys"
	gentoo.shell(cmd)
	cmd = "mount --make-rslave /mnt/gentoo/sys"
	gentoo.shell(cmd)
	cmd = "mount --rbind /dev /mnt/gentoo/dev"
	gentoo.shell(cmd)
	cmd = "mount --make-rslave /mnt/gentoo/dev"
	gentoo.shell(cmd)
	gentoo.chroot()	
	cmd = "source /etc/profile"
	gentoo.shell(cmd)
	cmd = 'export PS1="(chroot) ${PS1}"'
	gentoo.shell(cmd)
	print("=> Mounting the boot partition")
	cmd = "mount "+gentoo.disk+str(gentoo.p_boot)+" /boot"
	gentoo.shell(cmd)
	if not os.path.isdir('/boot/efi'):
		print("=> Creating efi directory")
		cmd = "mkdir /boot/efi"
		gentoo.shell(cmd)
	print("=> Mounting the efi partition")
	cmd = "mount "+gentoo.disk+str(gentoo.p_efi)+" /boot/efi"
	gentoo.shell(cmd)
	print("=> Updating the Gentoo ebuild repository")
	cmd = "emerge --sync"
	gentoo.shell(cmd)
	print("=> Updating the @world set")
	cmd = "emerge --ask --verbose --update --deep --newuse @world"
	gentoo.shell(cmd)
	print("=> Configuring Timezone")
	cmd = 'echo "'+gentoo.timezone+'" > /etc/timezone'
	gentoo.shell(cmd)
	cmd = "emerge --config sys-libs/timezone-data"
	gentoo.shell(cmd)
	print("=> Configuring locales")
	cmd = 'echo "'+gentoo.locale+'" >> /etc/locale.gen'
	gentoo.shell(cmd)
	cmd = "locale-gen"
	gentoo.shell(cmd)
	cmd = 'env-update && source /etc/profile && export PS1="(chroot) $PS1"'
	gentoo.shell(cmd)
	
def configure_kernel(option, opt, value, parser):
	print("#####################################")
	print("# Configuring the Linux kernel      #")
	print("#####################################")
	gentoo.chroot()
	print("=> Installing Gentoo sources")
	cmd = "emerge --ask sys-kernel/gentoo-sources"
	gentoo.shell(cmd)
	print("** Default: Manual configuration")
	cmd = "cd /usr/src/linux"
	gentoo.shell(cmd)
	cmd = "make menuconfig"
	gentoo.shell(cmd)
	print("=> Compiling and installing")
	cmd = "make && make modules_install"
	gentoo.shell(cmd)
	cmd = "make install"
	gentoo.shell(cmd)
	print("=> Installing Genkernel")
	cmd = "emerge --ask sys-kernel/genkernel"
	gentoo.shell(cmd)
	print("=> Building an initramfs")
	cmd = "genkernel --lvm --install initramfs"
	gentoo.shell(cmd)
	print("=> Leaving chroot")
	gentoo.close_chroot()
def configure_kernel_automatically(option, opt, value, parser):
	print("#####################################")
	print("# Configuring the Linux kernel      #")
	print("#####################################")	
	gentoo.chroot()
	print("=> Executing etc-update for merge configuration")
	cmd = "etc-update"
	gentoo.shell(cmd)
	print("=> Installing Gentoo sources")
	cmd = "emerge --ask sys-kernel/gentoo-sources"
	gentoo.shell(cmd)
	print("=> Installing Genkernel")
	cmd = "emerge --ask sys-kernel/genkernel"
	print("** Alternative: Using genkernel")
	gentoo.shell(cmd)
	cmd = "genkernel all"
	gentoo.shell(cmd)
	print("=> Installing firmware")
	cmd = "emerge --ask sys-kernel/linux-firmware"
	gentoo.shell(cmd)
	gentoo.close_chroot()
def configure_system(option, opt, value, parser):
	print("#####################################")
	print("# Configuring the system      #")
	print("#####################################")
	gentoo.chroot()
	print("=> Networking information")
	print("** Host and domain information")
	gentoo.awk_add_update(
		"hostname",
		"\\\""+gentoo.hostname+"\\\"",
		"/etc/conf.d/hostname")		
	if not os.path.isfile('/etc/conf.d/net'):
		print("** Creating file /etc/conf.d/net")
		cmd = 'echo "# File created by BFurther Gentoo Instal" > /etc/conf.d/net'
	gentoo.awk_add_update(
		"dns_domain_lo",
		"\\\""+gentoo.domain+"\\\"",
		"/etc/conf.d/net")
	print("=> Installing system tools")
	print("** Installing system logger")
	cmd = "emerge --ask app-admin/sysklogd"
	gentoo.shell(cmd)
	cmd = "rc-update add sysklogd default"
	gentoo.shell(cmd)
	print("** Installing cron daemon")
	cmd = "emerge --ask sys-process/cronie"
	gentoo.shell(cmd)
	cmd = "rc-update add cronie default"
	gentoo.shell(cmd)
	print("** Installing file indexing")
	cmd = "emerge --ask sys-apps/mlocate"
	gentoo.shell(cmd)
	print("** Enabling remote access")
	cmd = "rc-update add sshd default"
	gentoo.shell(cmd)
	print("** Installing filesystem tools")
	cmd = "emerge --ask sys-fs/lvm2"
	gentoo.shell(cmd)
	cmd = "rc-update add lvm boot"
	gentoo.shell(cmd)
	cmd = "emerge --ask	sys-fs/e2fsprogs"
	gentoo.shell(cmd)
	cmd = "emerge --ask sys-fs/dosfstools"
	gentoo.shell(cmd)	
	# BOOTLOADER - GRUB2	
	print("=> Configuring the bootloader")
	cmd = "genkernel --lvm --install initramfs"
	gentoo.shell(cmd)
	print("** Installing GRUB2")
	cmd = "echo 'sys-boot/grub:2 device-mapper' >> /etc/portage/package.use/package.use"
	gentoo.shell(cmd)
	cmd = "emerge --ask --verbose sys-boot/grub:2"
	gentoo.shell(cmd)	
	cmd = "mount -o remount,rw /sys/firmware/efi/efivars"
	gentoo.shell(cmd)	
	cmd = "grub-install --target=x86_64-efi --efi-directory=/boot/efi"
	gentoo.shell(cmd)
	gentoo.awk_add_update(
		"GRUB_CMDLINE_LINUX",
		"\\\"dolvm\\\"",
		"/etc/default/grub")
	cmd = "grub-mkconfig -o /boot/grub/grub.cfg"
	gentoo.shell(cmd)
	print("=> Set root password")
	cmd = "passwd"
	gentoo.shell(cmd)
	
	gentoo.close_chroot()

gentoo = GentooInstall()



usage = "usage: %prog [options] arg"
parser = OptionParser(usage)
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
parser.add_option("-I", "--install-base",
					help="installing the Gentoo base system.",
					action="callback",
					callback=installing_base)
parser.add_option("-k", "--kernel",
					help="configuring & installing the Linux kernel manual",
					action="callback",
					callback=configure_kernel)
parser.add_option("-K", "--kernel-auto",
					help="configuring & installing the Linux kernel automatic",
					action="callback",
					callback=configure_kernel_automatically)
parser.add_option("-c", "--configure-system",
					help="configuring the system",
					action="callback",
					callback=configure_system)					
(options, args) = parser.parse_args()
