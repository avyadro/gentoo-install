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
		# Stage
		self.stage="http://distfiles.gentoo.org/releases/amd64/autobuilds/current-stage3-amd64/stage3-amd64-20190305T214502Z.tar.xz"
	def shell(self,cmd):
		print(cmd)

		

def revert():
	print("=> Removing logical volumes according to the new schema")
	for e in gentoo.lvms:
		print("- "+e.name)    
		cmd = "lvremove -y /dev/"+gentoo.lvm_vg+"/"+e.name
		gentoo.shell(cmd)
	print("=> Removing volume group")
	cmd = "vgremove -y "+gentoo.lvm_vg
	gentoo.shell(cmd)
	print("=> Removing physical volume")
	cmd = "pvremove -y "+gentoo.disk+str(gentoo.p_lvm)
	gentoo.shell(cmd)

def preparing_disk():
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
def installing_satage():
	print("##############################")
	print("# Installing a stage tarball #")
	print("##############################")
	print("=> Setting the date and time")
	cmd="ntpd -q -g"
	gentoo.shell(cmd)
	print("=> Entering /mnt/gentoo directory")
	cmd = "cd /mnt/gentoo"
	gentoo.shell(cmd)
	print("=> Downloading stage")
	cmd = "wget -c "+gentoo.stage
	gentoo.shell(cmd)
	print("=> Unpacking the stage tarball")
	cmd = "tar xpvf stage3-*.tar.bz2 --xattrs-include='*.*' --numeric-owner"

gentoo = GentooInstall()

# preparing_disk()
installing_satage()
