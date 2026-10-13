"""Build an ext4 image from a prepared tree; does not flash or mount devices."""
import argparse, hashlib, json, os, pathlib, shutil, subprocess
p=argparse.ArgumentParser()
p.add_argument('--source',type=pathlib.Path,required=True)
p.add_argument('--output',type=pathlib.Path,required=True)
p.add_argument('--size-mib',type=int,default=3072)
a=p.parse_args()
if a.source.is_symlink() or not a.source.is_dir(): p.error('Source must be an ordinary prepared directory')
if not (a.source/'etc/os-release').is_file() or not os.path.lexists(a.source/'sbin/init'): p.error('Missing OS metadata or init')
if not 32 <= a.size_mib <= 4096: p.error('Image size must be 32..4096 MiB')
if a.output.exists() or a.output.is_symlink(): p.error('Output must not already exist')
if not a.output.parent.is_dir(): p.error('Output parent must exist')
if a.output.resolve().is_relative_to(a.source.resolve()): p.error('Output must be outside the source tree')
partial=a.output.with_name(a.output.name+'.part')
if partial.exists() or partial.is_symlink(): p.error('Partial output exists; inspect it before retrying')
size=a.size_mib*1024**2
if shutil.disk_usage(a.output.parent).free < size+256*1024**2: p.error('Insufficient space for full image plus 256 MiB reserve')
features='none,has_journal,ext_attr,resize_inode,dir_index,filetype,extent,flex_bg,sparse_super,large_file,huge_file,uninit_bg,dir_nlink,extra_isize'
with partial.open('xb') as file: file.truncate(size)
subprocess.run(['mke2fs','-q','-t','ext4','-b','4096','-I','256','-m','0','-O',features,'-E','lazy_itable_init=0,lazy_journal_init=0','-L','ubuntu-rootfs','-d',str(a.source),str(partial)],check=True)
subprocess.run(['e2fsck','-f','-n',str(partial)],check=True)
h=hashlib.sha256()
with partial.open('rb') as file:
    while chunk:=file.read(1024*1024): h.update(chunk)
partial.rename(a.output)
print(json.dumps({'bytes':size,'sha256':h.hexdigest(),'features':features,'scope':'image construction only; not installation or hardware acceptance'}))
