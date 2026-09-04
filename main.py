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
    
    print("[1] Logging in...")
    login_res = requests.get(LOGIN_URL, headers=headers, verify=False).json()
    session = login_res.get("payload", {}).get("session")
    
    enc_download_v2 = login_res["payload"]["channels"][0]["download-v2"]
    category_url = decrypt_static(enc_download_v2)
    
    cat_headers = {
        "session": str(session),
        "mc": generate_mc_token(),
        "User-Agent": "Dart/3.5 (dart:io)"
    }
    
    print("[2] Fetching all channels...")
    channels = requests.get(category_url, headers=cat_headers, verify=False).json()
    total_channels = len(channels)
    print(f"[+] Found {total_channels} channels. Starting extraction...\n")
    
    # دروستکردنی فایلی M3U
    with open("istar_playlist.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        for i, channel in enumerate(channels, 1):
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
                
                # وەرگرتنی لینکی کۆتایی لە باڵانسەر
                bal_res = requests.get(balancer_url, headers=cat_headers, allow_redirects=False, verify=False)
                m3u8_link = bal_res.headers.get("Location")
                
                if m3u8_link:
                    print(f"[{i}/{total_channels}] ✔️ {name}")
                    # نووسینی ناو و لۆگۆ و لینکەکە لەناو فایلەکەدا
                    f.write(f'#EXTINF:-1 tvg-logo="{icon}",{name}\n')
                    f.write(f"{m3u8_link}\n")
                else:
                    print(f"[{i}/{total_channels}] ❌ Failed: {name}")
                
                # پشوویەکی زۆر بچووک بۆ ئەوەی سێرڤەرەکە بلۆکمان نەکات
                time.sleep(0.1)
                
            except Exception as e:
                print(f"[{i}/{total_channels}] ⚠️ Error on {name}: {e}")
                
    print("\n" + "="*50)
    print("🎉 SUCCESS! All channels saved to 'istar_playlist.m3u'")
    print("="*50)

if __name__ == "__main__":
    main()
