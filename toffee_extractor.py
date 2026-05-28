import urllib.request
import urllib.error
import json
import ssl
import gzip
import time
import os
import base64
import configparser
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# ----------------- CONFIGURATION -----------------

def load_config_token():
    """Load token from config.ini file"""
    config_paths = ['config.ini', 'toffee-extractor/config.ini']
    for config_path in config_paths:
        if os.path.exists(config_path):
            try:
                config = configparser.ConfigParser()
                config.read(config_path)
                if 'TOFFEE' in config and 'TOKEN' in config['TOFFEE']:
                    token = config['TOFFEE']['TOKEN'].strip()
                    if token and token != 'YOUR_JWT_TOKEN_HERE':
                        print(f"[*] Loaded token from {config_path}")
                        return token
            except Exception as e:
                print(f"[!] Error reading {config_path}: {e}")
    return None

# Load token from config.ini first, fallback to example token
DEFAULT_TOKEN = "YOUR_JWT_TOKEN_HERE"
TOKEN = load_config_token() or DEFAULT_TOKEN

# Token storage file
TOKEN_FILE = ".toffee_token"

# Auto-refresh settings
AUTO_REFRESH_ENABLED = True
REFRESH_BEFORE_HOURS = 24  # Refresh if expiring within 24 hours
TOKEN_BACKUP_FILE = ".toffee_token_backup"

RAIL_IDS = [
    "55fdb2bedaca2de399b470fb0ce14117",  # ১. EPL & BFL Live
    "08d90cecf964eb9a5f6be2e1887066fd",  # ২. Premium Sports
    "36eff4e5ed817e63c4a0859a0e11f1d5",  # ৩. Kids & Teen
    "cceb01a3ecb01516539b0adad38c1400",  # ৪. Movies
    "be7d42854f019db42fbc22153674b888",  # ৫. Entertainment
    "911e8f640af3a8892b628714d4acc133",  # ৬. Bangla TV Mix
    "cb7ea308e7742680ea8df1aae153bc9b",  # ৭. News Channels
    "84a2451df95d2eb3d2b0d09c5fc34fb1"   # ৮. Infotainment
]

JSON_FILE = "toffee_playlist.json"
M3U_FILE = "toffee_playlist.m3u"
TOTAL_RAW_USAGE = 0
TOTAL_COMP_USAGE = 0

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 3]  # Exponential backoff delays in seconds

ctx = ssl._create_unverified_context()


def log_usage(comp_bytes, raw_bytes):
    global TOTAL_COMP_USAGE, TOTAL_RAW_USAGE
    TOTAL_COMP_USAGE += comp_bytes
    TOTAL_RAW_USAGE += raw_bytes


def get_current_bd_time():
    return datetime.now(timezone(timedelta(hours=6))).strftime("%I:%M:%S %p %d-%m-%Y")


# ============== TOKEN MANAGEMENT FUNCTIONS ==============

