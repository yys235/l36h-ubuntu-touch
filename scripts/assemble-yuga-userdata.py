"""Assemble only the whitelisted fresh-install userdata payload, never live data."""
import argparse,importlib.util,json,os,pathlib,shutil

spec=importlib.util.spec_from_file_location('firstboot_preparer',pathlib.Path(__file__).with_name('prepare-yuga-firstboot.py'))
preparer=importlib.util.module_from_spec(spec); spec.loader.exec_module(preparer)

def assemble(overlay,firstboot,output):
    if os.name!='posix' or os.geteuid()!=0: raise ValueError('Use root in a Linux staging environment')
    if os.path.lexists(output) or os.path.lexists(output.with_name(output.name+'.part')):
        raise ValueError('Output or partial output already exists')
    preparer.no_links(output)
    if not output.parent.is_dir(): raise ValueError('Output parent does not exist')
    expected=[(overlay,{'yuga-port/bluetooth-init.sh'}),(firstboot,{'yuga-firstboot/input/authorized_key','yuga-firstboot/input/config.json'})]
    plan=[]
    for base,names in expected:
        preparer.no_links(base)
        if not base.is_dir() or base.resolve()==pathlib.Path('/') or base.is_mount(): raise ValueError('Input must be a staging directory')
        if output.resolve().is_relative_to(base.resolve()) or base.resolve().is_relative_to(output.resolve()): raise ValueError('Output overlaps input')
        for name in names:
            path=base/name
            if path.is_symlink(): raise ValueError('Symlink in userdata input')
            if not path.is_file(): raise ValueError('Missing required userdata file: '+name)
        directories={str(parent) for name in names for parent in pathlib.PurePosixPath(name).parents if str(parent)!='.'}
        for path in base.rglob('*'):
            name=path.relative_to(base).as_posix()
            if path.is_symlink(): raise ValueError('Symlink in userdata input')
            if path.is_dir():
                if name not in directories: raise ValueError('Unexpected userdata directory')
            elif not path.is_file() or name not in names: raise ValueError('Unexpected userdata file')
        plan.extend((base/name,name) for name in sorted(names))
    preparer.public_key(firstboot/'yuga-firstboot/input/authorized_key')
    config=json.loads((firstboot/'yuga-firstboot/input/config.json').read_text())
    if not isinstance(config,dict) or set(config)!={'schema_version','server_mode'} or type(config['schema_version']) is not int or config['schema_version']!=1 or type(config['server_mode']) is not bool:
        raise ValueError('Invalid firstboot schema')
    partial=output.with_name(output.name+'.part'); partial.mkdir(mode=0o700)
    for source,name in plan:
        parent=partial
        for part in pathlib.PurePosixPath(name).parts[:-1]:
            parent=parent/part
            if not parent.exists(): parent.mkdir(mode=0o700)
        target=partial/name; shutil.copyfile(source,target)
        target.chmod(0o755 if name.endswith('.sh') else 0o400); os.chown(target,0,0)
    if os.path.lexists(output): raise ValueError('Output appeared during assembly; partial retained')
    partial.rename(output)
    return {'assembled':True,'files':len(plan),'scope':'personalized staging payload; not device installation'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--overlay-data',required=True,type=pathlib.Path)
    p.add_argument('--firstboot-data',required=True,type=pathlib.Path)
    p.add_argument('--output',required=True,type=pathlib.Path)
    a=p.parse_args()
    try: print(json.dumps(assemble(a.overlay_data,a.firstboot_data,a.output)))
    except (ValueError,OSError,UnicodeError) as error: p.error(str(error))
