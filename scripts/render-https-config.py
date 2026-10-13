"""Generate phone-only TLS proxy configuration; never modify a live system."""
import argparse, ipaddress, pathlib, re
p=argparse.ArgumentParser()
p.add_argument('--host',required=True)
p.add_argument('--port',type=int,default=9119)
p.add_argument('--backend-port',type=int,default=9120)
p.add_argument('--base',default='/userdata/tf-card/hermes')
p.add_argument('--output',type=pathlib.Path,required=True)
a=p.parse_args()
host=str(ipaddress.IPv4Address(a.host))
if not (1 <= a.port <= 65535 and 1 <= a.backend_port <= 65535) or a.port==a.backend_port:
    p.error('Ports must be valid and distinct')
if not re.fullmatch(r'/[A-Za-z0-9_/-]+',a.base) or '..' in a.base.split('/'):
    p.error('Use an absolute base path without spaces or traversal')
a.output.mkdir(parents=True,exist_ok=False)
url=f'https://{host}:{a.port}'
(a.output/'Caddyfile').write_text(f'{{\n    admin off\n    auto_https disable_redirects\n}}\n\n{url} {{\n    tls internal\n    reverse_proxy 127.0.0.1:{a.backend_port}\n}}\n')
(a.output/'yuga-hermes-https.service').write_text(f'''[Unit]
Description=Hermes HTTPS proxy on Yuga
After=network.target yuga-hermes-web.service
Requires=yuga-hermes-web.service
RequiresMountsFor={a.base}

[Service]
Type=simple
Environment=HOME={a.base}/https
Environment=GOMEMLIMIT=128MiB
Environment=GOMAXPROCS=2
Environment=XDG_DATA_HOME={a.base}/https/data
Environment=XDG_CONFIG_HOME={a.base}/https/config
ExecStart={a.base}/native/caddy run --config {a.base}/https/Caddyfile --adapter caddyfile
Restart=on-failure
RestartSec=10
UMask=0077

[Install]
WantedBy=multi-user.target
''')
(a.output/'web-backend.conf').write_text(f'[Service]\nExecStart=\nExecStart={a.base}/hermes-tf-launch.sh dashboard --host 127.0.0.1 --port {a.backend_port} --skip-build --no-open\n')
(a.output/'public-url.txt').write_text(url+'\n')
print('Generated configuration only; set dashboard.public_url and preserve authentication before deploying.')
