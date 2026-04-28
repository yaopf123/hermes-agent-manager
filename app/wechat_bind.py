import asyncio
import json
import os
import time
from pathlib import Path

from gateway.platforms import weixin as wx

HOME = Path(os.environ.get('HERMES_HOME', '/opt/data'))
STATE = HOME / 'wechat-bind-state.json'
ENV = HOME / '.env'
BOT_TYPE = os.environ.get('WEIXIN_BOT_TYPE', '3')
TIMEOUT = int(os.environ.get('WEIXIN_BIND_TIMEOUT', '600'))
DM_POLICY = os.environ.get('WEIXIN_DM_POLICY_DEFAULT', 'open')
GROUP_POLICY = os.environ.get('WEIXIN_GROUP_POLICY_DEFAULT', 'disabled')


def write_state(**kwargs):
    current = {}
    if STATE.exists():
        try:
            current = json.loads(STATE.read_text())
        except Exception:
            current = {}
    current.update(kwargs)
    current['updated_at'] = time.time()
    STATE.write_text(json.dumps(current, ensure_ascii=False, indent=2))


def set_env(updates):
    lines = ENV.read_text().splitlines() if ENV.exists() else []
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
    out.append('')
    out.append('# Weixin configured by Hermes Manager')
    for key, val in updates.items():
        if key not in seen:
            out.append(f'{key}={val}')
    ENV.write_text('\n'.join(out) + '\n')


async def main():
    HOME.mkdir(parents=True, exist_ok=True)
    write_state(status='starting', message='Fetching Weixin QR code')
    if not wx.check_weixin_requirements():
        write_state(status='error', message='Missing Weixin dependencies in container')
        return
    async with wx.aiohttp.ClientSession(trust_env=True, connector=wx._make_ssl_connector()) as session:
        try:
            qr_resp = await wx._api_get(session, base_url=wx.ILINK_BASE_URL, endpoint=f'{wx.EP_GET_BOT_QR}?bot_type={BOT_TYPE}', timeout_ms=wx.QR_TIMEOUT_MS)
        except Exception as exc:
            write_state(status='error', message=f'Failed to fetch QR code: {exc}')
            return
        qrcode_value = str(qr_resp.get('qrcode') or '')
        qrcode_url = str(qr_resp.get('qrcode_img_content') or '')
        if not qrcode_value:
            write_state(status='error', message='QR response missing qrcode')
            return
        write_state(status='waiting_scan', message='Scan this QR code in WeChat', qrcode=qrcode_value, qrcode_url=qrcode_url, scan_data=qrcode_url or qrcode_value)
        deadline = time.time() + TIMEOUT
        current_base_url = wx.ILINK_BASE_URL
        refresh_count = 0
        while time.time() < deadline:
            try:
                status_resp = await wx._api_get(session, base_url=current_base_url, endpoint=f'{wx.EP_GET_QR_STATUS}?qrcode={qrcode_value}', timeout_ms=wx.QR_TIMEOUT_MS)
            except Exception as exc:
                write_state(status='polling', message=f'Polling QR status: {exc}')
                await asyncio.sleep(1)
                continue
            status = str(status_resp.get('status') or 'wait')
            if status == 'wait':
                write_state(status='waiting_scan', message='Waiting for WeChat scan')
            elif status == 'scaned':
                write_state(status='scanned', message='Scanned. Confirm login in WeChat')
            elif status == 'scaned_but_redirect':
                redirect_host = str(status_resp.get('redirect_host') or '')
                if redirect_host:
                    current_base_url = f'https://{redirect_host}'
                write_state(status='scanned', message='Scanned. Following redirect')
            elif status == 'expired':
                refresh_count += 1
                if refresh_count > 3:
                    write_state(status='error', message='QR expired too many times. Start again')
                    return
                try:
                    qr_resp = await wx._api_get(session, base_url=wx.ILINK_BASE_URL, endpoint=f'{wx.EP_GET_BOT_QR}?bot_type={BOT_TYPE}', timeout_ms=wx.QR_TIMEOUT_MS)
                    qrcode_value = str(qr_resp.get('qrcode') or '')
                    qrcode_url = str(qr_resp.get('qrcode_img_content') or '')
                    write_state(status='waiting_scan', message='QR refreshed. Scan again', qrcode=qrcode_value, qrcode_url=qrcode_url, scan_data=qrcode_url or qrcode_value)
                except Exception as exc:
                    write_state(status='error', message=f'QR refresh failed: {exc}')
                    return
            elif status == 'confirmed':
                account_id = str(status_resp.get('ilink_bot_id') or '')
                token = str(status_resp.get('bot_token') or '')
                base_url = str(status_resp.get('baseurl') or wx.ILINK_BASE_URL)
                user_id = str(status_resp.get('ilink_user_id') or '')
                if not account_id or not token:
                    write_state(status='error', message='Confirmed, but credential payload incomplete')
                    return
                wx.save_weixin_account(str(HOME), account_id=account_id, token=token, base_url=base_url, user_id=user_id)
                set_env({
                    'WEIXIN_ACCOUNT_ID': account_id,
                    'WEIXIN_TOKEN': token,
                    'WEIXIN_BASE_URL': base_url,
                    'WEIXIN_CDN_BASE_URL': 'https://novac2c.cdn.weixin.qq.com/c2c',
                    'WEIXIN_DM_POLICY': DM_POLICY,
                    'WEIXIN_ALLOW_ALL_USERS': 'true' if DM_POLICY == 'open' else 'false',
                    'WEIXIN_ALLOWED_USERS': user_id if DM_POLICY == 'allowlist' else '',
                    'WEIXIN_GROUP_POLICY': GROUP_POLICY,
                    'WEIXIN_GROUP_ALLOWED_USERS': '',
                    'WEIXIN_HOME_CHANNEL': user_id,
                })
                write_state(status='confirmed', message='Weixin configured successfully', account_id=account_id, user_id=user_id, base_url=base_url)
                return
            await asyncio.sleep(1)
        write_state(status='timeout', message='Weixin login timed out. Start again')

if __name__ == '__main__':
    asyncio.run(main())
