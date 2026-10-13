"""Record cached Debian package identities without installing anything."""
import argparse, hashlib, json, pathlib, subprocess
p=argparse.ArgumentParser()
p.add_argument('--directory',type=pathlib.Path,required=True)
p.add_argument('--output',type=pathlib.Path,required=True)
a=p.parse_args()
records=[]
for file in sorted(a.directory.rglob('*.deb')):
    result=subprocess.run(['dpkg-deb','--field',str(file)],check=True,capture_output=True,text=True)
    fields=dict(line.split(': ',1) for line in result.stdout.splitlines() if ': ' in line and not line.startswith(' '))
    record={key:fields.get(key) for key in ('Package','Version','Architecture','Source')}
    record.update(filename=file.name,relative_path=file.relative_to(a.directory).as_posix(),bytes=file.stat().st_size,sha256=hashlib.sha256(file.read_bytes()).hexdigest())
    records.append(record)
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(json.dumps({'scope':'cached build packages; not a proof every package was used','packages':records},indent=2)+'\n')
print('Cached package records',len(records))
