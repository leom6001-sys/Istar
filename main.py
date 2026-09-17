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

# کلیلە نهێنییەکەی خۆت بۆ پاراستنی فایلەکە لە Reqable
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

# فەنکشنی ئاڵۆزکردن (XOR) بۆ پاراستنی ماک ئەدرێس و لینکەکان
def xor_encrypt(data_bytes, key_string):
    key_bytes = key_string.encode('utf-8')
    key_length = len(key_bytes)
    encrypted_bytes = bytearray()
    
    for i in range(len(data_bytes)):
        encrypted_bytes.append(data_bytes[i] ^ key_bytes[i % key_length])
        
    return encrypted_bytes

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
        print(f"\n[!] Attempt {attempt} of {max_attempts}...")
        
        try:
            print("[1] Logging in...")
            login_res = requests.get(LOGIN_URL, headers=headers, verify=False, timeout=15).json()
            session = login_res.get("payload", {}).get("session")
            
            if not session:
                print("Login failed! Could not get session. Retrying...")
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
            
            print("[2] Fetching all channels...")
            channels_response = requests.get(category_url, headers=cat_headers, verify=False, timeout=15).json()
            
            if isinstance(channels_response, dict) and "message" in channels_response:
                print("Server Response:", channels_response)
                print("Error: Server still blocking the request. Retrying...")
                time.sleep(5)
                continue
                
            channels = channels_response
            total_channels = len(channels)
            print(f"[+] Found {total_channels} channels. Starting extraction and encryption...\n")
            
            # دروستکردنی فایلەکە لەناو مێشکی پایتۆن (بەبێ سەیڤکردن وەک تێکست)
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
                    print(f"Error decrypting channel {name}: {e}")
                    continue
            
            print("[3] Encrypting playlist with XOR...")
            # ئاڵۆزکردنی تەواوی لیستەکە
            encrypted_data = xor_encrypt(m3u_content.encode('utf-8'), MYSTAR_SECRET_KEY)
            
            print("[4] Saving encrypted file...")
            # سەیڤکردنی فایلە ئاڵۆزەکە بە ناوی نوێ
            with open("mystar_playlist.enc", "wb") as f:
                f.write(encrypted_data)
                    
            print("\n[+] Successfully generated and encrypted 'mystar_playlist.enc'")
            return 
            
        except Exception as e:
            print(f"Network error or timeout: {e}. Retrying...")
            time.sleep(5)
            
    print("\n[x] All 5 attempts failed.")

if __name__ == "__main__":
    main()
