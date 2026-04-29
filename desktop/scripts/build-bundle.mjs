import { execFileSync } from 'node:child_process';
import { platform } from 'node:os';

const run = (cmd, args) => {
  execFileSync(cmd, args, { stdio: 'inherit', shell: process.platform === 'win32' });
};

if (platform() === 'darwin') {
  run('npm', ['run', 'desktop:build:app']);
  run('npm', ['run', 'desktop:build:macos-dmg']);
} else if (platform() === 'win32') {
  run('npx', ['tauri', 'build', '--bundles', 'nsis']);
} else {
  run('npx', ['tauri', 'build', '--bundles', 'deb,rpm,appimage']);
}
