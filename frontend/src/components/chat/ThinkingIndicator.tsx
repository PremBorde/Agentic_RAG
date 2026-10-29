import React from 'react';
import { StudioBrandLogo } from '../avatar/StudioBrandLogo';
import { AvatarState } from '../../types';
import { THEME } from '../../constants/theme';

interface ThinkingIndicatorProps {
  avatarState: AvatarState;
}

export function ThinkingIndicator({ avatarState }: ThinkingIndicatorProps) {
  return (
    <div style={{ display: 'flex', gap: '10px', maxWidth: '820px', margin: '0 auto', width: '100%', alignItems: 'flex-start' }}>
      <div style={{ width: '32px', height: '32px', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '2px' }}>
        <StudioBrandLogo size={32} animation={avatarState} />
      </div>
      <div style={{
        backgroundColor: '#ffffff',
        border: `1px solid ${THEME.beigeBorder}`,
        borderRadius: '18px 18px 18px 4px',
        padding: '12px 18px',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
      }}>
        <span style={{ fontSize: '12.5px', color: THEME.slateMuted, fontWeight: 500 }}>
          {avatarState === 'searching' 
            ? 'Searching indexed documents & web...' 
            : (avatarState === 'generating' 
                ? 'Formulating response...' 
                : 'LangGraph is evaluating intent...')}
        </span>
        <span className="thinking-dot thinking-dot-1" />
        <span className="thinking-dot thinking-dot-2" />
        <span className="thinking-dot thinking-dot-3" />
      </div>
    </div>
  );
}

