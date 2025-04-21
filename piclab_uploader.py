import argparse
import os
import requests
import tempfile
import pyclip
import keyboard
from urllib.parse import urlparse
from datetime import datetime

class PiclabUploader:
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.api_key = api_key

    def upload_image(self, image_path_or_url):
        import mimetypes
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
            else:
                print("上传成功，但未返回Markdown链接。响应：", data)
        except Exception as e:
            print(f"上传失败: {e}")
            print("服务器返回:", getattr(resp, 'text', '无响应内容'))
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
                uploader.upload_image(args.image)
            else:
                image_path_or_url = cls.get_clipboard_image_or_url()
                uploader.upload_image(image_path_or_url)
        except Exception as e:
            print(f"上传失败: {e}")

# 快捷键绑定功能

def run_on_hotkey():
    def handler():
        try:
            PiclabUploader.main()
        except Exception as e:
            print(f"快捷键上传失败: {e}")
    keyboard.add_hotkey('f8+t', handler)
    print('已绑定快捷键 F8+T，按下即可上传剪贴板图片或图片链接...')
    keyboard.wait()

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and not (len(sys.argv) == 2 and sys.argv[1].startswith('-')):
        PiclabUploader.main()
    else:
        run_on_hotkey()
