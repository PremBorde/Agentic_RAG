import React, { useState } from 'react';
import { MessageSquare, Globe, BookOpen, Mail } from 'lucide-react';
import { AvatarState } from '../../types';
import { THEME } from '../../constants/theme';
import { StudioBrandLogo } from '../avatar/StudioBrandLogo';

interface HeroWelcomeProps {
  avatarState: AvatarState;
  onSetAvatarState: (fn: (prev: AvatarState) => AvatarState) => void;
  onSelectPrompt: (prompt: string) => void;
  onOpenGoogleConnect?: () => void;
  onTriggerFileUpload?: () => void;
  googleConnected?: boolean;
  docsCount?: number;
  children: React.ReactNode; // Composer slot
}

export function HeroWelcome({
  avatarState,
  onSelectPrompt,
  googleConnected = false,
  children
}: HeroWelcomeProps) {
  const [pokeCount, setPokeCount] = useState<number>(0);
  const [actionClass, setActionClass] = useState<string>('');
  const [speechText, setSpeechText] = useState<string | null>(null);
  const speechTimeoutRef = React.useRef<any>(null);

  const FUNNY_QUOTES = [
    "Hey! Ready to explore or query some docs? 😄",
    "Boing! Hey, that tickles! 😆",
    "Who's the AI agent here, you or me? 🤖",
    "Careful! Click me again and I might launch autonomous mode! 🚀",
    "Achievement Unlocked: Master Mascot Poker! 🏆",
    "Wheee! Look at me go! 🌀",
    "Beep boop! My neural nets are buzzing with joy! ⚡",
    "Psst... ask me about LangGraph or check your Gmail! 📨",
    "Ready whenever you are! Just type below! 💬"
  ];

  const ANIMATION_CLASSES = [
    'mascot-action-bounce',
    'mascot-action-wiggle',
    'mascot-action-spin',
    'mascot-action-boing'
  ];

  const handleMascotClick = () => {
    const newCount = pokeCount + 1;
    setPokeCount(newCount);

    // Trigger next playful animation
    const anim = ANIMATION_CLASSES[(newCount - 1) % ANIMATION_CLASSES.length];
    setActionClass('');
    setTimeout(() => setActionClass(anim), 10);

    // Pick funny interactive quote
    const quote = newCount <= 5
      ? FUNNY_QUOTES[newCount - 1]
      : FUNNY_QUOTES[4 + ((newCount - 5) % (FUNNY_QUOTES.length - 4))];
    setSpeechText(quote);

    if (speechTimeoutRef.current) {
      clearTimeout(speechTimeoutRef.current);
    }
    speechTimeoutRef.current = setTimeout(() => {
      setSpeechText(null);
    }, 3600);
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  const suggestions = [
    { text: "Hello! What can you do?", icon: <MessageSquare size={13} color={THEME.burgundy} /> },
    ...(googleConnected
      ? [{ text: "Summarize my recent emails", icon: <Mail size={13} color={THEME.burgundy} /> }]
      : []),
    { text: "Search Agentic AI breakthroughs", icon: <Globe size={13} color={THEME.burgundy} /> },
    { text: "What is Corrective RAG?", icon: <BookOpen size={13} color={THEME.burgundy} /> }
  ];

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
      paddingBottom: '88px',
      overflowY: 'auto'
    }}>
      <div style={{
        maxWidth: '740px',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
        transform: 'translateY(-12px)'
      }}>
        {/* Custom Studio Logo with Interactive Reaction & Speech Bubble */}
        <div style={{
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '20px'
        }}>
          {/* Playful Floating Speech Bubble Popup */}
          {speechText && (
            <div 
              className="mascot-speech-bubble"
              style={{
                position: 'absolute',
                bottom: 'calc(100% + 14px)',
                left: '50%',
                backgroundColor: '#ffffff',
                border: `1.5px solid ${THEME.burgundyBorder}`,
                borderRadius: '16px',
                padding: '8px 14px',
                boxShadow: '0 8px 24px rgba(122, 28, 48, 0.12), 0 2px 6px rgba(0,0,0,0.04)',
                color: THEME.burgundy,
                fontSize: '12.5px',
                fontWeight: 600,
                whiteSpace: 'nowrap',
                zIndex: 20
              }}
            >
              {speechText}
              {/* Downward triangle pointer toward the mascot's head */}
              <div style={{
                position: 'absolute',
                bottom: '-6px',
                left: '50%',
                transform: 'translateX(-50%)',
                width: 0,
                height: 0,
                borderLeft: '6px solid transparent',
                borderRight: '6px solid transparent',
                borderTop: `6px solid ${THEME.burgundyBorder}`
              }} />
              <div style={{
                position: 'absolute',
                bottom: '-4.5px',
                left: '50%',
                transform: 'translateX(-50%)',
                width: 0,
                height: 0,
                borderLeft: '5px solid transparent',
                borderRight: '5px solid transparent',
                borderTop: '5px solid #ffffff'
              }} />
            </div>
          )}

          <div 
            onClick={handleMascotClick}
            className={actionClass}
            title="Click me to play!"
            style={{ 
              cursor: 'pointer', 
              transition: 'transform 0.18s ease',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              userSelect: 'none',
              WebkitUserSelect: 'none'
            }}
            onMouseEnter={(e) => {
              if (!actionClass) e.currentTarget.style.transform = 'scale(1.06)';
            }}
            onMouseLeave={(e) => {
              if (!actionClass) e.currentTarget.style.transform = 'scale(1)';
            }}
          >
            <StudioBrandLogo size={68} animation={avatarState} />
          </div>

          {/* Active status indicator only during actual busy / processing states */}
          {avatarState !== 'idle' && avatarState !== 'success' && (
            <div style={{
              position: 'absolute',
              bottom: '-6px',
              right: '-6px',
              width: '18px',
              height: '18px',
              borderRadius: '50%',
              backgroundColor: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 6px rgba(0,0,0,0.1)'
            }}>
              <div style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor: avatarState === 'thinking' ? '#f59e0b' : THEME.burgundy,
                animation: 'pulse 1.5s infinite'
              }} />
            </div>
          )}
        </div>

        {/* Editorial Greeting Header */}
        <h1 style={{
          fontFamily: "'Newsreader', Georgia, serif",
          fontSize: '32px',
          fontWeight: '450',
          color: THEME.slateDark,
          margin: '0 0 8px',
          letterSpacing: '-0.5px',
          lineHeight: 1.25
        }}>
          {getGreeting()}, what would you like to explore?
        </h1>
        <p style={{
          fontSize: '14px',
          color: THEME.slateMuted,
          margin: '0 0 28px',
          fontWeight: 400
        }}>
          Ask questions, search through your documents, or browse the web
        </p>

        {/* Hero Composer Box */}
        <div style={{ width: '100%', marginBottom: '20px' }}>
          {children}
        </div>

        {/* Suggestion Prompt Pills */}
        <div style={{ 
          display: 'flex', 
          flexWrap: 'wrap', 
          gap: '10px', 
          justifyContent: 'center',
          marginTop: '2px'
        }}>
          {suggestions.map((item, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectPrompt(item.text)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                borderRadius: '20px',
                backgroundColor: '#ffffff',
                border: '1px solid #e7ded2',
                color: THEME.slateDark,
                fontSize: '12.5px',
                fontWeight: 450,
                cursor: 'pointer',
                transition: 'all 0.18s ease',
                boxShadow: '0 1px 4px rgba(0,0,0,0.02)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#fdfaf8';
                e.currentTarget.style.borderColor = THEME.burgundyBorder;
                e.currentTarget.style.color = THEME.burgundy;
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = '0 3px 8px rgba(122, 28, 48, 0.08)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#ffffff';
                e.currentTarget.style.borderColor = '#e7ded2';
                e.currentTarget.style.color = THEME.slateDark;
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 1px 4px rgba(0,0,0,0.02)';
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
