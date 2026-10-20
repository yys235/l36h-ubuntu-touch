"""Per-device SSH initialization. Runtime entry point uses fixed phone paths."""
import base64,hashlib,json,os,pathlib,re,stat,subprocess,sys,tempfile

KEY_TYPES={'ssh-ed25519','ssh-rsa','ecdsa-sha2-nistp256','ecdsa-sha2-nistp384','ecdsa-sha2-nistp521'}

def safe_path(path,directory=False,private=False):
    path=pathlib.Path(path)
    for part in [path,*path.parents]:
        if part.is_symlink(): raise ValueError('Unexpected symlink in persistent path')
    info=path.stat()
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise ValueError('Unexpected persistent file type')
    if info.st_uid!=0 or info.st_mode & (0o077 if private else 0o022):
        raise ValueError('Unsafe persistent ownership or permission')
    return path

def public_key(path):
    safe_path(path)
    if path.stat().st_size>16384: raise ValueError('Invalid public key size')
    lines=path.read_text().splitlines()
    if len(lines)!=1: raise ValueError('Invalid public key: require one line')
    text=lines[0].strip(); parts=text.split(None,2)
    if len(parts)<2 or parts[0] not in KEY_TYPES: raise ValueError('Invalid public key or authorized-key options')
    try: base64.b64decode(parts[1],validate=True)
    except ValueError: raise ValueError('Invalid public key encoding')
    r=subprocess.run(['ssh-keygen','-l','-f',str(path)],capture_output=True,text=True)
    if r.returncode: raise ValueError('Invalid public key rejected by ssh-keygen')
    return text+'\n'

def validate_mounts(text,userdata,root_directory,ssh_directory):
    mounts={}
    for line in text.splitlines():
        fields=line.split()
        if len(fields)<10 or '-' not in fields: continue
        separator=fields.index('-')
        if separator+3>=len(fields): continue
        name=re.sub(r'\\([0-7]{3})',lambda match:chr(int(match.group(1),8)),fields[4])
        mounts.setdefault(name,[]).append((fields[2],fields[5].split(','),fields[separator+1],fields[separator+3].split(',')))
    device=None
    for path in [userdata,root_directory,ssh_directory]:
        path=pathlib.Path(path)
        entries=mounts.get(str(path),[])
        if len(entries)!=1: raise ValueError('Required persistent mount missing or ambiguous: '+str(path))
        mounted,options,kind,super_options=entries[0]
        actual=path.stat().st_dev
        if mounted!=str(os.major(actual))+':'+str(os.minor(actual)) or 'rw' not in options or 'rw' not in super_options or kind!='ext4':
            raise ValueError('Wrong device, type or read-only persistent mount')
        if device is not None and mounted!=device: raise ValueError('Persistent mounts are not on userdata')
        device=mounted

def validate_sshd(text):
    values={}
    for line in text.splitlines():
        parts=line.split(None,1)
        if len(parts)==2: values.setdefault(parts[0].lower(),[]).append(parts[1].strip())
    expected={'port':'22','passwordauthentication':'no','pubkeyauthentication':'yes','authenticationmethods':'publickey','allowusers':'root'}
    for key,value in expected.items():
        if values.get(key)!=[value]: raise ValueError('Unsafe effective SSH configuration: '+key)
    if values.get('permitrootlogin') not in (['without-password'],['prohibit-password']):
        raise ValueError('Unsafe effective SSH root login policy')
    interactive=[key for key in ['challengeresponseauthentication','kbdinteractiveauthentication'] if key in values]
    if not interactive or any(values[key]!=['no'] for key in interactive):
        raise ValueError('Unsafe effective SSH interactive authentication')

def sync_directory(path):
    descriptor=os.open(str(path),os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)

def atomic_new(path,data,mode=0o600):
    descriptor,name=tempfile.mkstemp(prefix='.yuga-init-',dir=str(path.parent))
    temporary=pathlib.Path(name)
    try:
        with os.fdopen(descriptor,'wb') as output:
            os.fchmod(output.fileno(),mode); os.fchown(output.fileno(),0,0)
            output.write(data); output.flush(); os.fsync(output.fileno())
        os.link(str(temporary),str(path))  # Never overwrite an identity or admin edit.
        temporary.unlink(); sync_directory(path.parent)
    finally:
        if temporary.exists(): temporary.unlink()

