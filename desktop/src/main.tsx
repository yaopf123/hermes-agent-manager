import React, { useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { invoke } from '@tauri-apps/api/core';
import { CheckCircle2, Cloud, Copy, ExternalLink, Play, Server, Terminal, XCircle } from 'lucide-react';
import './styles.css';

type Target = 'remote' | 'local';

type DeployRequest = {
  target: Target;
  host: string;
  user: string;
  password: string;
  sudoPassword: string;
  token: string;
  publicHost: string;
  agentName: string;
  agentPort: string;
  agentApiKey: string;
  agentApiModel: string;
  upstreamBaseUrl: string;
  upstreamModel: string;
  upstreamApiKey: string;
  upstreamContextLength: string;
  pullImage: boolean;
  installDocker: string;
};

type CommandResult = {
  ok: boolean;
  code?: number | null;
  stdout: string;
  stderr: string;
};

type HealthResult = {
  ok: boolean;
  status?: number | null;
  message: string;
};

const randomToken = () => {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
};

const initial: DeployRequest = {
  target: 'remote',
  host: '192.168.1.21',
  user: 'ypf',
  password: '',
  sudoPassword: '',
  token: randomToken(),
  publicHost: '192.168.1.21',
  agentName: 'coder',
  agentPort: '8642',
  agentApiKey: 'hermes-coder-local-key',
  agentApiModel: 'hermes-coder',
  upstreamBaseUrl: 'https://coding.dashscope.aliyuncs.com/v1',
  upstreamModel: 'qwen3.6-plus',
  upstreamApiKey: '',
  upstreamContextLength: '262144',
  pullImage: true,
  installDocker: 'auto',
};

function field<K extends keyof DeployRequest>(
  form: DeployRequest,
  setForm: React.Dispatch<React.SetStateAction<DeployRequest>>,
  key: K,
) {
  return {
    value: String(form[key] ?? ''),
    onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const value = event.target.value;
      setForm((prev) => ({ ...prev, [key]: value }));
    },
  };
}

