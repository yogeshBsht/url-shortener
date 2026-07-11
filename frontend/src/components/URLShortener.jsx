import React, { useState } from 'react';
import { QRCodeCanvas } from 'qrcode.react';
import { shortenURL } from '../services/api';
import { downloadQRCode, shouldGenerateQROnFrontend } from '../services/qrGenerator';
import ErrorMessage from './ErrorMessage';
import LoadingSpinner from './LoadingSpinner';
import config from '../config';

const URLShortener = () => {
  const [url, setUrl] = useState('');
  const [customAlias, setCustomAlias] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [copied, setCopied] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setCopied(false);

    // Validation
    if (!url.trim()) {
      setError('Please enter a URL');
      return;
    }

    // Basic URL validation
    try {
      new URL(url);
    } catch {
      setError('Please enter a valid URL (e.g., https://example.com)');
      return;
    }

    setLoading(true);

    try {
      const data = await shortenURL(url, customAlias.trim() || null);
      setResult(data);
    } catch (err) {
      setError(err.message || 'Failed to shorten URL');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(result.short_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      setError('Failed to copy to clipboard');
    }
  };

  const handleReset = () => {
    setUrl('');
    setCustomAlias('');
    setResult(null);
    setError(null);
    setCopied(false);
  };

  const qrCodeData = result?.qr_code || (shouldGenerateQROnFrontend() && result ? result.short_url : null);

  return (
    <div className="url-shortener">
      <div className="shortener-header">
        <h1>🔗 URL Shortener</h1>
        <p className="subtitle">Shorten your long URLs in seconds</p>
      </div>

      {!result ? (
        <form onSubmit={handleSubmit} className="shortener-form">
          <div className="form-group">
            <label htmlFor="url">Enter your long URL</label>
            <input
              id="url"
              type="text"
              placeholder="https://example.com/very/long/url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={loading}
              className="input-primary"
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="alias">
              Custom alias (optional)
              <span className="label-hint">Letters, numbers, hyphens, underscores only</span>
            </label>
            <input
              id="alias"
              type="text"
              placeholder="my-custom-link"
              value={customAlias}
              onChange={(e) => setCustomAlias(e.target.value)}
              disabled={loading}
              className="input-secondary"
              pattern="[a-zA-Z0-9_-]+"
              maxLength={50}
            />
          </div>

          {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? (
              <>
                <LoadingSpinner size="small" message="" />
                Shortening...
              </>
            ) : (
              <>
                <svg className="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                  />
                </svg>
                Shorten URL
              </>
            )}
          </button>
        </form>
      ) : (
        <div className="result-container">
          <div className="result-success">
            <svg className="success-icon" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            <h2>URL Shortened Successfully!</h2>
          </div>

          <div className="result-card">
            <div className="result-url">
              <label>Short URL</label>
              <div className="url-display">
                <input type="text" value={result.short_url} readOnly className="url-input" />
                <button onClick={handleCopy} className="btn-copy" title="Copy to clipboard">
                  {copied ? (
                    <>
                      <svg fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                      Copied!
                    </>
                  ) : (
                    <>
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                        />
                      </svg>
                      Copy
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="result-original">
              <label>Original URL</label>
              <a href={result.original_url} target="_blank" rel="noopener noreferrer" className="original-link">
                {result.original_url}
              </a>
            </div>

            {config.enableQRCode && qrCodeData && (
              <div className="result-qr">
                <label>QR Code</label>
                <div className="qr-container">
                  {result.qr_code ? (
                    <img src={result.qr_code} alt="QR Code" className="qr-image" />
                  ) : (
                    <QRCodeCanvas
                      id="qr-code-canvas"
                      value={result.short_url}
                      size={200}
                      level="M"
                      includeMargin={true}
                    />
                  )}
                  <button
                    onClick={() => downloadQRCode(result.short_url)}
                    className="btn-download"
                  >
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                    Download QR Code
                  </button>
                </div>
              </div>
            )}
          </div>

          <button onClick={handleReset} className="btn-secondary">
            Shorten Another URL
          </button>
        </div>
      )}
    </div>
  );
};

export default URLShortener;