import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { resolveShortCode } from '../services/api';

const RedirectHandler = () => {
  const { shortCode } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    const redirect = async () => {
      try {
        const originalUrl = await resolveShortCode(shortCode);
        window.location.replace(originalUrl);
      } catch {
        // Short code not found or expired — fall through to main UI
        navigate('/', { replace: true });
      }
    };

    redirect();
  }, [shortCode, navigate]);

  return null;
};

export default RedirectHandler;