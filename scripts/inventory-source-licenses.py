"""Copy only top-level license notices; source archives retain full notices."""
import argparse, hashlib, json, pathlib, tarfile
p=argparse.ArgumentParser()
p.add_argument('--sources',type=pathlib.Path,required=True)
p.add_argument('--output',type=pathlib.Path,required=True)
a=p.parse_args(); records=[]
for archive in sorted(a.sources.rglob('*.tar.*')):
    notices=[]
    with tarfile.open(archive,'r:*') as bundle:
        for member in bundle:
            path=pathlib.PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts: raise ValueError('Unsafe archive path')
            if len(path.parts)>2 or not member.isfile(): continue
            if not path.name.upper().startswith(('LICENSE','COPYING','NOTICE','COPYRIGHT')): continue
            if member.size>1024*1024: raise ValueError('Unexpected large license notice')
            content=bundle.extractfile(member).read()
            target=a.output/archive.name/path
            target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(content)
            notices.append({'member':member.name,'sha256':hashlib.sha256(content).hexdigest()})
    records.append({'archive':archive.relative_to(a.sources).as_posix(),'notices':notices})
a.output.mkdir(parents=True,exist_ok=True)
(a.output/'inventory.json').write_text(json.dumps({'scope':'top-level notices only; not complete dependency license audit','archives':records},indent=2)+'\n')
print('Archives',len(records),'notices',sum(len(x['notices']) for x in records))
