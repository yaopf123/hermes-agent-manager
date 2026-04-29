use serde::{Deserialize, Serialize};
use std::process::Command;

const DEFAULT_REPO: &str = "yaopf123/hermes-agent-manager";
const INSTALLER_URL: &str = "https://raw.githubusercontent.com/yaopf123/hermes-agent-manager/main/scripts/install-remote.sh";

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct DeployRequest {
    target: String,
    host: String,
    user: String,
    password: String,
    sudo_password: String,
    token: String,
    public_host: String,
    agent_name: String,
    agent_port: String,
    agent_api_key: String,
    agent_api_model: String,
    upstream_base_url: String,
    upstream_model: String,
    upstream_api_key: String,
    upstream_context_length: String,
    pull_image: bool,
    install_docker: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct CommandResult {
    ok: bool,
    code: Option<i32>,
    stdout: String,
    stderr: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct HealthResult {
    ok: bool,
    status: Option<u16>,
    message: String,
}

fn shell_escape(value: &str) -> String {
    if value.is_empty() {
        return "''".to_string();
    }
    let escaped = value.replace('\'', "'\"'\"'");
    format!("'{escaped}'")
}

fn env_assignment(key: &str, value: &str) -> String {
    format!("{key}={}", shell_escape(value))
}

fn build_env(req: &DeployRequest) -> Vec<String> {
    let public_host = if req.public_host.trim().is_empty() {
        req.host.trim()
    } else {
        req.public_host.trim()
    };
    vec![
        env_assignment("GITHUB_REPO", DEFAULT_REPO),
        env_assignment("HERMES_MANAGER_TOKEN", req.token.trim()),
        env_assignment("HERMES_MANAGER_PUBLIC_HOST", public_host),
        env_assignment("DEFAULT_AGENT_NAME", req.agent_name.trim()),
        env_assignment("DEFAULT_AGENT_PORT", req.agent_port.trim()),
        env_assignment("DEFAULT_AGENT_API_KEY", req.agent_api_key.trim()),
        env_assignment("DEFAULT_AGENT_API_MODEL", req.agent_api_model.trim()),
        env_assignment("UPSTREAM_BASE_URL", req.upstream_base_url.trim()),
        env_assignment("UPSTREAM_MODEL", req.upstream_model.trim()),
        env_assignment("UPSTREAM_API_KEY", req.upstream_api_key.trim()),
        env_assignment("UPSTREAM_CONTEXT_LENGTH", req.upstream_context_length.trim()),
        env_assignment("PULL_HERMES_IMAGE", if req.pull_image { "true" } else { "false" }),
        env_assignment("INSTALL_DOCKER", req.install_docker.trim()),
    ]
}

fn run_shell(script: &str) -> CommandResult {
    #[cfg(target_os = "windows")]
    let output = Command::new("powershell")
        .args(["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script])
        .output();

    #[cfg(not(target_os = "windows"))]
    let output = Command::new("bash").args(["-lc", script]).output();

    match output {
        Ok(out) => CommandResult {
            ok: out.status.success(),
            code: out.status.code(),
            stdout: String::from_utf8_lossy(&out.stdout).to_string(),
            stderr: String::from_utf8_lossy(&out.stderr).to_string(),
        },
        Err(err) => CommandResult {
            ok: false,
            code: None,
            stdout: String::new(),
            stderr: err.to_string(),
        },
    }
}

#[tauri::command]
fn deploy(req: DeployRequest) -> CommandResult {
    let envs = build_env(&req).join(" ");
    let target = req.target.trim();
    if target == "remote" {
        let host = req.host.trim();
        let user = req.user.trim();
        if host.is_empty() || user.is_empty() {
            return CommandResult {
                ok: false,
                code: None,
                stdout: String::new(),
                stderr: "Remote deployment needs host and user.".to_string(),
            };
        }
        let sudo_password = if req.sudo_password.trim().is_empty() {
            req.password.trim()
        } else {
            req.sudo_password.trim()
        };
        let remote_script = format!(
            "set -e; curl -fsSL {url} -o /tmp/hm-install-remote.sh; echo {sudo_pw} | sudo -S env {envs} bash /tmp/hm-install-remote.sh",
            url = shell_escape(INSTALLER_URL),
            sudo_pw = shell_escape(sudo_password),
            envs = envs,
        );
        if req.password.trim().is_empty() {
            let script = format!(
                "ssh -o StrictHostKeyChecking=no {}@{} {}",
                shell_escape(user).trim_matches('\''),
                shell_escape(host).trim_matches('\''),
                shell_escape(&remote_script)
            );
            return run_shell(&script);
        }
        let script = format!(
            "sshpass -p {} ssh -o StrictHostKeyChecking=no {}@{} {}",
            shell_escape(req.password.trim()),
            shell_escape(user).trim_matches('\''),
            shell_escape(host).trim_matches('\''),
            shell_escape(&remote_script)
        );
        return run_shell(&script);
    }

    #[cfg(target_os = "windows")]
    {
        return CommandResult {
            ok: false,
            code: None,
            stdout: String::new(),
            stderr: "Local install on Windows v0.1 needs WSL/Docker Desktop support. Use remote mode or install in a Linux/WSL shell for this preview.".to_string(),
        };
    }

    #[cfg(not(target_os = "windows"))]
    {
        let script = format!("curl -fsSL {} | {} bash", shell_escape(INSTALLER_URL), envs);
        run_shell(&script)
    }
}

#[tauri::command]
fn check_manager(url: String) -> HealthResult {
    let clean = url.trim();
    if clean.is_empty() {
        return HealthResult {
            ok: false,
            status: None,
            message: "Manager URL is empty.".to_string(),
        };
    }
    match ureq::get(clean).call() {
        Ok(resp) => HealthResult {
            ok: resp.status().is_success(),
            status: Some(resp.status().as_u16()),
            message: format!("HTTP {}", resp.status().as_u16()),
        },
        Err(err) => HealthResult {
            ok: false,
            status: None,
            message: err.to_string(),
        },
    }
}

#[tauri::command]
fn open_url(url: String) -> CommandResult {
    match open::that(url.trim()) {
        Ok(_) => CommandResult {
            ok: true,
            code: Some(0),
            stdout: "Opened URL.".to_string(),
            stderr: String::new(),
        },
        Err(err) => CommandResult {
            ok: false,
            code: None,
            stdout: String::new(),
            stderr: err.to_string(),
        },
    }
}

#[tauri::command]
fn command_available(name: String) -> bool {
    let script = if cfg!(target_os = "windows") {
        format!("Get-Command {} -ErrorAction SilentlyContinue", name)
    } else {
        format!("command -v {}", shell_escape(name.trim()))
    };
    run_shell(&script).ok
}

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            deploy,
            check_manager,
            open_url,
            command_available
        ])
        .run(tauri::generate_context!())
        .expect("error while running Hermes Agent Manager Desktop");
}
