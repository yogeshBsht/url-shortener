import React, { useState } from 'react';
import { getAnalytics } from '../services/api';
import ErrorMessage from './ErrorMessage';
import LoadingSpinner from './LoadingSpinner';

const Analytics = () => {
  const [shortCode, setShortCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analytics, setAnalytics] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setAnalytics(null);

    if (!shortCode.trim()) {
      setError('Please enter a short code');
      return;
    }

    setLoading(true);

    try {
      const data = await getAnalytics(shortCode.trim());
      setAnalytics(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch analytics');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="analytics">
      <div className="analytics-header">
        <h2>📊 Analytics</h2>
        <p className="subtitle">View statistics for your shortened URLs</p>
      </div>

      <form onSubmit={handleSubmit} className="analytics-form">
        <div className="form-group-inline">
          <input
            type="text"
            placeholder="Enter short code (e.g., abc123)"
            value={shortCode}
            onChange={(e) => setShortCode(e.target.value)}
            disabled={loading}
            className="input-primary"
          />
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Loading...' : 'View Stats'}
          </button>
        </div>
      </form>

      {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

      {loading && <LoadingSpinner message="Fetching analytics..." />}

      {analytics && (
        <div className="analytics-result">
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon">👥</div>
              <div className="stat-content">
                <span className="stat-label">Total Clicks</span>
                <span className="stat-value">{analytics.total_clicks.toLocaleString()}</span>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">📅</div>
              <div className="stat-content">
                <span className="stat-label">Created</span>
                <span className="stat-value">
                  {new Date(analytics.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>

          <div className="url-info">
            <h3>Original URL</h3>
            <a href={analytics.original_url} target="_blank" rel="noopener noreferrer">
              {analytics.original_url}
            </a>
          </div>

          {analytics.daily_clicks && analytics.daily_clicks.length > 0 && (
            <div className="chart-container">
              <h3>Last 7 Days Activity</h3>
              <div className="chart">
                {analytics.daily_clicks.map((day) => (
                  <div key={day.date} className="chart-bar-container">
                    <div
                      className="chart-bar"
                      style={{
                        height: `${(day.clicks / Math.max(...analytics.daily_clicks.map(d => d.clicks))) * 100}%`,
                      }}
                      title={`${day.clicks} clicks`}
                    >
                      <span className="chart-value">{day.clicks}</span>
                    </div>
                    <span className="chart-label">
                      {new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Analytics;