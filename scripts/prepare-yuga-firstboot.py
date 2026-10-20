"""Prepare a fresh rootfs and separate, device-specific firstboot payload."""
import argparse,base64,hashlib,json,os,pathlib,shutil,subprocess

TEMPLATES=pathlib.Path(__file__).resolve().parent.parent/'firstboot'
KEY_TYPES={'ssh-ed25519','ssh-rsa','ecdsa-sha2-nistp256','ecdsa-sha2-nistp384','ecdsa-sha2-nistp521'}

def public_key(path):
    if path.is_symlink() or not path.is_file(): raise ValueError('Public key must be an ordinary file')
    if path.stat().st_size>16384: raise ValueError('Invalid public key length')
    lines=path.read_text().splitlines()
    if len(lines)!=1: raise ValueError('Invalid public key: require one line')
    text=lines[0].strip()
    parts=text.split(None,2)
    if '\n' in text or '\r' in text or len(parts)<2 or parts[0] not in KEY_TYPES:
        raise ValueError('Invalid public key: require one key without options')
    try: base64.b64decode(parts[1],validate=True)
    except ValueError: raise ValueError('Invalid public key encoding')
    result=subprocess.run(['ssh-keygen','-l','-f',str(path)],capture_output=True,text=True)
    if result.returncode: raise ValueError('Invalid public key rejected by ssh-keygen')
    return text+'\n'

def no_links(path):
    for part in [path,*path.parents]:
        if part.is_symlink(): raise ValueError('Symlink in staging target: '+str(part))

def contained_file(root,path,label):
    try: resolved=path.resolve(strict=True)
    except (OSError,RuntimeError): raise ValueError('Missing or invalid '+label)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError('Unsafe '+label+' outside staging')
    return resolved

