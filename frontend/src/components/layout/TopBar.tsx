import React, { useEffect, useState } from 'react';
import { PanelLeft, CheckSquare, Mail } from 'lucide-react';
import { THEME } from '../../constants/theme';
import { StudioBrandLogo } from '../avatar/StudioBrandLogo';

interface TopBarProps {
  sidebarOpen: boolean;
  currentThreadTitle: string;
  currentThreadId: string | null;
  onToggleSidebar: () => void;
  onOpenTaskManager?: () => void;
  onOpenGoogleConnect?: () => void;
}

export function TopBar({
  sidebarOpen,
  currentThreadTitle,
  currentThreadId,
  onToggleSidebar,
  onOpenTaskManager,
  onOpenGoogleConnect
}: TopBarProps) {
  const [googleStatus, setGoogleStatus] = useState<{
    connected: boolean;
    email?: string | null;
    expires_at?: string | null;
  }>({
    connected: false,
    email: null,
    expires_at: null
  });

  useEffect(() => {
    const checkGoogle = async () => {
      try {
        const res = await fetch('/api/auth/status');
        if (res.ok) {
          const data = await res.json();
          setGoogleStatus(data);
        }
      } catch {
        // Ignored
      }
    };
    checkGoogle();
    const interval = setInterval(checkGoogle, 8000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header style={{
      height: '56px',
      borderBottom: `1px solid ${THEME.beigeBorder}`,
      backgroundColor: THEME.beigeBg,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 18px',
      flexShrink: 0
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {!sidebarOpen && (
          <button
            type="button"
            onClick={onToggleSidebar}
            title="Open sidebar"
            aria-label="Open sidebar"
            style={{
              background: 'transparent',
              border: 'none',
              color: THEME.slateMuted,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '6px',
              borderRadius: '6px'
            }}
          >
            <PanelLeft size={16} />
          </button>
        )}

        {!sidebarOpen && <StudioBrandLogo size={24} />}

        <span style={{
          fontFamily: "'Newsreader', Georgia, serif",
          fontSize: '17px',
          fontWeight: '600',
          color: THEME.slateDark,
          letterSpacing: '-0.3px',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          maxWidth: '320px'
        }}>
          {currentThreadTitle}
        </span>

        <span style={{
          fontSize: '11px',
          fontWeight: 600,
          padding: '2px 8px',
          borderRadius: '10px',
          backgroundColor: THEME.beigeSurface,
          color: THEME.slateMuted,
          border: `1px solid ${THEME.beigeBorder}`
        }}>
          Personal Agent
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {/* Google Workspace Pill */}
        {onOpenGoogleConnect && (
          <button
            type="button"
            onClick={onOpenGoogleConnect}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              borderRadius: '14px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
              backgroundColor: googleStatus.connected ? '#ecfdf5' : '#f3f4f6',
              color: googleStatus.connected ? '#065f46' : '#6b7280',
              border: `1px solid ${googleStatus.connected ? '#a7f3d0' : '#e5e7eb'}`
            }}
            title={
              googleStatus.connected
                ? `Connected as ${googleStatus.email || 'Google User'}`
                : 'Google not connected. Click to connect'
            }
          >
            <Mail size={12} color={googleStatus.connected ? '#059669' : '#9ca3af'} />
            <span>
              {googleStatus.connected
                ? (googleStatus.email ? (googleStatus.email.length > 22 ? googleStatus.email.slice(0, 20) + '…' : googleStatus.email) : 'Connected')
                : 'Connect Google'}
            </span>
            <span style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: googleStatus.connected ? '#10b981' : '#9ca3af'
            }} />
          </button>
        )}

        {/* Task Manager Button */}
        {onOpenTaskManager && (
          <button
            type="button"
            onClick={onOpenTaskManager}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              padding: '4px 10px',
              borderRadius: '14px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
              backgroundColor: THEME.beigeSurface,
              color: THEME.slateDark,
              border: `1px solid ${THEME.beigeBorder}`
            }}
            title="Open Task Manager"
          >
            <CheckSquare size={12} color={THEME.burgundy} />
            <span>Tasks</span>
          </button>
        )}

        {currentThreadId && (
          <span style={{ fontSize: '11px', color: THEME.slateLight, fontFamily: 'monospace' }}>
            ID: {currentThreadId.slice(0, 14)}
          </span>
        )}
      </div>
    </header>
  );
}
