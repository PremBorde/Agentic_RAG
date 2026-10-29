import React from 'react';
import { PanelLeft } from 'lucide-react';
import { THEME } from '../../constants/theme';
import { StudioBrandLogo } from '../avatar/StudioBrandLogo';

interface TopBarProps {
  sidebarOpen: boolean;
  currentThreadTitle: string;
  currentThreadId: string | null;
  onToggleSidebar: () => void;
}

export function TopBar({
  sidebarOpen,
  currentThreadTitle,
  currentThreadId,
  onToggleSidebar
}: TopBarProps) {
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
          maxWidth: '380px'
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
          LangGraph RAG
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {currentThreadId && (
          <span style={{ fontSize: '11px', color: THEME.slateLight, fontFamily: 'monospace' }}>
            ID: {currentThreadId.slice(0, 14)}
          </span>
        )}
      </div>
    </header>
  );
}