def prepare(root,userdata,key,server_mode):
    if os.name!='posix' or os.geteuid()!=0: raise ValueError('Use root in a Linux staging environment')
    if root.is_symlink() or not root.is_dir() or root.resolve()==pathlib.Path('/') or root.is_mount():
        raise ValueError('Refusing non-staging root')
    no_links(root); root=root.resolve()
    if root.stat().st_uid!=0 or root.stat().st_mode & 0o022:
        raise ValueError('Staging root must be root-owned and not group/world writable')
    if userdata.exists() or userdata.is_symlink(): raise ValueError('Userdata output must be new')
    no_links(userdata)
    if not userdata.parent.is_dir() or userdata.resolve().is_relative_to(root) or root.is_relative_to(userdata.resolve()):
        raise ValueError('Userdata output must be outside rootfs with an existing parent')
    metadata=contained_file(root,root/'etc/os-release','staging metadata')
    if not any(line.replace('"','').replace("'",'')=='VERSION_ID=20.04' for line in metadata.read_text().splitlines()):
        raise ValueError('Staging root must be the supported Ubuntu20.04 input')
    canonical=public_key(key)
    ssh=root/'etc/ssh'; no_links(ssh)
    if list(ssh.glob('ssh_host_*_key*')) or os.path.lexists(root/'root/.ssh/authorized_keys'):
        raise ValueError('Source identity must not be included in a fresh image')
    config=ssh/'sshd_config'; no_links(config)
    active=[line.strip() for line in config.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
    if not active or active[0]!='Include /etc/ssh/sshd_config.d/*.conf':
        raise ValueError('Unexpected SSH baseline or Include ordering')
    blocked={'port','permitrootlogin','passwordauthentication','pubkeyauthentication','authenticationmethods','authorizedkeysfile','hostkey','allowusers','match','listenaddress','include'}
    if any(line.split()[0].lower() in blocked for line in active[1:]):
        raise ValueError('Unexpected SSH authentication overrides')
    fragments=ssh/'sshd_config.d'; no_links(fragments)
    allowed_fragments={'50-lxc-android-config.conf':'e45e78736aadde6566596a368d08a2cbdc57344d033111ee1b4590cf2b284019'}
    if fragments.exists():
        for fragment in fragments.iterdir():
            if fragment.is_symlink() or not fragment.is_file() or fragment.name not in allowed_fragments or hashlib.sha256(fragment.read_bytes()).hexdigest()!=allowed_fragments[fragment.name]:
                raise ValueError('Unexpected or modified SSH configuration fragment')
    override=root/'etc/systemd/system/ssh.service'
    dropins=root/'etc/systemd/system/ssh.service.d'; no_links(dropins)
    if os.path.lexists(override) or (dropins.exists() and list(dropins.iterdir())):
        raise ValueError('Unexpected SSH service override or drop-in')
    if (ssh/'sshd_not_to_be_run').exists(): raise ValueError('SSH explicitly disabled in source image')
    required=['lib/systemd/system/ssh.service','etc/systemd/system/yuga-wlan-init.service','etc/systemd/system/yuga-backlight-interface.service']
    if server_mode: required.append('etc/systemd/system/yuga-server-awake.service')
    for name in required:
        contained_file(root,root/name,'required service '+name)
    files={
        'usr/lib/yuga-firstboot/yuga_firstboot.py':'yuga_firstboot.py',
        'etc/systemd/system/yuga-firstboot.service':'yuga-firstboot.service',
        'etc/systemd/system/ssh.service.d/20-yuga-firstboot.conf':'ssh-firstboot.conf',
        'etc/ssh/sshd_config.d/00-yuga-bootstrap.conf':'sshd-bootstrap.conf',
    }
    links={
        'etc/systemd/system/multi-user.target.wants/ssh.service':'/lib/systemd/system/ssh.service',
        'etc/systemd/system/multi-user.target.wants/yuga-wlan-init.service':'/etc/systemd/system/yuga-wlan-init.service',
        'etc/systemd/system/multi-user.target.wants/yuga-backlight-interface.service':'/etc/systemd/system/yuga-backlight-interface.service',
    }
    if server_mode:
        links['etc/systemd/system/multi-user.target.wants/yuga-server-awake.service']='/etc/systemd/system/yuga-server-awake.service'
        for name in ['sleep.target','suspend.target','hibernate.target','hybrid-sleep.target']:
            links['etc/systemd/system/'+name]='/dev/null'
    for name in [*files,*links]:
        target=root/name; no_links(target.parent)
        if os.path.lexists(target):
            if name in links and target.is_symlink() and os.readlink(target)==links[name]: continue
            raise ValueError('Existing staging target: '+name)
        for parent in target.parents:
            if parent==root: break
            if parent.exists() and (not parent.is_dir() or parent.stat().st_uid!=0 or parent.stat().st_mode & 0o022):
                raise ValueError('Unsafe staging parent: '+str(parent))
    for name in files.values():
        source=TEMPLATES/name
        if source.is_symlink() or not source.is_file(): raise ValueError('Missing ordinary firstboot template '+name)
    # No writes until all destinations, input and templates have passed preflight.
    userdata.mkdir(mode=0o700)
    state=userdata/'yuga-firstboot'; state.mkdir(mode=0o700)
    inputs=state/'input'; inputs.mkdir(mode=0o700)
    for name,text in [('authorized_key',canonical),('config.json',json.dumps({'schema_version':1,'server_mode':server_mode})+'\n')]:
        path=inputs/name; path.write_text(text); path.chmod(0o400); os.chown(path,0,0)
    for name,template in files.items():
        target=root/name; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(TEMPLATES/template,target); target.chmod(0o644); os.chown(target,0,0)
    for name,value in links.items():
        target=root/name; target.parent.mkdir(parents=True,exist_ok=True)
        if not target.is_symlink(): target.symlink_to(value)
    return {'prepared':True,'server_mode':server_mode,'scope':'staging only; not hardware acceptance'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True,type=pathlib.Path)
    p.add_argument('--userdata',required=True,type=pathlib.Path)
    p.add_argument('--public-key',required=True,type=pathlib.Path)
    p.add_argument('--server-mode',action='store_true')
    args=p.parse_args()
    try: print(json.dumps(prepare(args.root,args.userdata,args.public_key,args.server_mode)))
    except (ValueError,OSError,UnicodeError) as error: p.error(str(error))