def decode_jwt_payload(token):
    """Decode JWT payload and return expiration time"""
    try:
        payload = token.split('.')[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        decoded = json.loads(base64.urlsafe_b64decode(payload))
        exp_timestamp = decoded.get('exp', 0)
        iat_timestamp = decoded.get('iat', 0)
        return exp_timestamp, iat_timestamp
    except Exception as e:
        print(f"  [!] JWT decode error: {e}")
        return 0, 0


def get_token_expiry_info(token):
    """Get token expiry details"""
    exp_ts, iat_ts = decode_jwt_payload(token)
    if exp_ts == 0:
        return None

    exp_time = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    remaining = exp_time - now

    return {
        'exp_time': exp_time,
        'remaining': remaining,
        'remaining_hours': remaining.total_seconds() / 3600,
        'remaining_days': remaining.days,
        'is_expired': now >= exp_time,
        'needs_refresh': remaining.total_seconds() / 3600 < REFRESH_BEFORE_HOURS
    }


def save_token(token):
    """Save token to file"""
    try:
        with open(TOKEN_FILE, 'w') as f:
            f.write(token)
        # Create backup
        with open(TOKEN_BACKUP_FILE, 'w') as f:
            f.write(token)
        print(f"  [✓] Token saved to {TOKEN_FILE}")
    except Exception as e:
        print(f"  [!] Failed to save token: {e}")


def load_token():
    """Load token from file"""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                return f.read().strip()
        except Exception:
            pass
    return None


def update_global_token(new_token):
    """Update the global TOKEN variable"""
    global TOKEN
    TOKEN = new_token
    save_token(new_token)
    print(f"  [✓] Global token updated successfully!")


def refresh_token():
    """
    Attempt to refresh the token using the refresh token from JWT
    Note: This requires proper API endpoint and credentials from Toffee
    """
    global TOKEN

    print("[*] Attempting to refresh token...")

    # Get current token info
    info = get_token_expiry_info(TOKEN)
    if info:
        print(f"    Current expiry: {info['exp_time'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"    Time remaining: ~{info['remaining_days']} days, {int(info['remaining_hours'] % 24)} hours")

    # Try to refresh using the refresh token endpoint
    # Note: Toffee's refresh endpoint may require specific authentication
    # This is a placeholder - actual implementation depends on Toffee's API

    # Extract refresh token info from current token
    try:
        payload = TOKEN.split('.')[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        decoded = json.loads(base64.urlsafe_b64decode(payload))

        refresh_token_value = decoded.get('token', '')
        subscriber_id = decoded.get('s_id', '')
        device_id = decoded.get('d_id', '')

        # Try Toffee's token refresh endpoint
        refresh_url = "https://auth-prod.services.toffeelive.com/toffee/BD/DK/token/refresh"

        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K)',
            'Authorization': f'Bearer {TOKEN}'
        }

        data = json.dumps({
            "refresh_token": refresh_token_value,
            "subscriber_id": subscriber_id,
            "device_id": device_id
        }).encode('utf-8')

        req = urllib.request.Request(refresh_url, headers=headers, data=data, method='POST')

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
                raw_data = response.read()
                if response.info().get('Content-Encoding') == 'gzip':
                    json_text = gzip.decompress(raw_data).decode('utf-8')
                else:
                    json_text = raw_data.decode('utf-8')

                result = json.loads(json_text)

                if 'access_token' in result:
                    new_token = result['access_token']
                    update_global_token(new_token)
                    return True

        except Exception as e:
            print(f"  [!] Token refresh API failed: {e}")

    except Exception as e:
        print(f"  [!] Failed to extract refresh info: {e}")

    # Fallback: Check if token needs manual update
    if info and info['needs_refresh']:
        print("\n  [!] Token expiring soon. Please update manually!")
        print(f"  [!] Current token expires: {info['exp_time'].strftime('%Y-%m-%d %H:%M:%S UTC')}")

    return False


def check_and_refresh_token():
    """Check token expiry and refresh if needed"""
    global TOKEN

    # Try to load saved token first
    saved_token = load_token()
    if saved_token:
        TOKEN = saved_token
        print(f"[*] Loaded saved token from {TOKEN_FILE}")

    # Check current token
    info = get_token_expiry_info(TOKEN)

    if not info:
        print("[!] Unable to decode token. Using provided token.")
        return

    print(f"[*] Token expires: {info['exp_time'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"[*] Time remaining: ~{info['remaining_days']} days, {int(info['remaining_hours'] % 24)} hours")

    if info['is_expired']:
        print("\n[❌] Token is EXPIRED! Please update manually.")
        return False
    elif info['needs_refresh'] and AUTO_REFRESH_ENABLED:
        print(f"\n[*] Token expiring soon (within {REFRESH_BEFORE_HOURS} hours)")
        print("[*] Attempting auto-refresh...")
        return refresh_token()

    return True


# ============== FETCH FUNCTIONS ==============

def fetch_channel_playback(channel_id):
    """Fetch playback URL for a channel with retry logic"""
    url = f"https://entitlement-prod.services.toffeelive.com/toffee/BD/DK/web/playback/{channel_id}"
    headers = {
        'authorization': f'Bearer {TOKEN}',
        'content-type': 'application/json',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K)',
        'Accept-Encoding': 'gzip'
    }
    req = urllib.request.Request(url, headers=headers, data=b'{}', method='POST')

    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=20) as response:
                raw_data = response.read()
                comp_len = len(raw_data)

                if response.info().get('Content-Encoding') == 'gzip':
                    json_text = gzip.decompress(raw_data).decode('utf-8')
                else:
                    json_text = raw_data.decode('utf-8')

                raw_len = len(json_text.encode('utf-8'))

                cookies = response.info().get_all('Set-Cookie', [])
                cookie_str = ""
                for c in cookies:
                    if "Edge-Cache-Cookie" in c:
                        cookie_str = c.split(';')[0].strip()
                        break

                return channel_id, json.loads(json_text), comp_len, raw_len, cookie_str

        except urllib.error.HTTPError as e:
            if e.code == 401:  # Unauthorized - token may be expired
                print(f"  [!] 401 Unauthorized for {channel_id} - Token may be expired!")
                return channel_id, None, 0, 0, ""
            print(f"  [!] HTTP Error {e.code} for {channel_id}, attempt {attempt + 1}/{MAX_RETRIES}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
            continue

        except urllib.error.URLError as e:
            print(f"  [!] URL Error for {channel_id}, attempt {attempt + 1}/{MAX_RETRIES}: {e.reason}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
            continue

        except Exception as e:
            print(f"  [!] Error for {channel_id}, attempt {attempt + 1}/{MAX_RETRIES}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
            continue

    return channel_id, None, 0, 0, ""


def fetch_rail(rail_id):
    """Fetch rail content with retry logic"""
    api_url = f"https://content-prod.services.toffeelive.com/toffee/BD/DK/web/rail/generic/editorial-dynamic/{rail_id}"
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
        'Accept-Encoding': 'gzip'
    }
    req = urllib.request.Request(api_url, headers=headers)

    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=20) as response:
                raw_data = response.read()
                comp_len = len(raw_data)

                if response.info().get('Content-Encoding') == 'gzip':
                    json_text = gzip.decompress(raw_data).decode('utf-8')
                else:
                    json_text = raw_data.decode('utf-8')

                raw_len = len(json_text.encode('utf-8'))
                log_usage(comp_len, raw_len)
                data = json.loads(json_text)
                return data.get('list', []), rail_id, True

        except Exception as e:
            print(f"  [!] Failed rail {rail_id}, attempt {attempt + 1}/{MAX_RETRIES}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
            continue

    return [], rail_id, False


def run():
    global TOTAL_COMP_USAGE, TOTAL_RAW_USAGE, TOKEN
    current_time = get_current_bd_time()

    print("\n" + "="*60)
    print("         TOFFEE EXTRACTOR v2.0 - AUTO TOKEN REFRESH")
    print("="*60)

    # Check and refresh token
    token_ok = check_and_refresh_token()

    if token_ok is False:
        print("\n[❌] Token check failed! Exiting.")
        return

    print(f"\n[*] Toffee Extractor Started at {current_time}")
    print("[*] Fetching Content Rails (Parallel Mode)...")

    # Collect channels
    ordered_channel_ids = []
    channel_metadata_map = {}

    # Parallel rail fetching
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_rail, rail_id): rail_id for rail_id in RAIL_IDS}

        for future in as_completed(futures):
            rail_id = futures[future]
            try:
                items, rid, success = future.result()
                if success:
                    for item in items:
                        cid = item.get('id')
                        if cid and cid != "null" and cid not in channel_metadata_map:
                            ordered_channel_ids.append(cid)
                            channel_metadata_map[cid] = item
                    print(f"  [✓] Fetched Rail: {rid}")
                else:
                    print(f"  [-] Failed Rail: {rid} (all retries exhausted)")
            except Exception as e:
                print(f"  [-] Unexpected error for rail {rail_id}: {e}")

    if not ordered_channel_ids:
        print("[-] No channels found! Exiting.")
        return

    print(f"\n[*] Found {len(ordered_channel_ids)} unique channels.")
    print("[*] Fetching live links (Safe Speed: 5 workers)...")

    playback_results = {}

    # Parallel playback fetching
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_channel_playback, cid): cid for cid in ordered_channel_ids}

        for future in as_completed(futures):
            cid = futures[future]
            try:
                channel_id, body, comp_len, raw_len, cookie = future.result()
                log_usage(comp_len, raw_len)

                if body:
                    playback_results[channel_id] = (body, cookie)
                else:
                    print(f"  [!] Warning: Skipped channel {channel_id} due to server error.")
            except Exception as e:
                print(f"  [!] Unexpected error for channel {cid}: {e}")

    # Generate output
    output_json = {
        "playlist_info": {
            "name": "Toffee Live TV Full Data",
            "telegram": "https://t.me/livesportsplay",
            "owner": "Md Sohanur Rahman Hady",
            "last_update": current_time,
            "token_expires": get_token_expiry_info(TOKEN)['exp_time'].strftime('%Y-%m-%d %H:%M:%S UTC') if get_token_expiry_info(TOKEN) else 'Unknown'
        },
        "channels": []
    }

    m3u_content = f"""#EXTM3U
# name: Toffee Live TV Full Data
# telegram: https://t.me/livesportsplay
# owner: Md Sohanur Rahman Hady
# last_update: {current_time}

"""

    successful_channels = 0
    failed_channels = 0

    for cid in ordered_channel_ids:
        if cid not in playback_results:
            failed_channels += 1
            continue

        meta = channel_metadata_map[cid]
        p_body, cookie = playback_results[cid]

        raw_logo = meta.get('images', [{}])[0].get('path', '')
        logo_url = f"https://assets-prod.services.toffeelive.com/{raw_logo}" if raw_logo else "No Logo Found"

        badge = meta.get('badge', ["Free"])
        premium_status = badge[0] if badge else "Free"

        playback_data = p_body.get('playbackDetails', {}).get('data', [{}])
        stream_url = playback_data[0].get('url', 'N/A') if playback_data else 'N/A'
        stream_format = playback_data[0].get('streaming_format', 'Unknown') if playback_data else 'Unknown'
        drm_token = p_body.get('playbackDetails', {}).get('drmToken', 'N/A')

        is_drm = stream_url == 'N/A' or drm_token != 'N/A'

        channel_data = {
            "channel_id": cid,
            "channel_name": meta.get('title', 'N/A'),
            "category": meta.get('category', ["Unknown"])[0] if meta.get('category') else "Unknown",
            "genre": meta.get('genres', ["Unknown"])[0] if meta.get('genres') else "Unknown",
            "tags": meta.get('tags', ["Unknown"])[0] if meta.get('tags') else "Unknown",
            "logo_url": logo_url,
            "is_premium": premium_status,
            "content_type": meta.get('subType', 'Live_TV'),
            "status": meta.get('v_status', 'PUBLISHED'),
            "stream_url": stream_url,
            "stream_format": stream_format,
            "drm_token": drm_token,
            "has_ads": p_body.get('ads', 'no'),
            "access_status": p_body.get('access', 'denied'),
            "cookie": cookie,
            "is_drm_protected": is_drm
        }

        output_json["channels"].append(channel_data)

        if stream_url != "N/A":
            m3u_content += f'#EXTINF:-1 tvg-id="{cid}" tvg-logo="{logo_url}" group-title="{channel_data["category"]}",{channel_data["channel_name"]}\n'
            m3u_content += f'#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Linux; Android 10; K)\n'
            if cookie:
                m3u_content += f'#EXTVLCOPT:http-cookie={cookie}\n'
            m3u_content += f'{stream_url}\n\n'
            successful_channels += 1

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(output_json, f, indent=4, ensure_ascii=False)

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write(m3u_content.strip() + "\n")

    print(f"\n[✓] Completed!")
    print(f"    - Successful channels: {successful_channels}")
    print(f"    - Failed/DRM channels: {failed_channels}")
    print(f"    - Total channels in JSON: {len(output_json['channels'])}")

    print(f"\n{'='*60}")
    print(f"📊 DATA TRACKER REPORT:")
    print(f"  Total Network Download: {round(TOTAL_COMP_USAGE / 1024, 2)} KB")
    print(f"  Uncompressed Size: {round(TOTAL_RAW_USAGE / 1024, 2)} KB")
    print(f"  Token Auto-Save: {TOKEN_FILE}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run()