function App() {
  const [form, setForm] = useState<DeployRequest>(initial);
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState('');
  const [status, setStatus] = useState<HealthResult | null>(null);

  const managerUrl = useMemo(() => {
    const host = form.publicHost || form.host || '127.0.0.1';
    return `http://${host}:8787/?token=${form.token}`;
  }, [form.host, form.publicHost, form.token]);

  const agentUrl = useMemo(() => {
    const host = form.publicHost || form.host || '127.0.0.1';
    return `http://${host}:${form.agentPort}/v1`;
  }, [form.agentPort, form.host, form.publicHost]);

  const updateAgentName = (value: string) => {
    const slug = value.toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'coder';
    setForm((prev) => ({
      ...prev,
      agentName: slug,
      agentApiKey: `hermes-${slug}-local-key`,
      agentApiModel: `hermes-${slug}`,
    }));
  };

  const copy = async (value: string) => {
    await navigator.clipboard.writeText(value);
  };

  const deploy = async () => {
    setBusy(true);
    setStatus(null);
    setLog('Starting deployment...\n');
    try {
      const result = await invoke<CommandResult>('deploy', { req: form });
      setLog([result.stdout, result.stderr].filter(Boolean).join('\n') || 'No output.');
      if (!result.ok) {
        setStatus({ ok: false, status: result.code ?? null, message: 'Deployment failed.' });
      } else {
        setStatus({ ok: true, status: result.code ?? null, message: 'Deployment completed.' });
      }
    } catch (error) {
      setLog(String(error));
      setStatus({ ok: false, status: null, message: 'Deployment command failed.' });
    } finally {
      setBusy(false);
    }
  };

  const check = async () => {
    setBusy(true);
    try {
      const result = await invoke<HealthResult>('check_manager', { url: managerUrl });
      setStatus(result);
    } catch (error) {
      setStatus({ ok: false, status: null, message: String(error) });
    } finally {
      setBusy(false);
    }
  };

  const openManager = async () => {
    await invoke('open_url', { url: managerUrl });
  };

  return (
    <main>
      <aside>
        <div className="brand">
          <div className="mark">H</div>
          <div>
            <h1>Hermes Agent Manager</h1>
            <p>Desktop Installer</p>
          </div>
        </div>
        <nav>
          <a href="#deploy">Deploy</a>
          <a href="#model">Model</a>
          <a href="#logs">Logs</a>
        </nav>
        <section className="summary">
          <div>
            <span>Manager</span>
            <code>{managerUrl}</code>
          </div>
          <div>
            <span>Agent API</span>
            <code>{agentUrl}</code>
          </div>
        </section>
      </aside>

      <section className="content">
        <header>
          <div>
            <h2>一键安装服务端和默认 Agent</h2>
            <p>适配本机 Linux/macOS 和远程 Linux 服务器。Windows 第一版建议使用远程模式或 WSL。</p>
          </div>
          {status && (
            <div className={`pill ${status.ok ? 'ok' : 'bad'}`}>
              {status.ok ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
              {status.message}
            </div>
          )}
        </header>

        <section id="deploy" className="panel">
          <div className="section-title">
            <Server size={20} />
            <h3>部署目标</h3>
          </div>
          <div className="segmented">
            <button className={form.target === 'remote' ? 'active' : ''} onClick={() => setForm((p) => ({ ...p, target: 'remote' }))}>
              远程服务器
            </button>
            <button className={form.target === 'local' ? 'active' : ''} onClick={() => setForm((p) => ({ ...p, target: 'local' }))}>
              本机
            </button>
          </div>
          <div className="grid">
            <label>
              服务器 IP / Host
              <input {...field(form, setForm, 'host')} disabled={form.target === 'local'} />
            </label>
            <label>
              公网/局域网访问地址
              <input {...field(form, setForm, 'publicHost')} />
            </label>
            <label>
              SSH 用户
              <input {...field(form, setForm, 'user')} disabled={form.target === 'local'} />
            </label>
            <label>
              SSH 密码
              <input type="password" {...field(form, setForm, 'password')} disabled={form.target === 'local'} />
            </label>
            <label>
              sudo 密码
              <input type="password" placeholder="默认使用 SSH 密码" {...field(form, setForm, 'sudoPassword')} disabled={form.target === 'local'} />
            </label>
            <label>
              Docker 安装策略
              <select {...field(form, setForm, 'installDocker')}>
                <option value="auto">auto</option>
                <option value="true">true</option>
                <option value="false">false</option>
              </select>
            </label>
          </div>
          <label className="check">
            <input
              type="checkbox"
              checked={form.pullImage}
              onChange={(event) => setForm((prev) => ({ ...prev, pullImage: event.target.checked }))}
            />
            部署时拉取/更新 Hermes Agent Docker 镜像
          </label>
        </section>

        <section className="panel">
          <div className="section-title">
            <Cloud size={20} />
            <h3>默认 Agent</h3>
          </div>
          <div className="grid">
            <label>
              Agent 名称
              <input value={form.agentName} onChange={(event) => updateAgentName(event.target.value)} />
            </label>
            <label>
              Agent 端口
              <input {...field(form, setForm, 'agentPort')} />
            </label>
            <label>
              Agent API Model
              <input {...field(form, setForm, 'agentApiModel')} />
            </label>
            <label>
              Agent API Key
              <input {...field(form, setForm, 'agentApiKey')} />
            </label>
          </div>
        </section>

        <section id="model" className="panel">
          <div className="section-title">
            <Cloud size={20} />
            <h3>上游模型</h3>
          </div>
          <div className="grid">
            <label>
              Base URL
              <input {...field(form, setForm, 'upstreamBaseUrl')} />
            </label>
            <label>
              Model
              <input {...field(form, setForm, 'upstreamModel')} />
            </label>
            <label>
              API Key
              <input type="password" {...field(form, setForm, 'upstreamApiKey')} />
            </label>
            <label>
              Context Length
              <input {...field(form, setForm, 'upstreamContextLength')} />
            </label>
          </div>
        </section>

        <section className="toolbar">
          <button className="primary" onClick={deploy} disabled={busy}>
            <Play size={18} />
            {busy ? '运行中' : '一键部署'}
          </button>
          <button onClick={check} disabled={busy}>
            <CheckCircle2 size={18} />
            测试 Manager
          </button>
          <button onClick={openManager}>
            <ExternalLink size={18} />
            打开管理端
          </button>
          <button onClick={() => copy(managerUrl)}>
            <Copy size={18} />
            复制 Manager URL
          </button>
        </section>

        <section id="logs" className="panel log-panel">
          <div className="section-title">
            <Terminal size={20} />
            <h3>部署日志</h3>
          </div>
          <pre>{log || '点击“一键部署”后，这里会显示安装脚本输出。'}</pre>
        </section>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(<App />);
