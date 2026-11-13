export default {
  '/datafeeder-backend': {
    target: 'http://localhost:8000/',
    rewrite: (path) => path.replace(/^\/datafeeder-backend/, ''),
    secure: false,
    changeOrigin: true,
    logLevel: 'debug'
  }
}
