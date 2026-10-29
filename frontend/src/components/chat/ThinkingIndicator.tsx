import React from 'react';
import { StudioBrandLogo } from '../avatar/StudioBrandLogo';
import { AvatarState } from '../../types';
import { THEME } from '../../constants/theme';

interface ThinkingIndicatorProps {
  avatarState: AvatarState;
  currentStage?: string;
}

export function ThinkingIndicator({ avatarState, currentStage }: ThinkingIndicatorProps) {
  const getStageLabel = () => {
    switch (currentStage) {
      case 'searching_gmail':
        return 'Searching Gmail...';
      case 'checking_calendar':
        return 'Checking calendar...';
      case 'searching_docs':
        return 'Searching documents...';
      case 'searching_web':
        return 'Searching the web...';
      case 'organizing_tasks':
        return 'Organizing tasks...';
      case 'preparing_draft':
        return 'Preparing draft...';
      case 'generating':
        return 'Formulating response...';
      default:
        return avatarState === 'searching'
          ? 'Searching...'
          : (avatarState === 'generating' ? 'Formulating response...' : 'Evaluating intent...');
    }
  };

  const label = getStageLabel();

  return (
    <div style={{ display: 'flex', gap: '10px', width: '100%', alignItems: 'flex-start' }}>
      <div 
        className="mascot-thinking-container"
        style={{ 
          width: '32px', 
          height: '32px', 
          borderRadius: '50%', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center', 
          flexShrink: 0, 
          marginTop: '2px' 
        }}
      >
        <StudioBrandLogo size={32} animation={avatarState === 'idle' ? 'thinking' : avatarState} />
      </div>
      <div style={{
        backgroundColor: '#ffffff',
        border: `1px solid ${THEME.beigeBorder}`,
        borderRadius: '16px 16px 16px 4px',
        padding: '10px 16px',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
      }}>
        <span style={{ fontSize: '13px', color: THEME.slateDark, fontWeight: 550 }}>
          {label}
        </span>
        <span className="thinking-dot thinking-dot-1" />
        <span className="thinking-dot thinking-dot-2" />
        <span className="thinking-dot thinking-dot-3" />
      </div>
    </div>
  );
}
