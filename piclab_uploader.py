import argparse
import os
import requests
import tempfile
import pyclip
import keyboard
import platform
import subprocess
from urllib.parse import urlparse
from datetime import datetime

class PiclabUploader:
    def __init__(self, api_url=None, api_key=None):
        import os
        self.api_url = api_url or os.getenv('PICLAB_API_URL', 'http://localhost:3000/api/upload')
        self.api_key = api_key or os.getenv('PICLAB_API_KEY', 'your_api_key1')

    @staticmethod
    def send_system_notification(title, message):
        """
        跨平台桌面通知，优先支持Linux，自动处理root和非root用户。
        """
        system = platform.system()
        if system == "Linux":
            try:
                if hasattr(os, "geteuid") and os.geteuid() == 0:
                    current_user = os.environ.get('SUDO_USER')
                    if current_user:
                        user_home = f"/home/{current_user}"
                        display = os.environ.get('DISPLAY', ':0')
                        xauthority = os.environ.get('XAUTHORITY', f"{user_home}/.Xauthority")
                        cmd = f"DISPLAY={display} XAUTHORITY={xauthority} notify-send '{title}' '{message}'"
                        subprocess.run(['su', current_user, '-c', cmd], check=True)
                    else:
                        print("[通知] 无法确定实际用户，通知可能无法显示")
                else:
                    subprocess.run(['notify-send', title, message], check=True)
            except Exception as e:
                print(f"[通知] 发送系统通知失败: {e}")
        else:
            # 其它平台可扩展
            print(f"[通知] {title}: {message}")

    def upload_image(self, image_path_or_url):
        import mimetypes
        # 新增：支持 markdown 图片格式自动提取 URL
        url_from_md = self.extract_image_url(image_path_or_url)
        if url_from_md:
            image_path_or_url = url_from_md
        if self.is_url(image_path_or_url):
            file_path = self.download_image(image_path_or_url)
            remove_after = True
        else:
            file_path = image_path_or_url
            remove_after = False
        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            with open(file_path, 'rb') as f:
                files = {
                    'file': (os.path.basename(file_path), f, mime_type)
                }
                headers = {'Authorization': f'Bearer {self.api_key}'}
                resp = requests.post(self.api_url, files=files, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            markdown = data.get('markdown', '')
            if markdown:
                pyclip.copy(markdown)
                print(f"上传成功，Markdown链接已复制到剪贴板：\n{markdown}")
                self.send_system_notification("Piclab上传成功", "Markdown链接已复制到剪贴板")
                return markdown
            else:
                print("上传成功，但未返回Markdown链接。响应：", data)
                self.send_system_notification("Piclab上传成功", "未返回Markdown链接")
                return None
        except Exception as e:
            print(f"上传失败: {e}")
            print("服务器返回:", getattr(resp, 'text', '无响应内容'))
            self.send_system_notification("Piclab上传失败", str(e))
        finally:
            if remove_after and os.path.exists(file_path):
                os.remove(file_path)

    @staticmethod
    def is_url(path):
        try:
            result = urlparse(path)
            return result.scheme in ('http', 'https')
        except Exception:
            return False

    @staticmethod
    def extract_image_url(text):
        """
        支持从 markdown 图片语法中提取图片 URL，如：
        ![alt](url) 或 ![](url)
        若不是 markdown 格式，返回 None
        """
        import re
        # 匹配 ![xxx](url) 或 ![](url)
        match = re.match(r'!\[[^\]]*\]\((https?://[^\)]+)\)', text.strip())
        if match:
            return match.group(1)
        return None

    @staticmethod
    def download_image(url):
        resp = requests.get(url, stream=True)
        resp.raise_for_status()
        suffix = os.path.splitext(urlparse(url).path)[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in resp.iter_content(chunk_size=8192):
                tmp.write(chunk)
            return tmp.name
    
    @staticmethod
    def get_clipboard_image_or_url():
        val = pyclip.paste()
        if isinstance(val, bytes):
            val = val.decode('utf-8', errors='ignore')
        val = val.strip()
        # 新增：支持 markdown 图片格式自动提取 URL
        url_from_md = PiclabUploader.extract_image_url(val)
        if url_from_md:
            return url_from_md
        if val.startswith('http://') or val.startswith('https://'):
            return val
        if os.path.exists(val):
            return val
        raise ValueError('剪贴板内容不是有效的本地图片路径或网络图片地址')

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Piclab 图床上传工具')
        parser.add_argument('image', nargs='?', help='本地图片路径或网络图片地址')
        parser.add_argument('--api-url', default=os.getenv('PICLAB_API_URL', 'http://localhost:3000/api/upload'), help='API上传地址')
        parser.add_argument('--api-key', default=os.getenv('PICLAB_API_KEY', 'your_api_key1'), help='API密钥')
        args = parser.parse_args()

        uploader = cls(args.api_url, args.api_key)
        try:
            if args.image:
                markdown = uploader.upload_image(args.image)
            else:
                image_path_or_url = cls.get_clipboard_image_or_url()
                markdown = uploader.upload_image(image_path_or_url)
        except Exception as e:
            print(f"上传失败: {e}")
            markdown = None
        return markdown

    @classmethod
    def run_on_hotkey(cls, hotkey='f8+p'):
        def handler():
            try:
                cls.main()
            except Exception as e:
                print(f"快捷键上传失败: {e}")
        keyboard.add_hotkey(hotkey, handler)
        print(f'已绑定快捷键 {hotkey.upper()}，按下即可上传剪贴板图片或图片链接...')
    
def upload_clipboard_image():
    PiclabUploader().upload_image(PiclabUploader.get_clipboard_image_or_url())


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and not (len(sys.argv) == 2 and sys.argv[1].startswith('-')):
        # 用法1：命令行上传
        PiclabUploader.main()
    else:
        # 用法2：绑定快捷键上传，仅供参考
        PiclabUploader.run_on_hotkey('f8+p')
        import keyboard
        keyboard.wait('esc+f9')  # 按下 Esc+F9 退出

