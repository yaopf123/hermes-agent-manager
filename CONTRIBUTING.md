# Contributing

## Local checks

```bash
python3 -m py_compile app/app.py app/wechat_bind.py
bash -n scripts/install.sh
bash -n scripts/install-remote.sh
bash -n scripts/load-images.sh
bash -n docker/install-docker-ubuntu.sh
```

Do not commit API keys, `models.yaml`, agent data directories, or Docker image tarballs.
