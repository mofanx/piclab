require('dotenv').config();
const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const slugify = require('slugify');
const cors = require('cors');

const app = express();
// 添加跨域支持
app.use(cors());
const PORT = process.env.PORT || 3000;
const IMAGE_DOMAIN = process.env.IMAGE_DOMAIN || 'http://localhost:3000';
const UPLOAD_DIR = process.env.UPLOAD_DIR || 'uploads';
const API_KEYS = (process.env.API_KEYS || '').split(',').map(k => k.trim()).filter(Boolean);

// 认证中间件
function apiKeyAuth(req, res, next) {
  const auth = req.headers['authorization'];
  if (!auth || !auth.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing or invalid Authorization header' });
  }
  const key = auth.replace('Bearer ', '').trim();
  if (!API_KEYS.includes(key)) {
    return res.status(403).json({ error: 'Invalid API key' });
  }
  next();
}

// 存储配置
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const dir = path.join(UPLOAD_DIR, `${year}`, `${month}`);
    fs.mkdirSync(dir, { recursive: true });
    cb(null, dir);
  },
  filename: function (req, file, cb) {
    const now = new Date();
    const timestamp = now.toISOString().replace(/[-T:.Z]/g, '').slice(0, 14);
    const ext = path.extname(file.originalname);
    let base = path.basename(file.originalname, ext);
    // slugify 中文文件名
    base = slugify(base, { lower: true, strict: true, locale: 'zh' });
    if (!base) base = 'image';
    cb(null, `${base}_${timestamp}${ext}`);
  }
});

const upload = multer({
  storage,
  limits: { fileSize: 50 * 1024 * 1024 }, // 50MB
  fileFilter: (req, file, cb) => {
    // 仅允许图片
    if (!file.mimetype.startsWith('image/')) {
      return cb(new Error('Only image files are allowed!'));
    }
    cb(null, true);
  }
});

// 健康检查端点
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.post('/api/upload', apiKeyAuth, upload.single('file'), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded' });
  }
  // 构造图片URL
  const relPath = req.file.path.replace(/\\/g, '/');
  const url = `${IMAGE_DOMAIN}/${relPath}`;
  const markdown = `![image](${url})`;
  res.json({ 
    success: true,
    url, 
    markdown,
    filename: req.file.filename,
    size: req.file.size,
    mimetype: req.file.mimetype
  });
});

// 错误处理中间件
app.use((err, req, res, next) => {
  console.error(err.stack);
  
  if (err.code === 'LIMIT_FILE_SIZE') {
    return res.status(413).json({ 
      success: false,
      error: 'File too large. Maximum size is 50MB.' 
    });
  }
  
  if (err.message === 'Only image files are allowed!') {
    return res.status(400).json({ 
      success: false,
      error: 'Only image files are allowed' 
    });
  }
  
  res.status(500).json({ 
    success: false,
    error: 'Internal server error' 
  });
});

// 静态文件服务（如需本地预览）
app.use(`/${UPLOAD_DIR}`, express.static(UPLOAD_DIR));

// 启动服务器
const server = app.listen(PORT, () => {
  console.log(`Piclab API server running at http://localhost:${PORT}`);
  console.log(`Upload directory: ${path.resolve(UPLOAD_DIR)}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
});

// 处理未捕获的异常
process.on('uncaughtException', (err) => {
  console.error('Uncaught Exception:', err);
  // 优雅关闭
  server.close(() => {
    process.exit(1);
  });
});

// 处理未处理的 promise 拒绝
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});
