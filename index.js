require('dotenv').config();
const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const slugify = require('slugify');
const crypto = require('crypto');
const cors = require('cors');
const mime = require('mime-types');

const app = express();
// 添加跨域支持
app.use(cors());
app.use(express.json({ limit: '60mb' }));
app.use(express.urlencoded({ extended: true, limit: '60mb' }));
const PORT = process.env.PORT || 3000;
const IMAGE_DOMAIN = process.env.IMAGE_DOMAIN || 'http://localhost:3000';
const UPLOAD_DIR = process.env.UPLOAD_DIR || 'uploads';
const API_KEYS = (process.env.API_KEYS || '').split(',').map(k => k.trim()).filter(Boolean);
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB，适用于文件和 base64
const FILE_FIELD_NAME = 'file';
const BASE64_FIELD_CANDIDATES = ['base64', 'fileBase64', 'data'];
const BODY_MIMETYPE_FIELDS = ['mimeType', 'mimetype', 'contentType', 'type'];
const BODY_FILENAME_FIELDS = ['filename', 'name', 'fileName'];
const fsp = fs.promises;

function buildUploadContext(now = new Date()) {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const relDir = path.join(`${year}`, `${month}`);
  const dir = path.join(UPLOAD_DIR, relDir);
  fs.mkdirSync(dir, { recursive: true });
  return { dir, relDir, now };
}

function getOrCreateRequestContext(req) {
  if (!req._uploadContext) {
    req._uploadContext = buildUploadContext();
  }
  return req._uploadContext;
}

function ensureExtension(ext) {
  if (!ext) return '';
  return ext.startsWith('.') ? ext : `.${ext}`;
}

function generateStoredFilename(originalName = 'image', options = {}) {
  const now = options.now || new Date();
  const extOverride = ensureExtension(options.extOverride || '');
  const inferredExt = extOverride || path.extname(originalName) || '.bin';
  let base = path.basename(originalName, inferredExt) || 'image';
  base = slugify(base, { lower: true, strict: true, locale: 'zh' });
  if (!base) base = 'image';
  const timestamp = now.toISOString().replace(/[-T:.Z]/g, '');
  const randomSuffix = crypto.randomBytes(4).toString('hex');
  return `${base}_${randomSuffix}_${timestamp}${inferredExt}`;
}

function resolveBase64String(body = {}) {
  for (const key of BASE64_FIELD_CANDIDATES) {
    if (typeof body[key] === 'string' && body[key].trim()) {
      return body[key].trim();
    }
  }
  return null;
}

function pickFirstString(body = {}, fields = []) {
  for (const key of fields) {
    if (typeof body[key] === 'string' && body[key].trim()) {
      return body[key].trim();
    }
  }
  return undefined;
}

function normalizeBase64Payload(data) {
  const trimmed = data.replace(/\s/g, '');
  if (!trimmed) {
    throw new Error('INVALID_BASE64');
  }
  let normalized = trimmed.replace(/-/g, '+').replace(/_/g, '/');
  const remainder = normalized.length % 4;
  if (remainder) {
    normalized = normalized.padEnd(normalized.length + (4 - remainder), '=');
  }
  return normalized;
}

function decodeBase64Payload(raw, declaredMimeType) {
  if (typeof raw !== 'string') {
    throw new Error('INVALID_BASE64');
  }
  let input = raw.trim();
  let inlineMime = null;
  const dataUrlMatch = input.match(/^data:([^;]+);base64,(.+)$/i);
  if (dataUrlMatch) {
    inlineMime = dataUrlMatch[1];
    input = dataUrlMatch[2];
  }
  const normalized = normalizeBase64Payload(input);
  const buffer = Buffer.from(normalized, 'base64');
  if (!buffer.length) {
    throw new Error('INVALID_BASE64');
  }
  const reEncoded = buffer.toString('base64').replace(/=+$/, '');
  const normalizedComparable = normalized.replace(/=+$/, '');
  if (reEncoded !== normalizedComparable) {
    throw new Error('INVALID_BASE64');
  }
  const mimeType = (declaredMimeType || inlineMime || '').toLowerCase();
  return { buffer, mimeType: mimeType || 'application/octet-stream' };
}

function buildStaticResponse(relPath, filename, size, mimetype) {
  const formattedPath = relPath.replace(/\\/g, '/');
  const url = `${IMAGE_DOMAIN}/${formattedPath}`;
  const markdown = `![image](${url})`;
  return { url, markdown, filename, size, mimetype };
}

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
    const context = getOrCreateRequestContext(req);
    cb(null, context.dir);
  },
  filename: function (req, file, cb) {
    const context = getOrCreateRequestContext(req);
    cb(null, generateStoredFilename(file.originalname, { now: context.now }));
  }
});

const upload = multer({
  storage,
  limits: { fileSize: MAX_FILE_SIZE }, // 50MB
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

app.post('/api/upload', apiKeyAuth, upload.single(FILE_FIELD_NAME), async (req, res, next) => {
  try {
    if (req.file) {
      const relPath = req.file.path.replace(/\\/g, '/');
      const response = buildStaticResponse(relPath, req.file.filename, req.file.size, req.file.mimetype);
      return res.json({ success: true, ...response });
    }

    const base64Input = resolveBase64String(req.body);
    if (!base64Input) {
      return res.status(400).json({ success: false, error: 'No file uploaded or base64 payload found' });
    }

    let decoded;
    try {
      decoded = decodeBase64Payload(base64Input, pickFirstString(req.body, BODY_MIMETYPE_FIELDS));
    } catch (err) {
      return res.status(400).json({ success: false, error: 'Invalid base64 data' });
    }

    const { buffer, mimeType } = decoded;
    if (!mimeType.startsWith('image/')) {
      return res.status(400).json({ success: false, error: 'Only image mime types are allowed' });
    }
    if (buffer.length > MAX_FILE_SIZE) {
      return res.status(413).json({ success: false, error: 'File too large. Maximum size is 50MB.' });
    }

    const mimeExt = mime.extension(mimeType);
    const extFromMime = mimeExt ? `.${mimeExt}` : '.png';
    const providedName = pickFirstString(req.body, BODY_FILENAME_FIELDS) || `image${extFromMime}`;
    const context = buildUploadContext();
    const filename = generateStoredFilename(providedName, { now: context.now, extOverride: extFromMime });
    const absolutePath = path.join(context.dir, filename);
    await fsp.writeFile(absolutePath, buffer);
    const relPath = path.join(UPLOAD_DIR, context.relDir, filename).replace(/\\/g, '/');
    const response = buildStaticResponse(relPath, filename, buffer.length, mimeType);
    return res.json({ success: true, ...response });
  } catch (error) {
    next(error);
  }
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
