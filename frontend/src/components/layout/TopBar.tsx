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
  const [googleConnected, setGoogleConnected] = useState(false);

  useEffect(() => {
    const checkGoogle = async () => {
      try {
        const res = await fetch('/api/auth/google/status');
        if (res.ok) {
          const data = await res.json();
          setGoogleConnected(data.connected);
        }
      } catch {
        // Ignored
      }
    };
    checkGoogle();
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
              backgroundColor: googleConnected ? '#ecfdf5' : THEME.beigeSurface,
              color: googleConnected ? '#065f46' : THEME.slateMuted,
              border: `1px solid ${googleConnected ? '#a7f3d0' : THEME.beigeBorder}`
            }}
            title={googleConnected ? 'Google Workspace Connected' : 'Connect Google Account'}
          >
            <Mail size={12} color={googleConnected ? '#059669' : THEME.burgundy} />
            <span>{googleConnected ? 'Google Connected' : 'Connect Google'}</span>
            <span style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: googleConnected ? '#10b981' : '#9ca3af'
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
