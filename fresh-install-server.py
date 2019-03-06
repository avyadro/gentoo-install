class Map(object):
     def __init__(self,key,value):
         self.key=key
         self.value=value
         
class List(object):
     def __init__(self):
         """
         """ 
         self.list = []  
     def put(self,key,value):
         self.list.append(Map(key,value))
     def get(self,key):
         for e in self.list:
            if e.key == key:
              return e                  
     def list(self):
         return self.list
         
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
		# Physical volume
		self.lvm_pv=self.disk+"3" 
		# Volume group
		self.lvm_vg="gentoo"
		# Logical volume
		_lvms = List()
		_lvms.put('swapfs','-L 8G')
		_lvms.put('homefs','-L 8G')
		_lvms.put('rootfs','-l 100%VG')
		self.lvms = _lvms.list
	def shell(self,cmd):
		print(cmd)

		

def revert():
	print("=> Removing logical volumes according to the new schema")
	for e in gentoo.lvms:
		print("- "+e.key)    
		cmd = "lvremove -y /dev/"+gentoo.lvm_vg+"/"+e.key
		gentoo.shell(cmd)
	print("=> Removing volume group")
	cmd = "vgremove -y "+gentoo.lvm_vg
	gentoo.shell(cmd)
	print("=> Removing physical volume")
	cmd = "pvremove -y "+gentoo.lvm_pv
	gentoo.shell(cmd)

def process():
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
	cmd = "pvcreate -y "+gentoo.lvm_pv
	gentoo.shell(cmd)
	print("=> Creating the volume group")
	cmd = "vgcreate -y "+gentoo.lvm_vg+" "+gentoo.lvm_pv
	gentoo.shell(cmd)
	cmd = "vgchange -ay"
	gentoo.shell(cmd)
	print("=> Creating the logical volumes")
	for e in gentoo.lvms:
		print("+ "+e.key)    
		cmd = "lvcreate -y "+e.value+" -n "+e.key+" "+gentoo.lvm_vg
		gentoo.shell(cmd)
	print("=> Creating the filesystems")
	print("** Creating EFI filesystem")
	cmd = "mkfs.fat -F 32 "+gentoo.disk+str(gentoo.p_efi)
	gentoo.shell(cmd)
	print("** Creating BOOT filesystem")
	cmd = "mkfs.ext2 -F "+gentoo.disk+str(gentoo.p_boot)
	gentoo.shell(cmd)
	print("** Creating SWAP filesystem")
	cmd = "mkswap /dev/"+gentoo.lvm_vg
	gentoo.shell(cmd)
	#echo -e "\t\t=> Activating the swap partition <="
	#swapon /dev/gentoo/swapfs
	#echo -e "\t=> Creating HOME filesystem /dev/gentoo/homefs (ext4) <="
	#mkfs.ext4 -F /dev/gentoo/homefs
	#echo -e "\t=> Creating ROOT filesystem /dev/gentoo/rootfs (ext4) <="
	#mkfs.ext4 -F /dev/gentoo/rootfs
	#echo -e "=> Mounting the root partition <="
	#mount /dev/gentoo/rootfs /mnt/gentoo
		
gentoo = GentooInstall()

process()
