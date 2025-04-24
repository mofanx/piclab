import os
import tempfile
import pyclip
import keyboard
import platform
import time
import requests
from urllib.parse import urlparse
import argparse
import mimetypes
import subprocess
import shutil
import pyautogui

class ScreenshotTool:
    """多平台截图工具类"""
    
    def __init__(self, cache_dir_name='llm_ocr'):
        """初始化截图工具
        
        Args:
            cache_dir_name (str): 缓存目录名称
        """
        self.is_capturing = False
        self.system = platform.system()  # 获取操作系统类型
        
        # 获取用户缓存目录
        self.cache_dir = self._get_cache_dir(cache_dir_name)
        
        # 设置截图保存路径
        if self.cache_dir:
            self.temp_dir = self.cache_dir  # 不是临时创建的目录，所以不会在__del__中被删除
            self.screenshot_path = os.path.join(self.cache_dir, f'screenshot_{int(time.time())}.png')
        else:
            # 如果创建缓存目录失败，使用临时目录
            self.temp_dir = tempfile.mkdtemp()
            self.screenshot_path = os.path.join(self.temp_dir, 'screenshot.png')
            
    def _get_cache_dir(self, cache_dir_name):
        """根据不同操作系统获取缓存目录
        
        Args:
            cache_dir_name (str): 缓存目录名称
            
        Returns:
            str: 缓存目录路径，如果创建失败则返回None
        """
        try:
            if self.system == 'Linux':
                # Linux系统
                if hasattr(os, 'geteuid') and os.geteuid() == 0:
                    # 如果是root用户运行，获取原始用户
                    username = os.environ.get('SUDO_USER', 'root')
                    user_home = f"/home/{username}"
                else:
                    # 非root用户
                    user_home = os.path.expanduser('~')
                cache_dir = os.path.join(user_home, '.cache', cache_dir_name)
                
                # 创建目录并设置权限
                if not os.path.exists(cache_dir):
                    os.makedirs(cache_dir, exist_ok=True)
                    # 如果是root创建的目录，确保原始用户有权限
                    if hasattr(os, 'geteuid') and os.geteuid() == 0:
                        username = os.environ.get('SUDO_USER')
                        if username and username != 'root':
                            import pwd
                            uid = pwd.getpwnam(username).pw_uid
                            gid = pwd.getpwnam(username).pw_gid
                            os.chown(cache_dir, uid, gid)
                            
            elif self.system == 'Windows':
                # Windows系统
                appdata = os.environ.get('LOCALAPPDATA')
                if not appdata:
                    appdata = os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local')
                cache_dir = os.path.join(appdata, cache_dir_name)
                if not os.path.exists(cache_dir):
                    os.makedirs(cache_dir, exist_ok=True)
                    
            elif self.system == 'Darwin':
                # macOS系统
                user_home = os.path.expanduser('~')
                cache_dir = os.path.join(user_home, 'Library', 'Caches', cache_dir_name)
                if not os.path.exists(cache_dir):
                    os.makedirs(cache_dir, exist_ok=True)
            else:
                # 其他系统使用临时目录
                print(f"未知操作系统: {self.system}，使用临时目录")
                return None
                
            return cache_dir
        except Exception as e:
            print(f"创建缓存目录失败: {e}")
            return None
            
    def __del__(self):
        """清理临时文件"""
        # 清理临时文件
        if hasattr(self, 'temp_dir') and self.temp_dir and os.path.exists(self.temp_dir):
            if self.temp_dir.startswith(tempfile.gettempdir()):  # 只删除系统临时目录
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # 删除截图文件
        if hasattr(self, 'screenshot_path') and os.path.exists(self.screenshot_path):
            try:
                os.remove(self.screenshot_path)
            except Exception as e:
                print(f"删除截图文件失败: {e}")
                
    def capture_screenshot(self):
        """截取屏幕区域
        
        Returns:
            str: 截图文件路径，如果截图失败则返回None
        """
        print("正在启动截图工具...")
        try:
            if self._take_screenshot_with_system_tools():
                return self.screenshot_path
            else:
                print("截图失败，请确保安装了截图工具")
                return None
        except Exception as e:
            print(f"截图失败: {str(e)}")
            return None
    
    def _take_screenshot_with_system_tools(self):
        """使用系统工具进行截图
        
        Returns:
            bool: 截图是否成功
        """
        try:
            print("正在进行区域截图...")
            
            if self.system == 'Linux':
                return self._take_screenshot_linux()
            elif self.system == 'Windows':
                return self._take_screenshot_windows()
            elif self.system == 'Darwin':
                return self._take_screenshot_macos()
            else:
                print(f"不支持的操作系统: {self.system}")
                return False
        except Exception as e:
            print(f"截图失败: {str(e)}")
            return False
            
    def _take_screenshot_linux(self):
        """Linux系统下的截图方法
        
        Returns:
            bool: 截图是否成功
        """
        try:
            # 检查是否安装了gnome-screenshot
            if not shutil.which('gnome-screenshot'):
                print("错误：未安装gnome-screenshot工具")
                return False
                
            # 检查是否是root用户运行
            if hasattr(os, 'geteuid') and os.geteuid() == 0:
                # 获取当前用户的DISPLAY和XAUTHORITY环境变量
                current_user = os.environ.get('SUDO_USER')
                user_home = f"/home/{current_user}" if current_user else os.path.expanduser('~')
                display = os.environ.get('DISPLAY', ':0')
                xauthority = os.environ.get('XAUTHORITY', f"{user_home}/.Xauthority")
                
                # 使用su命令以原用户身份运行gnome-screenshot
                cmd = f"DISPLAY={display} XAUTHORITY={xauthority} gnome-screenshot -a -f {self.screenshot_path}"
                subprocess.run(['su', current_user, '-c', cmd], check=True)
            else:
                # 非root用户直接运行
                subprocess.run(['gnome-screenshot', '-a', '-f', self.screenshot_path], check=True)

            return self._wait_for_screenshot()
        except subprocess.CalledProcessError as e:
            print(f"gnome-screenshot截图失败: {e}")
            return False
        except Exception as e:
            print(f"Linux截图失败: {str(e)}")
            return False
            
    def _take_screenshot_windows(self):
        """Windows系统下的截图方法
        
        Returns:
            bool: 截图是否成功
        """
        try:
            # 使用PIL和pyautogui进行截图
            try:
                from PIL import ImageGrab
                import pyautogui
            except ImportError:
                print("错误：未安装必要的库，请运行以下命令安装：")
                print("pip install pillow pyautogui")
                return False
                
            # 提示用户按下回车键开始截图
            print("请按下回车键开始截图，然后拖动鼠标选择区域...")
            input()
            
            # 记录鼠标初始位置
            start_x, start_y = pyautogui.position()
            print("请拖动鼠标并点击以选择区域...")
            
            # 等待鼠标点击
            pyautogui.mouseDown()
            while pyautogui.mouseIsDown():
                time.sleep(0.1)
                
            # 获取结束位置
            end_x, end_y = pyautogui.position()
            
            # 确保坐标正确（左上角到右下角）
            left = min(start_x, end_x)
            top = min(start_y, end_y)
            right = max(start_x, end_x)
            bottom = max(start_y, end_y)
            
            # 截取屏幕区域
            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
            screenshot.save(self.screenshot_path)
            
            return self._wait_for_screenshot()
        except Exception as e:
            print(f"Windows截图失败: {str(e)}")
            return False
            
    def _take_screenshot_macos(self):
        """macOS系统下的截图方法
        
        Returns:
            bool: 截图是否成功
        """
        try:
            # 使用macOS自带的screencapture工具
            subprocess.run(['screencapture', '-i', self.screenshot_path], check=True)
            return self._wait_for_screenshot()
        except subprocess.CalledProcessError as e:
            print(f"macOS截图失败: {e}")
            return False
        except Exception as e:
            print(f"macOS截图失败: {str(e)}")
            return False
            
    def _wait_for_screenshot(self):
        """等待截图文件生成
        
        Returns:
            bool: 截图文件是否生成成功
        """
        timeout = 10  # 设置超时时间（秒）
        start_time = time.time()
        while not os.path.exists(self.screenshot_path) or os.path.getsize(self.screenshot_path) == 0:
            if time.time() - start_time > timeout:
                print("截图超时")
                return False
            time.sleep(0.5)
            
        print(f"截图文件已生成: {self.screenshot_path}")
        return True


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

        # 调试输出
        # print(f"[调试] 当前API上传地址: {args.api_url}")
        # print(f"[调试] 当前API密钥: {args.api_key}")
        
        uploader = cls(args.api_url, args.api_key)
        try:
            if args.image:
                uploader.upload_image(args.image)
            else:
                image_path_or_url = cls.get_clipboard_image_or_url()
                uploader.upload_image(image_path_or_url)
        except Exception as e:
            print(f"上传失败: {e}")

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
        print(f"[通知] {title}: {message}")

