"""Read-only audit of resolved revisions and local source modifications."""
import argparse, json, pathlib, subprocess, xml.etree.ElementTree as ET
p = argparse.ArgumentParser()
p.add_argument('--root', type=pathlib.Path, required=True)
p.add_argument('--manifest', type=pathlib.Path, required=True)
p.add_argument('--output', type=pathlib.Path, required=True)
a = p.parse_args()
results = []
for project in ET.parse(a.manifest).getroot().findall('project'):
    item = {'path':project.get('path') or project.get('name'), 'expected':project.get('revision')}
    if not item['path']:
        raise ValueError('Manifest project has neither path nor name')
    directory = a.root / item['path']
    try:
        head = subprocess.run(['git','-C',str(directory),'rev-parse','HEAD'],capture_output=True,text=True,timeout=60,check=True).stdout.strip()
        changes = subprocess.run(['git','-C',str(directory),'status','--porcelain','--untracked-files=normal'],capture_output=True,text=True,timeout=120,check=True).stdout.splitlines()
        item.update(actual=head, revision_matches=head==item['expected'], changes=changes)
    except (OSError, subprocess.SubprocessError) as exc:
        item['error'] = type(exc).__name__
    results.append(item)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps({'completed':False,'projects':results},indent=2)+'\n')
a.output.write_text(json.dumps({'completed':True,'projects':results},indent=2)+'\n')
print(json.dumps({'projects':len(results),'errors':sum('error' in x for x in results),'revision_mismatches':sum(x.get('revision_matches') is False for x in results),'modified_projects':sum(bool(x.get('changes')) for x in results)}))
