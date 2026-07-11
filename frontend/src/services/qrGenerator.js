import config from '../config';

/**
 * Generate QR code on frontend (fallback if backend doesn't provide)
 * Uses qrcode.react library
 */
export const shouldGenerateQROnFrontend = () => {
  return config.enableQRCode;
};

/**
 * Download QR code as image
 */
export const downloadQRCode = (shortUrl) => {
  const canvas = document.getElementById('qr-code-canvas');
  if (!canvas) return;

  const pngUrl = canvas
    .toDataURL('image/png')
    .replace('image/png', 'image/octet-stream');

  const downloadLink = document.createElement('a');
  downloadLink.href = pngUrl;
  downloadLink.download = `qr-${shortUrl.split('/').pop()}.png`;
  document.body.appendChild(downloadLink);
  downloadLink.click();
  document.body.removeChild(downloadLink);
};