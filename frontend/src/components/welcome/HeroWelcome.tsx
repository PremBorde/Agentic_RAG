import React from 'react';
import { Sparkles, Globe, BookOpen } from 'lucide-react';
import { AvatarState } from '../../types';
import { THEME } from '../../constants/theme';
import { StudioBrandLogo } from '../avatar/StudioBrandLogo';

interface HeroWelcomeProps {
  avatarState: AvatarState;
  onSetAvatarState: (fn: (prev: AvatarState) => AvatarState) => void;
  onSelectPrompt: (prompt: string) => void;
  children: React.ReactNode; // Composer slot
}

export function HeroWelcome({
  avatarState,
  onSetAvatarState,
  onSelectPrompt,
  children
}: HeroWelcomeProps) {
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
      overflowY: 'auto'
    }}>
      <div style={{
        maxWidth: '680px',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center'
      }}>
        {/* Custom Studio Logo + Time-Based Serif Heading + Dynamic Assistant Status */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          marginBottom: '14px'
        }}>
          <div 
            onClick={() => onSetAvatarState((prev) => prev === 'sleeping' ? 'idle' : 'success')}
            title="Click to interact with your AI companion"
            style={{ cursor: 'pointer', transition: 'transform 0.2s ease' }}
            onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.04)'}
            onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
          >
            <StudioBrandLogo size={74} animation={avatarState} />
          </div>

          <div style={{
            fontSize: '11px',
            fontWeight: 600,
            padding: '3px 12px',
            borderRadius: '14px',
            backgroundColor: avatarState === 'sleeping' ? '#e2e8f0' : (avatarState === 'error' ? '#fee2e2' : (avatarState === 'success' ? '#dcfce7' : (avatarState === 'generating' || avatarState === 'searching' || avatarState === 'thinking' ? '#fce7eb' : '#f2ece0'))),
            color: avatarState === 'sleeping' ? '#64748b' : (avatarState === 'error' ? '#dc2626' : (avatarState === 'success' ? '#16a34a' : (avatarState === 'generating' || avatarState === 'searching' || avatarState === 'thinking' ? '#7a1c30' : '#586474'))),
            transition: 'all 0.25s ease',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <span style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: avatarState === 'sleeping' ? '#94a3b8' : (avatarState === 'error' ? '#ef4444' : (avatarState === 'success' ? '#22c55e' : (avatarState === 'generating' || avatarState === 'searching' || avatarState === 'thinking' ? '#7a1c30' : '#10b981')))
            }} />
            {avatarState === 'sleeping' && 'Resting (Zzz...) — Move mouse to wake'}
            {avatarState === 'idle' && 'Agentic AI Assistant • Ready'}
            {avatarState === 'thinking' && 'Analyzing question & routing...'}
            {avatarState === 'searching' && 'Searching vector docs & live web...'}
            {avatarState === 'generating' && 'Synthesizing response...'}
            {avatarState === 'success' && 'Response complete!'}
            {avatarState === 'error' && 'Error encountered'}
          </div>
        </div>

        <h1 style={{
          fontFamily: "'Newsreader', Georgia, serif",
          fontSize: '28px',
          fontWeight: '500',
          color: THEME.slateDark,
          margin: '0 0 16px',
          letterSpacing: '-0.4px'
        }}>
          {getGreeting()}, what would you like to explore?
        </h1>

        {/* Hero Composer Box */}
        <div style={{ width: '100%', marginBottom: '18px' }}>
          {children}
        </div>

        {/* Suggestion Prompt Pills */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center' }}>
          {[
            { text: "Hello! What can you do?", icon: <Sparkles size={13} color={THEME.burgundy} /> },
            { text: "Search Agentic AI breakthroughs", icon: <Globe size={13} color={THEME.burgundy} /> },
            { text: "What is Corrective RAG?", icon: <BookOpen size={13} color={THEME.burgundy} /> }
          ].map((item, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectPrompt(item.text)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '7px 14px',
                borderRadius: '16px',
                backgroundColor: '#ffffff',
                border: `1px solid ${THEME.beigeBorderDark}`,
                color: THEME.slateDark,
                fontSize: '12px',
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = THEME.burgundySubtle;
                e.currentTarget.style.borderColor = THEME.burgundyBorder;
                e.currentTarget.style.color = THEME.burgundy;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#ffffff';
                e.currentTarget.style.borderColor = THEME.beigeBorderDark;
                e.currentTarget.style.color = THEME.slateDark;
              }}
            >
              {item.icon}
              <span>{item.text}</span>
            </button>
          ))}
        </div>

      </div>
    </div>
  );
}

