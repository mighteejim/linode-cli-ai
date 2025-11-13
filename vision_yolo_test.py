import pathlib
import subprocess
import textwrap
from linodecli_ai.core.cloud_init import CloudInitConfig, generate_cloud_init

cfg=CloudInitConfig(
    container_image='ultralytics/ultralytics:latest',
    internal_port=8000,
    external_port=8080,
    env_vars={'UVICORN_HOST':'0.0.0.0','UVICORN_PORT':'8000'},
    command='python -m ultralytics serve --show --host 0.0.0.0 --port 8000'
)
script=generate_cloud_init(cfg)
path=pathlib.Path('tmp_script.sh')
path.write_text('\n'.join(line for line in script.splitlines() if line.startswith('#!/bin/bash') or line.startswith('docker run')))
print('wrote', path)
