import requests
import base64
import time
import hashlib
import urllib3
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEVICE_ID = "98f238170000015b"
PACKAGE = "istar"
LOGIN_URL = f"https://live.istariq.com/live/v2/login?mc={DEVICE_ID}&package={PACKAGE}"

STATIC_KEY = b"T209iFeRrK2ySdk8"
STATIC_IV = b"ab0FogjEh6s9s5Wx"

MYSTAR_SECRET_KEY = "mystar2month9898"

def generate_mc_token():
    time_window = round(time.time() / 300) * 300
    secret = "c0cwHnAYTBxdXLki5xbxKzv2ojsiZG0K"
    return hashlib.sha1(f"{time_window} {secret}".encode('utf-8')).hexdigest()

def decrypt_static(encrypted_b64):
    enc_data = base64.b64decode(encrypted_b64)
    cipher = AES.new(STATIC_KEY, AES.MODE_CBC, STATIC_IV)
    return unpad(cipher.decrypt(enc_data), AES.block_size).decode('utf-8')

def decrypt_dynamic(encrypted_b64, session):
    suffix = str(session)[2:]
    key = f"5HjN18OI{suffix}".encode('utf-8')
    iv = f"g3Rt30n8{suffix}".encode('utf-8')
    
    enc_data = base64.b64decode(encrypted_b64)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(enc_data), AES.block_size).decode('utf-8')

# XOR لەسەر تێکست و پاشان Base64 بۆ پاراستنی سەد لە سەدی
def text_xor_encrypt(text, key_string):
    text_bytes = text.encode('utf-8')
    key_bytes = key_string.encode('utf-8')
    encrypted_bytes = bytearray()
    
    for i in range(len(text_bytes)):
        encrypted_bytes.append(text_bytes[i] ^ key_bytes[i % len(key_bytes)])
        
    return base64.b64encode(encrypted_bytes).decode('utf-8')

def main():
    headers = {
        "user-agent": "Dart/3.5 (dart:io)",
        "x-device-model": "samsung | a71naxx",
        "accept-encoding": "gzip",
        "host": "live.istariq.com",
        "x-device-id": DEVICE_ID,
        "x-app-package-name": "com.istargroups.istarmedialive",
        "x-app-version": "2.0.20",
        "x-app-platform": "android",
        "x-language": "fa"
    }
    
    max_attempts = 5
    
    for attempt in range(1, max_attempts + 1):
        try:
            login_res = requests.get(LOGIN_URL, headers=headers, verify=False, timeout=15).json()
            session = login_res.get("payload", {}).get("session")
            
            if not session:
                time.sleep(5)
                continue

            enc_download_v2 = login_res["payload"]["channels"][0]["download-v2"]
            category_url = decrypt_static(enc_download_v2)
            
            cat_headers = {
                "session": str(session),
                "mc": generate_mc_token(),
                "user-agent": "Dart/3.5 (dart:io)",
                "x-device-model": "samsung | a71naxx",
                "x-device-id": DEVICE_ID,
                "x-app-package-name": "com.istargroups.istarmedialive",
                "x-app-version": "2.0.20",
                "x-app-platform": "android",
                "X-Forwarded-For": "37.236.14.15"
            }
            
            channels_response = requests.get(category_url, headers=cat_headers, verify=False, timeout=15).json()
            
            if isinstance(channels_response, dict) and "message" in channels_response:
                time.sleep(5)
                continue
                
            channels = channels_response
            m3u_content = "#EXTM3U\n"
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            m3u_content += f"# Last Updated: {current_time}\n"

            for i, channel in enumerate(channels, 1):
                if not isinstance(channel, dict):
                    continue
                    
                name = channel.get("name", f"Channel {i}")
                icon = channel.get("icon", "")
                prefix = channel.get("prefix")
                channel_url = channel.get("channel_url")
                
                if not prefix or not channel_url:
                    continue
                    
                try:
                    decrypted_content = decrypt_dynamic(prefix, session)
                    if decrypted_content.startswith("?"):
                        balancer_url = f"{channel_url}{decrypted_content}"
                    elif decrypted_content.startswith("content="):
                        balancer_url = f"{channel_url}?{decrypted_content}"
                    else:
                        balancer_url = f"{channel_url}?content={decrypted_content}"
                        
                    m3u_content += f'#EXTINF:-1 tvg-logo="{icon}",{name}\n'
                    m3u_content += f"{balancer_url}\n"
                except Exception as e:
                    continue
            
            # ئاڵۆزکردن بە Text XOR و Base64
            encrypted_text = text_xor_encrypt(m3u_content, MYSTAR_SECRET_KEY)
            
            with open("mystar_playlist.enc", "w", encoding="utf-8") as f:
                f.write(encrypted_text)
                    
            return 
            
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    main()
