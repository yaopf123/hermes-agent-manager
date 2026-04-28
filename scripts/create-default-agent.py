#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
from pathlib import Path

import yaml

APP_DIR = Path(os.environ.get('APP_DIR', '/home/ypf/hermes-manager'))
HERMES_DIR = Path(os.environ.get('HERMES_DIR', '/home/ypf/hermes-docker'))
IMAGE = os.environ.get('HERMES_AGENT_IMAGE', 'nousresearch/hermes-agent:latest')
AGENT = re.sub(r'[^a-z0-9_-]+', '-', os.environ.get('DEFAULT_AGENT_NAME', 'coder').strip().lower()).strip('-_') or 'coder'
if AGENT.startswith('hermes-'):
    AGENT = AGENT.removeprefix('hermes-')
SERVICE = f'hermes-{AGENT}'
PORT = os.environ.get('DEFAULT_AGENT_PORT', '8642')
API_KEY = os.environ.get('DEFAULT_AGENT_API_KEY', f'hermes-{AGENT}-local-key')
API_MODEL = os.environ.get('DEFAULT_AGENT_API_MODEL', f'hermes-{AGENT}')
SOUL = os.environ.get('DEFAULT_AGENT_SOUL', 'You are a helpful Hermes agent.')
START = os.environ.get('START_DEFAULT_AGENT', 'true').lower() == 'true'

UPSTREAM = {
    'provider': os.environ.get('UPSTREAM_PROVIDER', 'custom'),
    'base_url': os.environ.get('UPSTREAM_BASE_URL', 'https://coding.dashscope.aliyuncs.com/v1'),
    'model': os.environ.get('UPSTREAM_MODEL', 'qwen3.6-plus'),
    'api_key': os.environ.get('UPSTREAM_API_KEY', 'sk-no-key-required'),
    'context_length': int(os.environ.get('UPSTREAM_CONTEXT_LENGTH', '262144')),
    'max_tokens': int(os.environ.get('UPSTREAM_MAX_TOKENS', '8192')),
}

LOOP_RULE = '''

## Task Loop Control

You must not stay stuck in an endless task loop.

Operational limits:
- Treat one model/tool cycle as one working loop.
- After 6 loops on the same user request, pause internally and check whether there is real progress.
- After 12 loops total, stop working and ask the user for clarification, approval, or a narrower next step.
- If the same tool/action fails 2 times with the same error, do not repeat it a third time without changing strategy.
- If a task is blocked by missing credentials, missing files, insufficient permissions, API quota, expired login, or ambiguous requirements, stop and ask the user.
- Before asking the user, summarize what you tried, what failed, and the exact decision or input you need.
- Never silently continue long-running exploration just because more tools are available.
'''


def run(cmd, cwd=None, check=True):
    print('+', ' '.join(map(str, cmd)))
    return subprocess.run(cmd, cwd=cwd, check=check)


def set_env(path: Path, updates: dict[str, str]):
    lines = path.read_text().splitlines() if path.exists() else []
    seen = set()
    out = []
    for line in lines:
        if '=' in line and not line.lstrip().startswith('#'):
            key = line.split('=', 1)[0]
            if key in updates:
                out.append(f'{key}={updates[key]}')
                seen.add(key)
                continue
        out.append(line)
    if updates:
        out.append('')
        out.append('# Managed by Hermes Manager installer')
    for key, value in updates.items():
        if key not in seen:
            out.append(f'{key}={value}')
    path.write_text('\n'.join(out).rstrip() + '\n')


def install_custom_skills(agent_dir: Path):
    src = HERMES_DIR / 'custom-skills'
    if not src.exists():
        return
    target_root = agent_dir / 'skills'
    for skill_md in src.rglob('SKILL.md'):
        rel = skill_md.parent.relative_to(src)
        target = target_root / rel
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill_md.parent, target)


def main():
    HERMES_DIR.mkdir(parents=True, exist_ok=True)
    agent_dir = HERMES_DIR / AGENT
    agent_dir.mkdir(parents=True, exist_ok=True)

    if not (agent_dir / 'config.yaml').exists():
        run(['docker', 'run', '--rm', '-v', f'{agent_dir}:/opt/data', IMAGE, 'version'], check=False)

    cfg_path = agent_dir / 'config.yaml'
    cfg = yaml.safe_load(cfg_path.read_text()) if cfg_path.exists() else {}
    cfg = cfg or {}
    cfg['model'] = {
        'default': UPSTREAM['model'],
        'provider': UPSTREAM['provider'],
        'base_url': UPSTREAM['base_url'],
        'context_length': UPSTREAM['context_length'],
        'max_tokens': UPSTREAM['max_tokens'],
    }
    cfg.setdefault('terminal', {})['cwd'] = '/opt/data/workspace'
    cfg.setdefault('agent', {})['max_turns'] = 12
    cfg.setdefault('delegation', {})['max_iterations'] = 8
    cfg.setdefault('delegation', {})['child_timeout_seconds'] = 300
    cfg.setdefault('code_execution', {})['max_tool_calls'] = 12
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))

    set_env(agent_dir / '.env', {
        'OPENAI_API_KEY': UPSTREAM['api_key'],
        'HERMES_INFERENCE_PROVIDER': UPSTREAM['provider'],
        'HERMES_API_TIMEOUT': '1800',
        'API_SERVER_ENABLED': 'true',
        'API_SERVER_HOST': '0.0.0.0',
        'API_SERVER_PORT': '8642',
        'API_SERVER_CORS_ORIGINS': '*',
        'API_SERVER_KEY': API_KEY,
        'API_SERVER_MODEL_NAME': API_MODEL,
        'GATEWAY_ALLOW_ALL_USERS': 'true',
    })

    (agent_dir / 'SOUL.md').write_text(f'# {AGENT.title()}\n\n{SOUL.rstrip()}\n{LOOP_RULE}\n')
    install_custom_skills(agent_dir)

    compose_path = HERMES_DIR / 'docker-compose.yml'
    compose = yaml.safe_load(compose_path.read_text()) if compose_path.exists() else {}
    compose = compose or {}
    services = compose.setdefault('services', {})
    services[SERVICE] = {
        'image': IMAGE,
        'container_name': SERVICE,
        'restart': 'unless-stopped',
        'command': 'gateway run',
        'ports': [f'{PORT}:8642'],
        'volumes': [
            f'{agent_dir}:/opt/data',
            f'{HERMES_DIR}/patches/weixin.py:/opt/hermes/gateway/platforms/weixin.py:ro',
        ],
        'shm_size': '1gb',
        'extra_hosts': ['host.docker.internal:host-gateway'],
        'environment': ['GATEWAY_ALLOW_ALL_USERS=true'],
        'deploy': {'resources': {'limits': {'memory': '4G', 'cpus': '2.0'}}},
    }
    compose_path.write_text(yaml.safe_dump(compose, sort_keys=False, allow_unicode=True))

    run(['chown', '-R', '10000:10000', str(agent_dir)], check=False)
    if START:
        run(['docker', 'compose', 'up', '-d', SERVICE], cwd=HERMES_DIR)


if __name__ == '__main__':
    main()
