"""Stream one image only after matching READY, and require a matching final receipt."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import socket

CHUNK = 1024 * 1024

def receipt(reader):
    line=reader.readline(257)
    if not line.endswith(b'\n') or len(line)>256:
        raise ValueError('Missing or oversized receipt')
    fields=line.decode('ascii').strip().split()
    if len(fields)!=4:
        raise ValueError('Malformed receipt')
    return fields

def send_image(path,host,port,name,expected_hash,timeout=600,progress=None):
    if name not in ('rootfs.img','system.img') or not re.fullmatch('[0-9a-f]{64}',expected_hash):
        raise ValueError('Invalid image identity')
    with Path(path).open('rb') as source:
        size=os.fstat(source.fileno()).st_size
        if not 0<size<=4294967296:
            raise ValueError('Invalid image size')
        digest=hashlib.sha256()
        while block:=source.read(CHUNK): digest.update(block)
        if digest.hexdigest()!=expected_hash:
            raise ValueError('Local image hash mismatch')
        source.seek(0)
        identity=[name,str(size),expected_hash]
        with socket.create_connection((host,port),timeout=timeout) as connection:
            connection.settimeout(timeout)
            with connection.makefile('rb') as reader:
                ready=receipt(reader)
                if ready[1:]!=identity or ready[0] not in ('READY','ALREADY_COMMITTED'):
                    raise ValueError('Receiver identity mismatch')
                if ready[0]=='ALREADY_COMMITTED': return ready[0]
                sent=0; streamed=hashlib.sha256()
                while block:=source.read(CHUNK):
                    connection.sendall(block); streamed.update(block); sent+=len(block)
                    if progress is not None: progress(sent,size)
                if sent!=size or streamed.hexdigest()!=expected_hash:
                    raise ValueError('Source changed during transmission')
                connection.shutdown(socket.SHUT_WR)
                committed=receipt(reader)
                if committed!=['COMMITTED',*identity]:
                    raise ValueError('Missing matching commit receipt')
                return committed[0]

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image',type=Path)
    parser.add_argument('name',choices=['rootfs.img','system.img'])
    parser.add_argument('sha256')
    parser.add_argument('--host',default='172.16.42.1')
    parser.add_argument('--port',type=int,default=9997)
    args=parser.parse_args()
    last=[0]
    def progress(sent,size):
        if sent==size or sent-last[0]>=64*1024**2:
            print('SENT',args.name,sent,size,flush=True); last[0]=sent
    print(send_image(args.image,args.host,args.port,args.name,args.sha256,progress=progress),flush=True)