def screenshot_and_upload_piclab():
    """
    截图后自动上传到 Piclab 图床，并将 Markdown 链接复制到剪贴板
    """
    # 截图
    tool = ScreenshotTool(cache_dir_name='piclab_upload')
    screenshot_path = tool.capture_screenshot()
    if not screenshot_path or not os.path.exists(screenshot_path):
        print("截图失败，未生成图片")
        send_system_notification("截图失败", "未生成图片")
        return
    # 上传
    api_url = os.getenv('PICLAB_API_URL', 'http://localhost:3000/api/upload')
    api_key = os.getenv('PICLAB_API_KEY', 'your_api_key1')
    uploader = PiclabUploader(api_url, api_key)
    try:
        uploader.upload_image(screenshot_path)
        send_system_notification("截图上传成功", "Markdown链接已复制到剪贴板")
    except Exception as e:
        print(f"截图上传失败: {e}")
        send_system_notification("截图上传失败", str(e))
    finally:
        if os.path.exists(screenshot_path):
            try:
                os.remove(screenshot_path)
            except Exception:
                pass

# 可选：直接注册快捷键（也可在主程序注册）
def run_on_hotkey():
    keyboard.add_hotkey('f8+o', screenshot_and_upload_piclab)
    print('已绑定快捷键 F8+O，截图后自动上传到 Piclab 图床')

if __name__ == '__main__':
    run_on_hotkey()
    keyboard.wait('esc')