import React, { useState, useEffect } from 'react';
import { X, Mail, CheckCircle2, ShieldCheck, LogOut, ArrowRight, Calendar } from 'lucide-react';
import { THEME } from '../../constants/theme';

interface GoogleConnectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStatusChanged?: () => void;
}

export const GoogleConnectModal: React.FC<GoogleConnectModalProps> = ({
  isOpen,
  onClose,
  onStatusChanged
}) => {
  const [status, setStatus] = useState<{ connected: boolean; email?: string | null }>({
    connected: false,
    email: null
  });
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/auth/status');
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch {
      // Ignored
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
      setErrorMsg('');
    }
  }, [isOpen]);

  const handleSignInWithGoogle = () => {
    setLoading(true);
    // Direct browser redirect to Google OAuth login endpoint
    window.location.href = '/api/auth/google/login';
  };

  const handleSignOut = async () => {
    setLoading(true);
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
      await fetchStatus();
      if (onStatusChanged) onStatusChanged();
      onClose();
      // Reload page to reset current session state
      window.location.href = '/?disconnected=true';
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to sign out.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      backgroundColor: 'rgba(30, 24, 20, 0.45)',
      backdropFilter: 'blur(3px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '480px',
        backgroundColor: '#ffffff',
        borderRadius: '16px',
        border: `1px solid ${THEME.beigeBorderDark}`,
        boxShadow: '0 20px 40px rgba(122, 28, 48, 0.15)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          backgroundColor: THEME.beigeSurface,
          borderBottom: `1px solid ${THEME.beigeBorder}`
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              backgroundColor: THEME.burgundy,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff'
            }}>
              <Mail size={16} />
            </div>
            <div>
              <div style={{ fontSize: '15px', fontWeight: 650, color: THEME.slateDark }}>
                Google Workspace
              </div>
              <div style={{ fontSize: '11px', color: THEME.slateMuted }}>
                Gmail & Google Calendar Multi-User OAuth 2.0
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: THEME.slateMuted,
              padding: '4px',
              display: 'flex',
              alignItems: 'center',
              borderRadius: '4px'
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '24px 20px' }}>
          {errorMsg && (
            <div style={{
              padding: '10px 14px',
              backgroundColor: '#fee2e2',
              color: '#991b1b',
              borderRadius: '8px',
              fontSize: '12px',
              marginBottom: '16px'
            }}>
              {errorMsg}
            </div>
          )}

          {status.connected ? (
            /* Connected View */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '14px',
                backgroundColor: '#ecfdf5',
                borderRadius: '12px',
                border: '1px solid #a7f3d0'
              }}>
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  backgroundColor: '#10b981',
                  color: '#ffffff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}>
                  <CheckCircle2 size={20} />
                </div>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: '#065f46' }}>
                    Signed in with Google
                  </div>
                  <div style={{ fontSize: '13px', fontWeight: 650, color: '#047857', wordBreak: 'break-all' }}>
                    {status.email || 'Connected Account'}
                  </div>
                </div>
              </div>

              <div style={{
                fontSize: '12px',
                color: THEME.slateMuted,
                lineHeight: '1.5',
                padding: '0 4px'
              }}>
                Your personal Gmail and Google Calendar are active. You can ask the agent to search messages, draft replies, check meeting availability, and schedule events.
              </div>

              <button
                type="button"
                onClick={handleSignOut}
                disabled={loading}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  padding: '10px 16px',
                  backgroundColor: '#ffffff',
                  color: '#dc2626',
                  border: '1px solid #fecaca',
                  borderRadius: '10px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  transition: 'all 0.15s ease',
                  marginTop: '8px'
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#fef2f2'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#ffffff'}
              >
                <LogOut size={15} />
                <span>Sign Out of Google</span>
              </button>
            </div>
          ) : (
            /* Disconnected / Sign In View */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div style={{ fontSize: '13px', color: THEME.slateDark, lineHeight: '1.5' }}>
                Sign in with your Google account to grant your agent access to your Gmail and Google Calendar. Each user connects securely with their own individual credentials.
              </div>

              {/* Feature Points */}
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
                padding: '14px',
                backgroundColor: THEME.beigeBg,
                borderRadius: '12px',
                border: `1px solid ${THEME.beigeBorder}`
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '12px', color: THEME.slateDark }}>
                  <Mail size={15} color={THEME.burgundy} />
                  <span><strong>Gmail:</strong> Search inbox, read threads, prepare replies</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '12px', color: THEME.slateDark }}>
                  <Calendar size={15} color={THEME.burgundy} />
                  <span><strong>Calendar:</strong> Check availability, find slots, propose events</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '12px', color: THEME.slateDark }}>
                  <ShieldCheck size={15} color="#16a34a" />
                  <span><strong>Per-User Security:</strong> Tokens encrypted with Fernet at rest</span>
                </div>
              </div>

              {/* Direct Sign in with Google Button */}
              <button
                type="button"
                onClick={handleSignInWithGoogle}
                disabled={loading}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '10px',
                  padding: '12px 20px',
                  backgroundColor: THEME.burgundy,
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '10px',
                  fontSize: '14px',
                  fontWeight: 650,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  boxShadow: '0 4px 12px rgba(122, 28, 48, 0.25)',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = THEME.burgundyHover}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = THEME.burgundy}
              >
                <svg width="18" height="18" viewBox="0 0 24 24">
                  <path fill="#ffffff" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#ffffff" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#ffffff" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                  <path fill="#ffffff" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                </svg>
                <span>{loading ? 'Redirecting to Google...' : 'Sign in with Google'}</span>
                <ArrowRight size={16} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
