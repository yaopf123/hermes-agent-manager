# Security Notes

Hermes Manager can create, stop, delete, and restart Docker containers. Treat access to the web UI as privileged server access.

Recommendations:

- Use a long random `HERMES_MANAGER_TOKEN`.
- Keep the service on a trusted LAN, VPN, or behind a reverse proxy with authentication.
- Do not commit real model API keys.
- Store large Docker image archives in GitHub Releases or private object storage, not in git.
