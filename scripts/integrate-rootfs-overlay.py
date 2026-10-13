"""Integrate public files into a staging tree, with separate userdata output."""
import argparse, hashlib, json, os, pathlib, shutil
p=argparse.ArgumentParser()
p.add_argument('--root',type=pathlib.Path,required=True)
p.add_argument('--overlay',type=pathlib.Path,required=True)
p.add_argument('--userdata',type=pathlib.Path,required=True)
a=p.parse_args()
if a.overlay.is_symlink() or not a.overlay.is_dir(): p.error('Overlay must be an ordinary directory')
if os.name!='posix' or os.geteuid()!=0: p.error('Use a root Linux staging environment')
if a.root.is_symlink() or not a.root.is_dir() or a.root.resolve()==pathlib.Path('/'): p.error('Refusing non-staging root')
root=a.root.resolve(); data=a.userdata.resolve()
if a.userdata.exists() or a.userdata.is_symlink() or data.is_relative_to(root): p.error('Userdata output must be new and outside rootfs')
metadata=root/'etc/os-release'; config=root/'var/lib/lxc/android/config'
if not metadata.resolve().is_relative_to(root) or not metadata.is_file(): p.error('Missing or unsafe root metadata')
if not config.resolve().is_relative_to(root) or not config.is_file(): p.error('Missing or unsafe LXC config')
old=config.read_text()
if old.count('lxc.tty.max = 4')!=1 or 'lxc.console.path' in old: p.error('Unexpected LXC config; inspect instead of guessing')
plan=[]
for source in sorted(a.overlay.rglob('*')):
    if source.is_symlink(): p.error('Symlink in overlay input')
    if not source.is_file(): continue
    relative=source.relative_to(a.overlay)
    if relative.as_posix()=='README.md': continue
    if relative.parts[0] not in ('etc','usr','userdata'): p.error('Unexpected overlay namespace')
    base=data if relative.parts[0]=='userdata' else root
    target=base.joinpath(*relative.parts[1:]) if base==data else base/relative
    if target.is_symlink() or not target.resolve().is_relative_to(base): p.error('Overlay target escapes staging')
    if target.exists() and not target.is_file(): p.error('Overlay target is not an ordinary file')
    plan.append((source,target,relative))
if not plan: p.error('No overlay files selected')
# Only write after every target and the LXC replacement have been checked.
a.userdata.mkdir(parents=True,mode=0o700,exist_ok=False)
records=[]
for source,target,relative in plan:
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,target)
    target.chmod(0o755 if target.suffix=='.sh' else 0o644)
    os.chown(target,0,0)
    records.append({'path':relative.as_posix(),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
config.write_text(old.replace('lxc.tty.max = 4','lxc.tty.max = 0\nlxc.console.path = none'))
print(json.dumps({'copied_files':records,'lxc_console_disabled':True,'scope':'staging integration only; service enabling and first-boot setup still required'},indent=2))
