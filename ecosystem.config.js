module.exports = {
  apps: [
    {
      name: 'piclab',
      script: 'index.js',
      cwd: __dirname,
      env: {
        NODE_ENV: 'production',
        PORT: process.env.PORT || 3000,
        IMAGE_DOMAIN: process.env.IMAGE_DOMAIN || 'http://localhost:3000',
        API_KEYS: process.env.API_KEYS || 'your_api_key1',
        UPLOAD_DIR: process.env.UPLOAD_DIR || 'uploads'
      },
      watch: false,
      instances: 1,
      autorestart: true,
      error_file: './logs/pm2-err.log',
      out_file: './logs/pm2-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};
