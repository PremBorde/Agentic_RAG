import React, { useState } from 'react';
import { MessageSquare, Globe, BookOpen, Mail, UploadCloud, Check, X, ArrowRight, Compass } from 'lucide-react';
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
  onSetAvatarState,
  onSelectPrompt,
  onOpenGoogleConnect,
  onTriggerFileUpload,
  googleConnected = false,
  docsCount = 0,
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

  const [showOnboarding, setShowOnboarding] = useState<boolean>(() => {
    try {
      return localStorage.getItem('agentic_onboarding_dismissed') !== 'true';
    } catch {
      return true;
    }
  });

  const handleDismissOnboarding = () => {
    setShowOnboarding(false);
    try {
      localStorage.setItem('agentic_onboarding_dismissed', 'true');
    } catch {
      // Ignored
    }
  };

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
        transform: 'translateY(-20px)'
      }}>
        {/* Custom Studio Logo with Interactive Reaction & Speech Bubble */}
        <div style={{
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '18px'
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
              marginTop: '10px',
              fontSize: '11px',
              fontWeight: 600,
              padding: '3px 12px',
              borderRadius: '14px',
              backgroundColor: avatarState === 'sleeping' ? '#e2e8f0' : (avatarState === 'error' ? '#fee2e2' : '#fce7eb'),
              color: avatarState === 'sleeping' ? '#64748b' : (avatarState === 'error' ? '#dc2626' : '#7a1c30'),
              transition: 'all 0.25s ease',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px'
            }}>
              <span style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: avatarState === 'sleeping' ? '#94a3b8' : (avatarState === 'error' ? '#ef4444' : '#7a1c30')
              }} />
              {avatarState === 'sleeping' && 'Resting (Zzz...)'}
              {avatarState === 'thinking' && 'Analyzing question & routing...'}
              {avatarState === 'searching' && 'Searching vector docs & live web...'}
              {avatarState === 'generating' && 'Synthesizing response...'}
              {avatarState === 'error' && 'Error encountered'}
            </div>
          )}
        </div>

        {/* Elegant Serif Heading & Subtitle */}
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

        {/* Onboarding Card for First Launch */}
        {showOnboarding && (
          <div style={{
            width: '100%',
            maxWidth: '680px',
            backgroundColor: '#ffffff',
            borderRadius: '14px',
            border: `1px solid ${THEME.beigeBorderDark}`,
            boxShadow: '0 4px 16px rgba(122, 28, 48, 0.04)',
            padding: '14px 18px',
            marginBottom: '18px',
            textAlign: 'left'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '6px',
                  backgroundColor: THEME.burgundySubtle,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: THEME.burgundy
                }}>
                  <Compass size={14} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '13px', fontWeight: 650, color: THEME.slateDark }}>
                    Quick Start Onboarding
                  </h3>
                  <p style={{ margin: 0, fontSize: '11px', color: THEME.slateMuted }}>
                    Set up your workspace tools or jump straight in with an example query
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleDismissOnboarding}
                title="Dismiss onboarding card"
                style={{
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  color: THEME.slateMuted,
                  padding: '4px',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <X size={15} />
              </button>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
              gap: '10px'
            }}>
              {/* Step 1: Connect Google */}
              <div 
                onClick={onOpenGoogleConnect}
                style={{
                  padding: '10px 12px',
                  borderRadius: '10px',
                  backgroundColor: THEME.beigeBg,
                  border: `1px solid ${THEME.beigeBorder}`,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = THEME.burgundyBorder;
                  e.currentTarget.style.backgroundColor = THEME.burgundySubtle;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = THEME.beigeBorder;
                  e.currentTarget.style.backgroundColor = THEME.beigeBg;
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontSize: '10.5px', fontWeight: 650, color: THEME.burgundy, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                    1. Connect Google
                  </span>
                  {googleConnected ? (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px', fontSize: '10px', color: '#16a34a', fontWeight: 600 }}>
                      <Check size={11} /> Connected
                    </span>
                  ) : (
                    <Mail size={12} color={THEME.slateMuted} />
                  )}
                </div>
                <div style={{ fontSize: '11px', color: THEME.slateMuted, lineHeight: '1.3' }}>
                  {googleConnected ? 'Gmail & Calendar ready' : 'Connect Gmail & Calendar'}
                </div>
              </div>

              {/* Step 2: Upload Doc */}
              <div 
                onClick={onTriggerFileUpload}
                style={{
                  padding: '10px 12px',
                  borderRadius: '10px',
                  backgroundColor: THEME.beigeBg,
                  border: `1px solid ${THEME.beigeBorder}`,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = THEME.burgundyBorder;
                  e.currentTarget.style.backgroundColor = THEME.burgundySubtle;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = THEME.beigeBorder;
                  e.currentTarget.style.backgroundColor = THEME.beigeBg;
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontSize: '10.5px', fontWeight: 650, color: THEME.burgundy, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                    2. Upload Doc
                  </span>
                  {docsCount > 0 ? (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px', fontSize: '10px', color: '#16a34a', fontWeight: 600 }}>
                      <Check size={11} /> {docsCount} Indexed
                    </span>
                  ) : (
                    <UploadCloud size={12} color={THEME.slateMuted} />
                  )}
                </div>
                <div style={{ fontSize: '11px', color: THEME.slateMuted, lineHeight: '1.3' }}>
                  Index PDF, DOCX, or link
                </div>
              </div>

              {/* Step 3: Try Example Query */}
              <div 
                onClick={() => onSelectPrompt('What can you do? Show me how you search emails, check calendar, and manage tasks.')}
                style={{
                  padding: '10px 12px',
                  borderRadius: '10px',
                  backgroundColor: THEME.beigeBg,
                  border: `1px solid ${THEME.beigeBorder}`,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = THEME.burgundyBorder;
                  e.currentTarget.style.backgroundColor = THEME.burgundySubtle;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = THEME.beigeBorder;
                  e.currentTarget.style.backgroundColor = THEME.beigeBg;
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontSize: '10.5px', fontWeight: 650, color: THEME.burgundy, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                    3. Try Query
                  </span>
                  <ArrowRight size={12} color={THEME.slateMuted} />
                </div>
                <div style={{ fontSize: '11px', color: THEME.slateMuted, lineHeight: '1.3' }}>
                  Test agent capabilities
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Hero Composer Box */}
        <div style={{ width: '100%', marginBottom: '22px' }}>
          {children}
        </div>

        {/* Suggestion Prompt Pills */}
        <div style={{ 
          display: 'flex', 
          flexWrap: 'wrap', 
          gap: '10px', 
          justifyContent: 'center',
          marginTop: '4px'
        }}>
          {[
            { text: "Hello! What can you do?", icon: <MessageSquare size={13} color={THEME.burgundy} /> },
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

