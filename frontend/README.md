# URL Shortener Frontend

React-based frontend for URL shortening service.

## Features

- ✅ Clean, modern UI
- ✅ QR code generation
- ✅ Click analytics visualization
- ✅ Responsive design
- ✅ Error handling

## Setup

```bash
# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your backend URL

# Run development server
npm start

# Build for production
npm run build
```

## Environment Variables

- `REACT_APP_API_URL` - Backend API URL (default: http://localhost:8000/api)
- `REACT_APP_BASE_URL` - Base URL for short links
- `REACT_APP_ENABLE_QR_CODE` - Enable QR code feature

## Scripts

- `npm start` - Development server (port 3000)
- `npm run build` - Production build
- `npm test` - Run tests

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Deployment

### Static Hosting (S3 + CloudFront)

```bash
# Build
npm run build

# Deploy to S3
aws s3 sync build/ s3://your-bucket --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id YOUR_ID --paths "/*"
```

## License

MIT