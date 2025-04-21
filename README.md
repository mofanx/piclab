# Piclab 简易图床 API

## 功能简介
- 通过 API 上传图片，支持密钥认证
- 按年月自动分文件夹存储
- 文件名自动转码、加时间戳，避免重复
- 返回 Markdown 图片链接，域名可配置
- 支持中文文件名

## 快速开始

1. 安装依赖

推荐使用 pnpm（更快更节省空间）：

```bash
pnpm install
```

如未安装 pnpm，可用 npm：

```bash
npm install
```

2. 配置环境变量

复制 `.env.example` 为 `.env` 并修改：

```
IMAGE_DOMAIN=https://img.example.com
API_KEYS=your_api_key1,your_api_key2
UPLOAD_DIR=uploads
PORT=3000
```

3. 启动服务

使用 pm2 推荐方式（生产环境）：

```bash
pm2 start ecosystem.config.js
```

开发环境可用 npm/pnpm：

```bash
npm start
# 或
pnpm start
```

4. 上传图片

### 方式一：curl 命令行

```bash
curl -H "Authorization: Bearer your_api_key1" -F "file=@本地图片路径.jpg" http://localhost:3000/api/upload
```

### 方式二：Python 脚本（piclab_uploader.py）

- 依赖安装（建议激活 base 环境后）：
  ```bash
  mamba install pyclip keyboard requests
  ```
- 上传本地图片：
  ```bash
  python piclab_uploader.py /path/to/your.jpg --api-key your_api_key1
  ```
- 上传网络图片：
  ```bash
  python piclab_uploader.py https://img.xxx.com/xxx.jpg --api-key your_api_key1
  ```
- 无参数时自动读取剪贴板内容（本地路径或图片URL）：
  ```bash
  python piclab_uploader.py
  ```
- 绑定快捷键（F8+P），按下后自动上传剪贴板图片或链接：
  ```bash
  python piclab_uploader.py
  # 按 F8+P 即可自动上传
  ```

### 方式三：截图并上传（screenshot_piclab_uploader.py）

- 依赖安装：
  ```bash
  mamba install pyclip keyboard requests pyautogui
  # Linux 桌面还需安装截图工具，如 flameshot、scrot、gnome-screenshot 等
  ```
- 运行脚本后，按 F8+O 自动截图并上传，Markdown 链接自动复制到剪贴板。
  ```bash
  python screenshot_piclab_uploader.py
  # 按 F8+O 区域截图并上传
  # 按 Esc 退出监听
  ```

返回示例：
```
{
  "url": "https://img.example.com/2025/04/xxx_20250420190000.jpg",
  "markdown": "![image](https://img.example.com/2025/04/xxx_20250420190000.jpg)"
}
```

## 依赖说明
- Node.js
- express
- multer
- slugify
- dotenv

---

## API Key 批量生成脚本

可用 `gen_api_keys.py` 快速生成高强度 API Key，直接复制到 .env 文件：
```bash
python gen_api_keys.py 3
# 输出示例：API_KEYS=key1,key2,key3
```

如需扩展支持云存储、图片压缩等，可在此基础上修改。
