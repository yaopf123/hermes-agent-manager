import os
import re
import shlex
import subprocess
import json
import io
import secrets
import html
import urllib.request
import urllib.error
import time
import shutil
from pathlib import Path
from typing import Dict, Any

import yaml
from flask import Flask, request, redirect, url_for, render_template_string, abort, flash, send_file, Response

APP_DIR = Path(os.environ.get('HERMES_MANAGER_APP_DIR', '/home/ypf/hermes-manager'))
ROOT = Path(os.environ.get('HERMES_DOCKER_ROOT', '/home/ypf/hermes-docker'))
COMPOSE = ROOT / 'docker-compose.yml'
MODEL_LIBRARY = Path(os.environ.get('HERMES_MODEL_LIBRARY', str(APP_DIR / 'models.yaml')))
CUSTOM_SKILLS = ROOT / 'custom-skills'
IMAGE = os.environ.get('HERMES_AGENT_IMAGE', 'nousresearch/hermes-agent:latest')
PUBLIC_HOST = os.environ.get('HERMES_MANAGER_PUBLIC_HOST', '192.168.1.21')
DEFAULT_UPSTREAM_BASE_URL = 'https://coding.dashscope.aliyuncs.com/v1'
DEFAULT_UPSTREAM_MODEL = 'qwen3.6-plus'
DEFAULT_UPSTREAM_KEY = os.environ.get('DEFAULT_UPSTREAM_KEY', '')
TOKEN = os.environ.get('HERMES_MANAGER_TOKEN', 'change-me')
TASK_LOOP_RULE = '''

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

app = Flask(__name__)
app.secret_key = os.environ.get('HERMES_MANAGER_SECRET', 'local-dev-secret')

CSS = r'''
:root { color-scheme: dark; --bg:#0f1216; --panel:#171b21; --panel2:#1f252d; --text:#eef2f6; --muted:#98a2ad; --line:#2b3440; --ok:#58d68d; --bad:#ff6b6b; --accent:#78a6ff; }
* { box-sizing: border-box; }
body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:var(--bg); color:var(--text); }
a { color: var(--accent); text-decoration: none; }
header { padding:18px 24px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; align-items:center; background:#11151a; position:sticky; top:0; z-index:10; }
h1 { font-size:18px; margin:0; letter-spacing:0; }
main { padding:24px; max-width:1320px; margin:0 auto; }
.grid { display:grid; gap:16px; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); }
.panel { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; }
.agent { display:flex; flex-direction:column; gap:12px; }
.row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
.space { justify-content:space-between; }
.muted { color:var(--muted); }
.badge { padding:3px 8px; border-radius:999px; background:var(--panel2); border:1px solid var(--line); font-size:12px; color:var(--muted); }
.badge.ok { color:#b9ffd2; border-color:#2b6842; background:#14251b; }
.badge.bad { color:#ffc7c7; border-color:#743636; background:#2b1717; }
.traffic { display:inline-flex; width:12px; height:12px; border-radius:999px; border:1px solid var(--line); background:#59616b; margin-right:8px; vertical-align:-1px; box-shadow:0 0 0 2px rgba(255,255,255,0.03); }
.traffic.ok { background:#46d17a; border-color:#2b6842; box-shadow:0 0 10px rgba(70,209,122,0.35); }
.traffic.bad { background:#ff5f68; border-color:#743636; box-shadow:0 0 10px rgba(255,95,104,0.25); }
code, pre { background:#0b0e12; border:1px solid var(--line); border-radius:6px; }
code { padding:2px 5px; }
pre { padding:12px; overflow:auto; white-space:pre-wrap; }
form { display:grid; gap:10px; }
label { display:grid; gap:5px; color:var(--muted); font-size:13px; }
input, textarea, select { width:100%; padding:9px 10px; border-radius:6px; border:1px solid var(--line); background:#0d1116; color:var(--text); font:inherit; }
textarea { min-height:86px; resize:vertical; }
button, .button { border:1px solid var(--line); background:var(--panel2); color:var(--text); border-radius:6px; padding:8px 11px; cursor:pointer; font:inherit; display:inline-flex; align-items:center; justify-content:center; min-height:36px; }
button.primary, .button.primary { background:#244c8f; border-color:#3867b6; }
button.danger { background:#4a1f25; border-color:#843743; }
button:hover, .button:hover { filter:brightness(1.12); }
.actions { display:flex; gap:8px; flex-wrap:wrap; }
.table { width:100%; border-collapse:collapse; }
.table th, .table td { padding:9px 8px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
.table th { color:var(--muted); font-weight:600; }
.flash { margin-bottom:12px; padding:10px 12px; border-radius:6px; border:1px solid #4d5f2d; background:#202715; color:#eaffbe; }
.flash.ok { border-color:#2b6842; background:#14251b; color:#b9ffd2; }
.flash.bad { border-color:#743636; background:#2b1717; color:#ffc7c7; }
.two { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
@media (max-width:800px) { .two { grid-template-columns:1fr; } header { align-items:flex-start; flex-direction:column; gap:8px; } }
'''

BASE = '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="icon" href="{{ url_for('favicon') }}"><title>Hermes Manager</title><style>{{ css }}</style></head><body><header><h1>Hermes Agent Manager</h1><div class="row"><span class="badge">{{ root }}</span><a class="button" href="{{ url_for('index', token=token) }}">Agents</a><a class="button" href="{{ url_for('models_page', token=token) }}">Models</a><a class="button" href="{{ url_for('logs', token=token) }}">Logs</a></div></header><main>{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for category, m in messages %}<div class="flash {{ category }}">{{ m }}</div>{% endfor %}{% endif %}{% endwith %}{{ body|safe }}</main></body></html>'''


def check_token():
    if request.args.get('token') == TOKEN or request.form.get('token') == TOKEN:
        return
    abort(403)


@app.before_request
def auth():
    if request.endpoint in {'static', 'favicon'}:
        return
    check_token()


@app.route('/favicon.ico')
def favicon():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#171b21"/><path d="M14 18h36v8H28v6h18v8H28v6h22v8H14z" fill="#78a6ff"/></svg>'
    return Response(svg, mimetype='image/svg+xml')


def run(cmd, cwd=None, timeout=120):
    p = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(map(shlex.quote, cmd))}\n{p.stdout}")
    return p.stdout


def compose_data() -> Dict[str, Any]:
    if not COMPOSE.exists():
        return {'services': {}}
    return yaml.safe_load(COMPOSE.read_text()) or {'services': {}}


def save_compose(data):
    COMPOSE.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def slugify_name(value):
    value = (value or '').strip().lower()
    if value.startswith('hermes-'):
        value = value.removeprefix('hermes-')
    value = re.sub(r'[^a-z0-9_-]+', '-', value).strip('-_')
    return value


def model_library():
    if not MODEL_LIBRARY.exists():
        return {'models': []}
    data = yaml.safe_load(MODEL_LIBRARY.read_text()) or {}
    data.setdefault('models', [])
    return data


def save_model_library(data):
    MODEL_LIBRARY.parent.mkdir(parents=True, exist_ok=True)
    MODEL_LIBRARY.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def model_profiles():
    return model_library().get('models', []) or []


def get_model_profile(profile_id):
    for profile in model_profiles():
        if profile.get('id') == profile_id:
            return profile
    return None


def set_model_test_status(profile_id, status, message):
    data = model_library()
    for profile in data.get('models', []):
        if profile.get('id') == profile_id:
            profile['test_status'] = status
            profile['test_message'] = message[:500]
            profile['tested_at'] = int(time.time())
            save_model_library(data)
            return profile
    return None


def mask_secret(value):
    if not value:
        return ''
    if len(value) <= 8:
        return '********'
    return value[:4] + '...' + value[-4:]


def test_model_connection(profile):
    base_url = (profile.get('base_url') or '').rstrip('/')
    if not base_url:
        raise RuntimeError('base_url is empty')
    url = f'{base_url}/chat/completions'
    payload = {
        'model': profile.get('model') or DEFAULT_UPSTREAM_MODEL,
        'messages': [{'role': 'user', 'content': 'ping'}],
        'max_tokens': 1,
        'temperature': 0,
    }
    headers = {'Content-Type': 'application/json'}
    if profile.get('api_key'):
        headers['Authorization'] = f"Bearer {profile.get('api_key')}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read(4096).decode('utf-8', errors='replace')
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read(4096).decode('utf-8', errors='replace')
        raise RuntimeError(f'HTTP {e.code}: {body[:1000]}')
    except urllib.error.URLError as e:
        raise RuntimeError(f'connection failed: {e.reason}')


def apply_model_to_agent(agent, profile, api_model=None, api_key=None, restart=True):
    update_config(
        agent,
        profile.get('model') or DEFAULT_UPSTREAM_MODEL,
        profile.get('base_url') or DEFAULT_UPSTREAM_BASE_URL,
        profile.get('provider') or 'custom',
        str(profile.get('context_length') or '262144'),
        str(profile.get('max_tokens') or '8192'),
    )
    updates = {
        'HERMES_INFERENCE_PROVIDER': profile.get('provider') or 'custom',
        'API_SERVER_MODEL_NAME': api_model or f'hermes-{agent}',
        'API_SERVER_KEY': api_key or f'hermes-{agent}-local-key',
    }
    if profile.get('api_key'):
        updates['OPENAI_API_KEY'] = str(profile.get('api_key'))
    set_env(data_dir(agent) / '.env', updates)
    if restart:
        run(['docker', 'compose', 'restart', service_name(agent)], cwd=ROOT, timeout=180)


def service_name(agent):
    return f'hermes-{agent}'


def agent_from_service(svc):
    return svc.removeprefix('hermes-')


def data_dir(agent):
    return ROOT / agent


def read_file(path):
    try:
        return Path(path).read_text()
    except Exception:
        return ''


def parse_env(text):
    out = {}
    for line in text.splitlines():
        if '=' in line and not line.strip().startswith('#'):
            k, v = line.split('=', 1)
            out[k.strip()] = v.strip()
    return out


def set_env(path: Path, updates: Dict[str, str]):
    lines = path.read_text().splitlines() if path.exists() else []
    seen = set()
    new = []
    for line in lines:
        if '=' in line and not line.lstrip().startswith('#'):
            k = line.split('=', 1)[0]
            if k in updates:
                new.append(f'{k}={updates[k]}')
                seen.add(k)
                continue
        new.append(line)
    if updates:
        new.append('')
        new.append('# Managed by Hermes Manager')
    for k, v in updates.items():
        if k not in seen:
            new.append(f'{k}={v}')
    path.write_text('\n'.join(new) + '\n')


def update_config(agent, model, base_url, provider='custom', context_length='262144', max_tokens='8192'):
    cfg = data_dir(agent) / 'config.yaml'
    text = cfg.read_text()
    out = []
    for line in text.splitlines():
        stripped = line.lstrip()
        indent = line[:len(line)-len(stripped)]
        if not stripped.startswith('#') and stripped.startswith('default:'):
            line = f'{indent}default: "{model}"'
        elif not stripped.startswith('#') and stripped.startswith('provider:'):
            line = f'{indent}provider: "{provider}"'
        elif not stripped.startswith('#') and stripped.startswith('base_url:'):
            line = f'{indent}base_url: "{base_url}"'
        elif not stripped.startswith('#') and stripped.startswith('context_length:'):
            line = f'{indent}context_length: {context_length}'
        elif not stripped.startswith('#') and stripped.startswith('max_tokens:'):
            line = f'{indent}max_tokens: {max_tokens}'
        out.append(line)
    joined = '\n'.join(out)
    if 'context_length:' not in joined:
        joined += f'\ncontext_length: {context_length}'
    if 'max_tokens:' not in joined:
        joined += f'\nmax_tokens: {max_tokens}'
    cfg.write_text(joined + '\n')


def apply_loop_limits(agent):
    cfg = data_dir(agent) / 'config.yaml'
    if cfg.exists():
        data = yaml.safe_load(cfg.read_text()) or {}
        data.setdefault('agent', {})['max_turns'] = 12
        data.setdefault('delegation', {})['max_iterations'] = 8
        data.setdefault('delegation', {})['child_timeout_seconds'] = 300
        data.setdefault('code_execution', {})['max_tool_calls'] = 12
        cfg.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def write_soul(agent, content):
    base = f"# {agent.title()}\n\n{content or 'You are a helpful Hermes agent.'}"
    if '## Task Loop Control' not in base:
        base = base.rstrip() + TASK_LOOP_RULE
    (data_dir(agent) / 'SOUL.md').write_text(base.rstrip() + '\n')


def parse_config(agent):
    text = read_file(data_dir(agent) / 'config.yaml')
    info = {'model': '', 'provider': '', 'base_url': '', 'context_length': '', 'max_tokens': ''}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('#') or ':' not in stripped:
            continue
        k, v = stripped.split(':', 1)
        v = v.strip().strip('"')
        if k == 'default': info['model'] = v
        if k == 'provider': info['provider'] = v
        if k == 'base_url': info['base_url'] = v
        if k == 'context_length': info['context_length'] = v
        if k == 'max_tokens': info['max_tokens'] = v
    return info


def docker_status():
    try:
        out = run(['docker', 'ps', '--format', '{{.Names}}|{{.Status}}|{{.Ports}}'], timeout=20)
    except Exception:
        return {}
    status = {}
    for line in out.splitlines():
        parts = line.split('|', 2)
        if len(parts) == 3:
            status[parts[0]] = {'status': parts[1], 'ports': parts[2]}
    return status


def list_agents():
    data = compose_data()
    services = data.get('services', {}) or {}
    statuses = docker_status()
    agents = []
    for svc, spec in services.items():
        if not svc.startswith('hermes-'):
            continue
        agent = agent_from_service(svc)
        cfg = parse_config(agent)
        env = parse_env(read_file(data_dir(agent) / '.env'))
        ports = spec.get('ports') or []
        public_port = ''
        if ports:
            public_port = str(ports[0]).split(':', 1)[0].strip('"')
        agents.append({
            'name': agent,
            'service': svc,
            'port': public_port,
            'api_model': env.get('API_SERVER_MODEL_NAME', svc),
            'api_key': env.get('API_SERVER_KEY', ''),
            'cfg': cfg,
            'status': statuses.get(svc, {}).get('status', 'stopped'),
            'ports': statuses.get(svc, {}).get('ports', ''),
        })
    return sorted(agents, key=lambda x: x['port'] or x['name'])


def ensure_initialized(agent):
    d = data_dir(agent)
    d.mkdir(parents=True, exist_ok=True)
    if not (d / 'config.yaml').exists():
        run(['docker', 'run', '--rm', '-v', f'{d}:/opt/data', IMAGE, 'version'], timeout=300)


def install_custom_skills(agent):
    if not CUSTOM_SKILLS.exists():
        return
    target_root = data_dir(agent) / 'skills'
    for skill_dir in CUSTOM_SKILLS.rglob('SKILL.md'):
        rel = skill_dir.parent.relative_to(CUSTOM_SKILLS)
        target = target_root / rel
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill_dir.parent, target)
    try:
        run(['chown', '-R', '10000:10000', str(target_root)], timeout=60)
    except Exception:
        pass


def next_port():
    used = {a['port'] for a in list_agents() if a['port']}
    port = 8642
    while str(port) in used:
        port += 1
    return str(port)


def render(body, **ctx):
    return render_template_string(BASE, body=body, css=CSS, root=str(ROOT), token=TOKEN, **ctx)


@app.route('/')
def index():
    agents = list_agents()
    profiles = model_profiles()
    profile_options = '<option value="">Use default model</option>' + ''.join(
        f'<option value="{html.escape(p.get("id", ""))}">{html.escape(p.get("name", p.get("model", "model")))} - {html.escape(p.get("model", ""))}</option>'
        for p in profiles
    )
    create_html = f'''
    <section class="panel"><h2>New Agent</h2>
    <form method="post" action="{url_for('create_agent')}">
      <input type="hidden" name="token" value="{TOKEN}">
      <div class="two"><label>Name<input name="name" placeholder="planner" required pattern="[a-zA-Z0-9_-]+"></label><label>Port<input name="port" value="{next_port()}" required></label></div>
      <label>Model preset<select name="model_profile">{profile_options}</select></label>
      <div class="two"><label>Agent API model name<input name="api_model" placeholder="hermes-planner"></label><label>Agent API key<input name="api_key" placeholder="hermes-planner-local-key"></label></div>
      <label>SOUL / role<textarea name="soul">You are a helpful Hermes agent. Keep work inside /opt/data/workspace unless instructed otherwise.</textarea></label>
      <button class="primary" type="submit">Create Agent</button>
    </form></section>'''
    cards = []
    for a in agents:
        running = a['status'].lower().startswith('up')
        cards.append(f'''
        <section class="panel agent">
          <div class="row space"><h2>{a['name']}</h2><span class="badge {'ok' if running else 'bad'}">{a['status']}</span></div>
          <div class="muted">Service <code>{a['service']}</code> · Port <code>{a['port']}</code></div>
          <div>Agent URL <code>http://{PUBLIC_HOST}:{a['port']}/v1</code></div>
          <div>Agent model <code>{a['api_model']}</code></div>
          <div>Upstream <code>{a['cfg']['provider']}</code> · <code>{a['cfg']['model']}</code></div>
          <div class="muted"><code>{a['cfg']['base_url']}</code></div>
          <div class="actions">
            <form method="post" action="{url_for('restart_agent', agent=a['name'])}"><input type="hidden" name="token" value="{TOKEN}"><button>Restart</button></form>
            <form method="post" action="{url_for('stop_agent', agent=a['name'])}"><input type="hidden" name="token" value="{TOKEN}"><button>Stop</button></form>
            <form method="post" action="{url_for('start_agent', agent=a['name'])}"><input type="hidden" name="token" value="{TOKEN}"><button>Start</button></form>
            <a class="button" href="{url_for('edit_agent', agent=a['name'], token=TOKEN)}">Switch Model</a>
            <a class="button" href="{url_for('wechat_agent', agent=a['name'], token=TOKEN)}">WeChat</a>
            <a class="button" href="{url_for('agent_logs', agent=a['name'], token=TOKEN)}">Logs</a>
          </div>
          <form method="post" action="{url_for('delete_agent', agent=a['name'])}" onsubmit="return confirm('Delete {a['name']}?')"><input type="hidden" name="token" value="{TOKEN}"><label class="row"><input style="width:auto" type="checkbox" name="delete_data" value="1"> Delete data directory too</label><button class="danger">Delete Agent</button></form>
        </section>''')
    body = create_html + '<div style="height:16px"></div><section class="grid">' + ''.join(cards) + '</section>'
    return render(body)


@app.route('/agent/<agent>/edit')
def edit_agent(agent):
    cfg = parse_config(agent)
    env = parse_env(read_file(data_dir(agent) / '.env'))
    profiles = model_profiles()
    profile_options = ''.join(
        f'<option value="{html.escape(p.get("id", ""))}">{html.escape(p.get("name", p.get("model", "model")))} - {html.escape(p.get("model", ""))}</option>'
        for p in profiles
    ) or '<option value="">No saved presets</option>'
    preset_html = f'''<section class="panel"><h2>One-Click Preset: {agent}</h2>
    <form method="post" action="{url_for('apply_model_profile', agent=agent)}">
      <input type="hidden" name="token" value="{TOKEN}">
      <label>Model preset<select name="profile_id">{profile_options}</select></label>
      <div class="two"><label>Agent API model name<input name="api_model" value="{env.get('API_SERVER_MODEL_NAME', 'hermes-'+agent)}"></label><label>Agent API key<input name="api_key" value="{env.get('API_SERVER_KEY','')}"></label></div>
      <button class="primary">Apply Preset and Restart</button>
    </form></section><div style="height:16px"></div>'''
    body = preset_html + f'''
    <section class="panel"><h2>Manual Switch Model: {agent}</h2>
    <form method="post" action="{url_for('save_agent', agent=agent)}">
      <input type="hidden" name="token" value="{TOKEN}">
      <label>Provider<input name="provider" value="{cfg['provider'] or 'custom'}"></label>
      <label>Base URL<input name="base_url" value="{cfg['base_url']}"></label>
      <div class="two"><label>Model<input name="model" value="{cfg['model']}"></label><label>Upstream API key<input type="password" name="upstream_key" placeholder="leave blank to keep current"></label></div>
      <div class="two"><label>Context length<input name="context_length" value="{cfg['context_length'] or '262144'}"></label><label>Max tokens<input name="max_tokens" value="{cfg['max_tokens'] or '8192'}"></label></div>
      <div class="two"><label>Agent API model name<input name="api_model" value="{env.get('API_SERVER_MODEL_NAME', 'hermes-'+agent)}"></label><label>Agent API key<input name="api_key" value="{env.get('API_SERVER_KEY','')}"></label></div>
      <button class="primary">Save and Restart</button>
    </form></section>'''
    return render(body)


@app.route('/agent/<agent>/save', methods=['POST'])
def save_agent(agent):
    update_config(agent, request.form['model'], request.form['base_url'], request.form.get('provider','custom'), request.form.get('context_length','262144'), request.form.get('max_tokens','8192'))
    updates = {
        'HERMES_INFERENCE_PROVIDER': request.form.get('provider','custom'),
        'API_SERVER_MODEL_NAME': request.form.get('api_model') or f'hermes-{agent}',
        'API_SERVER_KEY': request.form.get('api_key') or f'hermes-{agent}-local-key',
    }
    if request.form.get('upstream_key'):
        updates['OPENAI_API_KEY'] = request.form['upstream_key']
    set_env(data_dir(agent) / '.env', updates)
    run(['docker', 'compose', 'restart', service_name(agent)], cwd=ROOT, timeout=180)
    flash(f'{agent} updated and restarted')
    return redirect(url_for('index', token=TOKEN))


@app.route('/agent/<agent>/apply-model', methods=['POST'])
def apply_model_profile(agent):
    profile = get_model_profile(request.form.get('profile_id'))
    if not profile:
        flash('Model preset not found')
        return redirect(url_for('edit_agent', agent=agent, token=TOKEN))
    apply_model_to_agent(
        agent,
        profile,
        api_model=request.form.get('api_model') or f'hermes-{agent}',
        api_key=request.form.get('api_key') or f'hermes-{agent}-local-key',
        restart=True,
    )
    flash(f'{agent} switched to {profile.get("name") or profile.get("model")} and restarted')
    return redirect(url_for('index', token=TOKEN))


@app.route('/agent/create', methods=['POST'])
def create_agent():
    agent = slugify_name(request.form['name'])
    port = request.form['port'].strip()
    api_model = request.form.get('api_model') or f'hermes-{agent}'
    api_key = request.form.get('api_key') or f'hermes-{agent}-local-key'
    ensure_initialized(agent)
    install_custom_skills(agent)
    profile = get_model_profile(request.form.get('model_profile'))
    if profile:
        update_config(
            agent,
            profile.get('model') or DEFAULT_UPSTREAM_MODEL,
            profile.get('base_url') or DEFAULT_UPSTREAM_BASE_URL,
            profile.get('provider') or 'custom',
            str(profile.get('context_length') or '262144'),
            str(profile.get('max_tokens') or '8192'),
        )
        upstream_key = profile.get('api_key') or DEFAULT_UPSTREAM_KEY or 'sk-no-key-required'
        provider = profile.get('provider') or 'custom'
    else:
        update_config(agent, request.form.get('model') or DEFAULT_UPSTREAM_MODEL, request.form.get('base_url') or DEFAULT_UPSTREAM_BASE_URL)
        upstream_key = request.form.get('upstream_key') or DEFAULT_UPSTREAM_KEY or 'sk-no-key-required'
        provider = 'custom'
    apply_loop_limits(agent)
    set_env(data_dir(agent) / '.env', {
        'OPENAI_API_KEY': upstream_key,
        'HERMES_INFERENCE_PROVIDER': provider,
        'HERMES_API_TIMEOUT': '1800',
        'API_SERVER_ENABLED': 'true',
        'API_SERVER_HOST': '0.0.0.0',
        'API_SERVER_PORT': '8642',
        'API_SERVER_CORS_ORIGINS': '*',
        'API_SERVER_KEY': api_key,
        'API_SERVER_MODEL_NAME': api_model,
        'GATEWAY_ALLOW_ALL_USERS': 'true',
    })
    write_soul(agent, request.form.get('soul'))
    data = compose_data(); services = data.setdefault('services', {})
    services[service_name(agent)] = {
        'image': IMAGE,
        'container_name': service_name(agent),
        'restart': 'unless-stopped',
        'command': 'gateway run',
        'ports': [f'{port}:8642'],
        'volumes': [
            f'{ROOT}/{agent}:/opt/data',
            f'{ROOT}/patches/weixin.py:/opt/hermes/gateway/platforms/weixin.py:ro',
        ],
        'shm_size': '1gb',
        'extra_hosts': ['host.docker.internal:host-gateway'],
        'environment': ['OPENAI_API_KEY=sk-no-key-required', 'HERMES_INFERENCE_PROVIDER=custom', 'GATEWAY_ALLOW_ALL_USERS=true'],
        'deploy': {'resources': {'limits': {'memory': '4G', 'cpus': '2.0'}}},
    }
    save_compose(data)
    run(['docker', 'compose', 'up', '-d', service_name(agent)], cwd=ROOT, timeout=300)
    flash(f'{agent} created')
    return redirect(url_for('index', token=TOKEN))


@app.route('/agent/<agent>/restart', methods=['POST'])
def restart_agent(agent):
    run(['docker', 'compose', 'restart', service_name(agent)], cwd=ROOT, timeout=180)
    flash(f'{agent} restarted')
    return redirect(url_for('index', token=TOKEN))

@app.route('/agent/<agent>/stop', methods=['POST'])
def stop_agent(agent):
    run(['docker', 'compose', 'stop', service_name(agent)], cwd=ROOT, timeout=180)
    flash(f'{agent} stopped')
    return redirect(url_for('index', token=TOKEN))

@app.route('/agent/<agent>/start', methods=['POST'])
def start_agent(agent):
    run(['docker', 'compose', 'up', '-d', service_name(agent)], cwd=ROOT, timeout=240)
    flash(f'{agent} started')
    return redirect(url_for('index', token=TOKEN))

@app.route('/agent/<agent>/delete', methods=['POST'])
def delete_agent(agent):
    svc = service_name(agent)
    subprocess.run(['docker', 'compose', 'stop', svc], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    subprocess.run(['docker', 'compose', 'rm', '-f', svc], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    data = compose_data(); data.get('services', {}).pop(svc, None); save_compose(data)
    if request.form.get('delete_data') == '1':
        run(['rm', '-rf', str(data_dir(agent))], timeout=60)
    flash(f'{agent} deleted')
    return redirect(url_for('index', token=TOKEN))


def bind_container_name(agent):
    return f'hermes-wechat-bind-{agent}'


def wechat_state(agent):
    path = data_dir(agent) / 'wechat-bind-state.json'
    try:
        return json.loads(path.read_text())
    except Exception:
        return {'status': 'idle', 'message': 'No active binding session'}


def binding_running(agent):
    name = bind_container_name(agent)
    try:
        out = run(['docker', 'ps', '--filter', f'name=^{name}$', '--format', '{{.Names}}'], timeout=15)
        return name in out.splitlines()
    except Exception:
        return False

@app.route('/agent/<agent>/wechat')
def wechat_agent(agent):
    state = wechat_state(agent)
    running = binding_running(agent)
    scan_data = state.get('scan_data') or state.get('qrcode_url') or state.get('qrcode') or ''
    qr_html = ''
    if scan_data and state.get('status') not in {'confirmed'}:
        qr_url = url_for('wechat_qr', agent=agent, token=TOKEN, t=state.get('updated_at', 0))
        qr_html = f'<img alt="WeChat QR" style="width:280px;height:280px;background:white;padding:10px;border-radius:8px" src="{qr_url}">'
    cmd = f"""# Optional CLI fallback
cd {ROOT}
docker compose stop {service_name(agent)}
docker rm -f {bind_container_name(agent)} 2>/dev/null || true
docker run -d --name {bind_container_name(agent)} \
  -v {ROOT}/{agent}:/opt/data \
  -v {APP_DIR}/wechat_bind.py:/opt/wechat_bind.py:ro \
  {IMAGE} python /opt/wechat_bind.py
"""
    body = f'''<section class="panel"><h2>Bind WeChat: {agent}</h2>
    <p class="muted">点击开始后，系统会停止该 agent，启动临时绑定容器，并在此页显示微信二维码。扫码确认成功后，点击 Start Agent 恢复服务。</p>
    <div class="actions">
      <form method="post" action="{url_for('wechat_start', agent=agent)}"><input type="hidden" name="token" value="{TOKEN}"><button class="primary">Start Web QR Binding</button></form>
      <form method="post" action="{url_for('wechat_stop', agent=agent)}"><input type="hidden" name="token" value="{TOKEN}"><button>Stop Binding</button></form>
      <form method="post" action="{url_for('start_agent', agent=agent)}"><input type="hidden" name="token" value="{TOKEN}"><button>Start Agent</button></form>
    </div>
    <div class="two" style="margin-top:14px"><div><h3>Status</h3><p><span class="badge {'ok' if state.get('status') == 'confirmed' else ''}">{state.get('status')}</span> {'binding container running' if running else 'binding container stopped'}</p><p>{state.get('message','')}</p><p class="muted">Account: <code>{state.get('account_id','')}</code><br>User: <code>{state.get('user_id','')}</code></p>{qr_html}</div><div><h3>Raw State</h3><pre>{json.dumps(state, ensure_ascii=False, indent=2)}</pre></div></div>
    <p class="muted">This page auto-refreshes while binding is pending.</p>
    <script>setTimeout(() => location.reload(), 3000);</script>
    <h3>CLI fallback</h3><pre>{cmd}</pre>
    </section>'''
    return render(body)


@app.route('/agent/<agent>/wechat/start', methods=['POST'])
def wechat_start(agent):
    svc = service_name(agent)
    bname = bind_container_name(agent)
    state_path = data_dir(agent) / 'wechat-bind-state.json'
    try:
        state_path.unlink()
    except FileNotFoundError:
        pass
    subprocess.run(['docker', 'compose', 'stop', svc], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    subprocess.run(['docker', 'rm', '-f', bname], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    run([
        'docker', 'run', '-d', '--name', bname,
        '-v', f'{data_dir(agent)}:/opt/data',
        '-v', f'{APP_DIR}/wechat_bind.py:/opt/wechat_bind.py:ro',
        IMAGE, 'python', '/opt/wechat_bind.py'
    ], timeout=60)
    flash(f'WeChat binding started for {agent}')
    return redirect(url_for('wechat_agent', agent=agent, token=TOKEN))


@app.route('/agent/<agent>/wechat/stop', methods=['POST'])
def wechat_stop(agent):
    subprocess.run(['docker', 'rm', '-f', bind_container_name(agent)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    flash(f'WeChat binding stopped for {agent}')
    return redirect(url_for('wechat_agent', agent=agent, token=TOKEN))


@app.route('/agent/<agent>/wechat/qr.png')
def wechat_qr(agent):
    import qrcode
    state = wechat_state(agent)
    data = state.get('scan_data') or state.get('qrcode_url') or state.get('qrcode') or ''
    if not data:
        abort(404)
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


@app.route('/models')
def models_page():
    rows = []
    for p in model_profiles():
        pid = html.escape(p.get('id', ''))
        name = html.escape(p.get('name', ''))
        provider = html.escape(p.get('provider', 'custom'))
        model = html.escape(p.get('model', ''))
        ctx = html.escape(str(p.get('context_length', '')))
        max_tokens = html.escape(str(p.get('max_tokens', '')))
        base_url = html.escape(p.get('base_url', ''))
        key = html.escape(mask_secret(str(p.get('api_key', ''))))
        test_status = p.get('test_status') if p.get('test_status') in {'ok', 'bad'} else ''
        status_title = html.escape(p.get('test_message') or 'Not tested yet')
        tested_at = p.get('tested_at')
        tested_text = f'<br><span class="muted">last test {html.escape(str(tested_at))}</span>' if tested_at else ''
        edit_url = url_for('edit_model_profile', profile_id=p.get('id', ''), token=TOKEN)
        test_url = url_for('test_model_profile_route', profile_id=p.get('id', ''))
        delete_url = url_for('delete_model_profile', profile_id=p.get('id', ''))
        rows.append(f'''<tr>
          <td><span class="traffic {test_status}" title="{status_title}"></span><strong>{name}</strong><br><span class="muted"><code>{pid}</code></span>{tested_text}</td>
          <td><code>{provider}</code></td>
          <td><code>{model}</code><br><span class="muted">ctx {ctx} / max {max_tokens}</span></td>
          <td><code>{base_url}</code><br><span class="muted">key {key}</span></td>
          <td><div class="actions"><a class="button" href="{edit_url}">Edit</a><form method="post" action="{test_url}"><input type="hidden" name="token" value="{TOKEN}"><button>Test</button></form><form method="post" action="{delete_url}" onsubmit="return confirm('Delete model preset?')"><input type="hidden" name="token" value="{TOKEN}"><button class="danger">Delete</button></form></div></td>
        </tr>''')
    table = ''.join(rows) or '<tr><td colspan="5" class="muted">No model presets yet.</td></tr>'
    body = f'''<section class="panel"><h2>Model Library</h2>
    <table class="table"><thead><tr><th>Name</th><th>Provider</th><th>Model</th><th>Endpoint</th><th></th></tr></thead><tbody>{table}</tbody></table>
    </section><div style="height:16px"></div>
    <section class="panel"><h2>Add Model Preset</h2>
    <form method="post" action="{url_for('create_model_profile')}">
      <input type="hidden" name="token" value="{TOKEN}">
      <div class="two"><label>Name<input name="name" placeholder="DashScope Qwen 3.6 Plus" required></label><label>Provider<input name="provider" value="custom"></label></div>
      <label>Base URL<input name="base_url" value="{DEFAULT_UPSTREAM_BASE_URL}" required></label>
      <div class="two"><label>Model<input name="model" value="{DEFAULT_UPSTREAM_MODEL}" required></label><label>API key<input name="api_key" type="password" placeholder="sk-..."></label></div>
      <div class="two"><label>Context length<input name="context_length" value="262144"></label><label>Max tokens<input name="max_tokens" value="8192"></label></div>
      <button class="primary">Save Model Preset</button>
    </form></section>'''
    return render(body)


@app.route('/models/create', methods=['POST'])
def create_model_profile():
    data = model_library()
    name = request.form.get('name', '').strip()
    profile = {
        'id': slugify_name(name) or secrets.token_hex(4),
        'name': name,
        'provider': request.form.get('provider') or 'custom',
        'base_url': request.form.get('base_url') or DEFAULT_UPSTREAM_BASE_URL,
        'model': request.form.get('model') or DEFAULT_UPSTREAM_MODEL,
        'api_key': request.form.get('api_key') or '',
        'context_length': request.form.get('context_length') or '262144',
        'max_tokens': request.form.get('max_tokens') or '8192',
    }
    existing = {p.get('id') for p in data.get('models', [])}
    base_id = profile['id']
    n = 2
    while profile['id'] in existing:
        profile['id'] = f'{base_id}-{n}'
        n += 1
    data.setdefault('models', []).append(profile)
    save_model_library(data)
    flash(f"Model preset {profile['name']} saved")
    return redirect(url_for('models_page', token=TOKEN))


@app.route('/models/<profile_id>/edit')
def edit_model_profile(profile_id):
    profile = get_model_profile(profile_id)
    if not profile:
        flash('Model preset not found')
        return redirect(url_for('models_page', token=TOKEN))
    body = f'''<section class="panel"><h2>Edit Model Preset</h2>
    <form method="post" action="{url_for('update_model_profile', profile_id=profile_id)}">
      <input type="hidden" name="token" value="{TOKEN}">
      <div class="two"><label>Name<input name="name" value="{html.escape(profile.get('name', ''))}" required></label><label>Provider<input name="provider" value="{html.escape(profile.get('provider', 'custom'))}"></label></div>
      <label>Base URL<input name="base_url" value="{html.escape(profile.get('base_url', ''))}" required></label>
      <div class="two"><label>Model<input name="model" value="{html.escape(profile.get('model', ''))}" required></label><label>API key<input name="api_key" type="password" placeholder="leave blank to keep {html.escape(mask_secret(str(profile.get('api_key', ''))))}"></label></div>
      <div class="two"><label>Context length<input name="context_length" value="{html.escape(str(profile.get('context_length', '262144')))}"></label><label>Max tokens<input name="max_tokens" value="{html.escape(str(profile.get('max_tokens', '8192')))}"></label></div>
      <div class="actions"><button class="primary">Save Changes</button><a class="button" href="{url_for('models_page', token=TOKEN)}">Cancel</a></div>
    </form></section>'''
    return render(body)


@app.route('/models/<profile_id>/update', methods=['POST'])
def update_model_profile(profile_id):
    data = model_library()
    for profile in data.get('models', []):
        if profile.get('id') == profile_id:
            profile['name'] = request.form.get('name') or profile.get('name', '')
            profile['provider'] = request.form.get('provider') or 'custom'
            profile['base_url'] = request.form.get('base_url') or DEFAULT_UPSTREAM_BASE_URL
            profile['model'] = request.form.get('model') or DEFAULT_UPSTREAM_MODEL
            if request.form.get('api_key'):
                profile['api_key'] = request.form.get('api_key')
            profile['context_length'] = request.form.get('context_length') or '262144'
            profile['max_tokens'] = request.form.get('max_tokens') or '8192'
            profile.pop('test_status', None)
            profile.pop('test_message', None)
            profile.pop('tested_at', None)
            save_model_library(data)
            flash(f"Model preset {profile['name']} updated")
            return redirect(url_for('models_page', token=TOKEN))
    flash('Model preset not found')
    return redirect(url_for('models_page', token=TOKEN))


@app.route('/models/<profile_id>/test', methods=['POST'])
def test_model_profile_route(profile_id):
    profile = get_model_profile(profile_id)
    if not profile:
        flash('Model preset not found')
        return redirect(url_for('models_page', token=TOKEN))
    try:
        status, body = test_model_connection(profile)
        message = f"HTTP {status}, {profile.get('model')} responded"
        set_model_test_status(profile_id, 'ok', message)
        flash(f"Test OK: {message}", 'ok')
    except Exception as e:
        message = str(e)
        set_model_test_status(profile_id, 'bad', message)
        flash(f"Test failed: {message}", 'bad')
    return redirect(url_for('models_page', token=TOKEN))


@app.route('/models/<profile_id>/delete', methods=['POST'])
def delete_model_profile(profile_id):
    data = model_library()
    before = len(data.get('models', []))
    data['models'] = [p for p in data.get('models', []) if p.get('id') != profile_id]
    save_model_library(data)
    flash('Model preset deleted' if len(data['models']) != before else 'Model preset not found')
    return redirect(url_for('models_page', token=TOKEN))


@app.route('/agent/<agent>/logs')
def agent_logs(agent):
    out = subprocess.run(['docker', 'logs', '--tail', '240', service_name(agent)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
    body = f'<section class="panel"><h2>Logs: {agent}</h2><pre>{out}</pre></section>'
    return render(body)

@app.route('/logs')
def logs():
    out = run(['docker', 'compose', 'ps'], cwd=ROOT, timeout=30)
    body = f'<section class="panel"><h2>Compose Status</h2><pre>{out}</pre></section>'
    return render(body)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '8787')))