def ensure_host_key(ssh_directory):
    ssh_directory=pathlib.Path(ssh_directory); safe_path(ssh_directory,directory=True)
    key=ssh_directory/'ssh_host_ed25519_key'; pub=key.with_name(key.name+'.pub')
    if not os.path.lexists(key):
        with tempfile.TemporaryDirectory(prefix='.yuga-keygen-',dir=str(ssh_directory)) as directory:
            generated=pathlib.Path(directory)/'identity'
            subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(generated)],check=True,capture_output=True)
            atomic_new(key,generated.read_bytes())
    safe_path(key,private=True)
    derived=subprocess.check_output(['ssh-keygen','-y','-f',str(key)],text=True).strip()
    if os.path.lexists(pub):
        safe_path(pub)
        if pub.read_text().split()[:2]!=derived.split()[:2]: raise ValueError('Host identity public/private mismatch')
    else: atomic_new(pub,(derived+'\n').encode(),mode=0o644)
    output=subprocess.check_output(['ssh-keygen','-l','-f',str(key)],text=True).split()
    if len(output)<2 or not output[1].startswith('SHA256:'): raise ValueError('Invalid host identity fingerprint')
    return output[1]

def read_json(path,private=False):
    safe_path(path,private=private)
    if path.stat().st_size>16384: raise ValueError('Oversized initialization metadata')
    value=json.loads(path.read_text())
    if not isinstance(value,dict): raise ValueError('Invalid initialization metadata')
    return value

def initialize(userdata,root_directory,ssh_directory,mountinfo,sshd_configuration):
    if os.geteuid()!=0: raise ValueError('Initialization requires root')
    userdata=pathlib.Path(userdata); root_directory=pathlib.Path(root_directory); ssh_directory=pathlib.Path(ssh_directory)
    validate_mounts(mountinfo,userdata,root_directory,ssh_directory)
    for path in [userdata,root_directory,ssh_directory]: safe_path(path,directory=True)
    state=userdata/'yuga-firstboot'; inputs=state/'input'
    safe_path(state,directory=True,private=True); safe_path(inputs,directory=True,private=True)
    canonical=public_key(inputs/'authorized_key')
    config=read_json(inputs/'config.json')
    if set(config)!={'schema_version','server_mode'} or type(config['schema_version']) is not int or config['schema_version']!=1 or type(config['server_mode']) is not bool:
        raise ValueError('Invalid firstboot input schema')
    validate_sshd(sshd_configuration)
    marker=state/'status.json'; previous=None
    key_hash=hashlib.sha256(canonical.encode()).hexdigest()
    if os.path.lexists(marker):
        previous=read_json(marker,private=True)
        if set(previous)!={'schema_version','server_mode','input_key_sha256','host_key_fingerprint'} or type(previous.get('schema_version')) is not int or previous.get('schema_version')!=1 or type(previous.get('server_mode')) is not bool or previous.get('server_mode')!=config['server_mode'] or previous.get('input_key_sha256')!=key_hash:
            raise ValueError('Invalid or inconsistent initialization status')
        if not (ssh_directory/'ssh_host_ed25519_key').is_file(): raise ValueError('Successful marker has missing host identity')
    authorized_directory=root_directory/'.ssh'; authorized=authorized_directory/'authorized_keys'
    if os.path.lexists(authorized_directory): safe_path(authorized_directory,directory=True,private=True)
    if os.path.lexists(authorized):
        safe_path(authorized,private=True)
        if not previous and authorized.read_text().strip()!=canonical.strip(): raise ValueError('Existing authorized_keys conflict; refusing overwrite')
        r=subprocess.run(['ssh-keygen','-l','-f',str(authorized)],capture_output=True,text=True)
        if r.returncode: raise ValueError('Invalid existing authorized_keys')
    elif previous: raise ValueError('Successful marker has missing authorized_keys')
    fingerprint=ensure_host_key(ssh_directory)
    if previous and previous['host_key_fingerprint']!=fingerprint: raise ValueError('Device host identity changed since initialization')
    if not authorized_directory.exists(): authorized_directory.mkdir(mode=0o700)
    sync_directory(root_directory)
    if not authorized.exists(): atomic_new(authorized,canonical.encode())
    record={'schema_version':1,'server_mode':config['server_mode'],'input_key_sha256':key_hash,'host_key_fingerprint':fingerprint}
    if previous is None: atomic_new(marker,(json.dumps(record,sort_keys=True)+'\n').encode())
    return {'initialized':True,'reused_identity':previous is not None,'host_key_fingerprint':fingerprint}

def main():
    output=subprocess.check_output(['/usr/sbin/sshd','-T','-C','user=root,host=localhost,addr=192.0.2.1'],text=True)
    return initialize(pathlib.Path('/userdata'),pathlib.Path('/root'),pathlib.Path('/etc/ssh'),pathlib.Path('/proc/self/mountinfo').read_text(),output)

if __name__=='__main__':
    try: print(json.dumps(main()))
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        print('Yuga SSH initialization failed: '+str(error),file=sys.stderr)
        sys.exit(1)
