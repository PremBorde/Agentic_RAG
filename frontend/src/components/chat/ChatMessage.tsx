import React from 'react';
import { 
  User, 
  Copy, 
  Check, 
  RotateCcw, 
  ThumbsUp, 
  ThumbsDown, 
  BookOpen, 
  FileText, 
  ArrowRight,
  MessageSquare, 
  Video, 
  ChevronDown, 
  ChevronUp,
  Mail 
} from 'lucide-react';
import { Message, AvatarState } from '../../types';
import { THEME } from '../../constants/theme';
import { StudioBrandLogo } from '../avatar/StudioBrandLogo';
import { MarkdownContent, getDisplaySourceBadge } from './MarkdownContent';
import { RetrievedContext } from './RetrievedContext';
import { ActionProposalCard } from './ActionProposalCard';

interface ChatMessageProps {
  msg: Message;
  isLatest: boolean;
  streamingMsgId: string | null;
  avatarState: AvatarState;
  copiedMsgId: string | null;
  likedMsgId: Record<string, boolean>;
  expandedDocs: Record<string, boolean>;
  highlightedChunk: string | null;
  onCopy: (msgId: string, text: string) => void;
  onRetry: () => void;
  onLike: (msgId: string) => void;
  onDislike: (msgId: string) => void;
  onToggleDocExpand: (msgId: string) => void;
  onJumpToChunk: (msgId: string, chunkIdx: number) => void;
  onSendFollowup: (q: string) => void;
  onOpenGoogleConnect?: () => void;
  currentStage?: string;
}

export function ChatMessage({
  msg,
  isLatest,
  streamingMsgId,
  avatarState,
  copiedMsgId,
  likedMsgId,
  expandedDocs,
  highlightedChunk,
  onCopy,
  onRetry,
  onLike,
  onDislike,
  onToggleDocExpand,
  onJumpToChunk,
  onSendFollowup,
  onOpenGoogleConnect,
  currentStage
}: ChatMessageProps) {
  // System Document Ingestion Notification Card
  if (msg.sender === 'system' && msg.source === 'Document Indexed') {
    return (
      <div style={{
        alignSelf: 'center',
        margin: '6px auto',
        width: 'fit-content',
        maxWidth: '460px',
        background: `linear-gradient(135deg, ${THEME.beigeBg} 0%, #fffbf5 100%)`,
        border: `1.5px solid ${THEME.burgundyBorder}`,
        borderRadius: '12px',
        padding: '10px 16px',
        boxShadow: '0 2px 8px rgba(122, 28, 48, 0.05)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            backgroundColor: THEME.burgundy,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}>
            {msg.docMeta?.sourceType === 'youtube' ? (
              <Video size={15} color="#fff" />
            ) : (
              <FileText size={15} color="#fff" />
            )}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ 
              fontSize: '13px', 
              fontWeight: 650, 
              color: THEME.burgundy,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              maxWidth: '240px'
            }}>
              {msg.docMeta?.title || 'Document Uploaded'}
            </div>
            <div style={{ fontSize: '11px', color: THEME.slateMuted }}>
              {msg.docMeta?.chunkCount ? `${msg.docMeta.chunkCount} Pages • ` : ''}Docs Uploaded
            </div>
          </div>
        </div>
        <span style={{
          fontSize: '11px',
          fontWeight: 600,
          padding: '3px 8px',
          borderRadius: '10px',
          backgroundColor: '#edf5ed',
          color: '#235928',
          border: '1px solid #c2e0c4',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          flexShrink: 0,
          whiteSpace: 'nowrap'
        }}>
          ✓ Docs Uploaded
        </span>
      </div>
    );
  }

  // System Error Banner
  if (msg.sender === 'system') {
    return (
      <div style={{
        alignSelf: 'center',
        margin: '6px auto',
        maxWidth: '680px',
        padding: '12px 18px',
        borderRadius: '12px',
        backgroundColor: '#fef2f2',
        color: '#991b1b',
        border: '1px solid #fecaca',
        fontSize: '13px',
        lineHeight: 1.5,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px'
      }}>
        <div>{msg.text}</div>
        <button
          type="button"
          onClick={onRetry}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '5px',
            padding: '4px 10px',
            borderRadius: '6px',
            backgroundColor: '#ffffff',
            border: '1px solid #fca5a5',
            color: '#991b1b',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          <RotateCcw size={12} /> Retry
        </button>
      </div>
    );
  }

  // User & Assistant Chat Messages
  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', alignItems: msg.sender === 'user' ? 'flex-end' : 'flex-start' }}>
      <div style={{
        display: 'flex',
        gap: '10px',
        maxWidth: msg.sender === 'user' ? '78%' : '100%',
        width: msg.sender === 'user' ? 'auto' : '100%',
        justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start'
      }}>
        {/* Avatar Column */}
        <div style={{
          width: '32px',
          height: '32px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          marginTop: '2px',
          order: msg.sender === 'user' ? 2 : 1
        }}>
          {msg.sender === 'user' ? (
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              backgroundColor: THEME.burgundy,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <User size={16} color="#fff" />
            </div>
          ) : (
            <div className={streamingMsgId === msg.id ? 'mascot-thinking-container' : ''}>
              <StudioBrandLogo 
                size={32} 
                animation={streamingMsgId === msg.id ? avatarState : 'idle'} 
              />
            </div>
          )}
        </div>

        {/* Content Column */}
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          maxWidth: msg.sender === 'user' ? '100%' : 'calc(100% - 44px)',
          order: msg.sender === 'user' ? 1 : 2
        }}>
          <div style={{
            backgroundColor: msg.sender === 'user' ? THEME.burgundy : THEME.beigeCard,
            color: msg.sender === 'user' ? '#fffaf8' : THEME.slateDark,
            padding: msg.sender === 'user' ? '9px 15px' : '12px 18px',
            borderRadius: msg.sender === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
            border: msg.sender === 'user' ? 'none' : `1px solid ${THEME.beigeBorder}`,
            boxShadow: msg.sender === 'user' 
              ? '0 2px 6px rgba(122, 28, 48, 0.12)' 
              : '0 2px 8px rgba(0,0,0,0.03)',
            width: 'fit-content',
            maxWidth: '100%',
            wordBreak: 'break-word',
            userSelect: 'text'
          }}>
            {/* Source Badge if Assistant used a real tool/source */}
            {msg.sender === 'assistant' && (() => {
              const badge = getDisplaySourceBadge(msg.source);
              if (!badge) return null;
              return (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                  <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '2.5px 9px',
                    borderRadius: '12px',
                    fontSize: '11px',
                    fontWeight: '600',
                    backgroundColor: badge.bg,
                    color: badge.color,
                    border: `1px solid ${badge.border}`
                  }}>
                    {badge.icon}
                    {badge.label}
                  </span>
                </div>
              );
            })()}

            {/* Live Active Tool Step Badge while streaming */}
            {msg.sender === 'assistant' && streamingMsgId === msg.id && currentStage && currentStage !== 'generating' && currentStage !== 'thinking' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <span style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '2.5px 9px',
                  borderRadius: '12px',
                  fontSize: '11px',
                  fontWeight: '600',
                  backgroundColor: '#fbf0f2',
                  color: '#7a1c30',
                  border: '1px solid #f0c2cc'
                }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#7a1c30', display: 'inline-block' }} />
                  {currentStage === 'searching_gmail' ? 'Searching Gmail...' :
                   currentStage === 'checking_calendar' ? 'Checking calendar...' :
                   currentStage === 'searching_docs' ? 'Searching documents...' :
                   currentStage === 'searching_web' ? 'Searching the web...' :
                   currentStage === 'organizing_tasks' ? 'Organizing tasks...' :
                   currentStage === 'preparing_draft' ? 'Preparing draft...' :
                   currentStage}
                </span>
              </div>
            )}

            {/* Markdown Content with Code Block highlighting & Tables */}
            <MarkdownContent 
              content={msg.text} 
              isUser={msg.sender === 'user'} 
              isStreaming={streamingMsgId === msg.id}
              onCitationClick={(chunkIdx) => onJumpToChunk(msg.id, chunkIdx)}
            />

            {/* Human-in-the-Loop Action Proposal Card */}
            {msg.proposal && (
              <ActionProposalCard proposal={msg.proposal} />
            )}

            {/* Inline Sign in with Google Button inside chat message bubble */}
            {(msg.requiresGoogleAuth || (msg.sender === 'assistant' && (
              msg.text.includes("don't have access to your Gmail") ||
              msg.text.includes("haven't connected it or authenticated your session") ||
              msg.text.includes("Google Workspace is Not Connected") ||
              msg.text.includes("Google account not connected") ||
              msg.text.includes("set up the Gmail integration")
            ))) && (
              <div style={{ marginTop: '14px', display: 'flex', alignItems: 'center' }}>
                <button
                  type="button"
                  onClick={() => {
                    window.location.href = '/api/auth/google/login';
                  }}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '9px 16px',
                    borderRadius: '10px',
                    border: 'none',
                    backgroundColor: THEME.burgundy,
                    color: '#ffffff',
                    fontSize: '13px',
                    fontWeight: 650,
                    cursor: 'pointer',
                    boxShadow: '0 3px 8px rgba(122, 28, 48, 0.25)',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = THEME.burgundyHover}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = THEME.burgundy}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24">
                    <path fill="#ffffff" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                    <path fill="#ffffff" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                    <path fill="#ffffff" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                    <path fill="#ffffff" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                  </svg>
                  <span>Sign in with Google</span>
                </button>
              </div>
            )}

            {/* Quick-Access Interactive Citation Pills */}
            {msg.sender === 'assistant' && msg.retrievedDocs && msg.retrievedDocs.length > 0 && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '6px',
                marginTop: '12px',
                paddingTop: '8px',
                borderTop: `1px dashed ${THEME.beigeBorder}`
              }}>
                <span style={{ fontSize: '11px', fontWeight: 600, color: THEME.slateMuted, display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <BookOpen size={11} color={THEME.burgundy} />
                  Sources:
                </span>
                {msg.retrievedDocs.map((doc, cIdx) => (
                  <button
                    key={cIdx}
                    type="button"
                    className="citation-badge"
                    style={{ height: '20px', padding: '0 8px', borderRadius: '10px', fontSize: '11px', cursor: 'pointer' }}
                    onClick={() => onJumpToChunk(msg.id, cIdx)}
                    title={`Jump to chunk #${cIdx + 1}: ${doc.source}`}
                    aria-label={`Jump to chunk ${cIdx + 1}: ${doc.source}`}
                  >
                    [{cIdx + 1}] {doc.source.length > 22 ? doc.source.slice(0, 22) + '…' : doc.source}
                  </button>
                ))}
              </div>
            )}

            {/* Expandable Actual Retrieved Docs Accordion */}
            {msg.retrievedDocs && msg.retrievedDocs.length > 0 && (
              <RetrievedContext 
                messageId={msg.id}
                docs={msg.retrievedDocs}
                isExpanded={!!expandedDocs[msg.id]}
                onToggle={onToggleDocExpand}
                highlightedChunk={highlightedChunk}
              />
            )}
          </div>

          {/* Action Bar Below Completed Assistant Messages */}
          {msg.sender === 'assistant' && streamingMsgId !== msg.id && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              marginTop: '6px',
              paddingLeft: '4px'
            }}>
              <span style={{ fontSize: '11px', color: THEME.slateLight }}>
                {msg.timestamp}
              </span>

              <button
                type="button"
                onClick={() => onCopy(msg.id, msg.text)}
                title="Copy response"
                aria-label="Copy response to clipboard"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: copiedMsgId === msg.id ? '#16a34a' : THEME.slateLight,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '11px',
                  padding: '2px 4px',
                  borderRadius: '4px',
                  transition: 'color 0.15s ease'
                }}
              >
                {copiedMsgId === msg.id ? <Check size={12} /> : <Copy size={12} />}
                <span>{copiedMsgId === msg.id ? 'Copied' : 'Copy'}</span>
              </button>

              <button
                type="button"
                onClick={onRetry}
                title="Regenerate response"
                aria-label="Regenerate response"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: THEME.slateLight,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '11px',
                  padding: '2px 4px',
                  borderRadius: '4px',
                  transition: 'color 0.15s ease'
                }}
              >
                <RotateCcw size={12} />
                <span>Retry</span>
              </button>

              <button
                type="button"
                onClick={() => onLike(msg.id)}
                title="Helpful response"
                aria-label="Mark response as helpful"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: likedMsgId[msg.id] === true ? THEME.burgundy : THEME.slateLight,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  padding: '2px 4px',
                  transition: 'color 0.15s ease'
                }}
              >
                <ThumbsUp size={12} />
              </button>

              <button
                type="button"
                onClick={() => onDislike(msg.id)}
                title="Unhelpful response"
                aria-label="Mark response as unhelpful"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: likedMsgId[msg.id] === false ? THEME.burgundy : THEME.slateLight,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  padding: '2px 4px',
                  transition: 'color 0.15s ease'
                }}
              >
                <ThumbsDown size={12} />
              </button>
            </div>
          )}

          {/* Follow-up question chips for the latest completed assistant message */}
          {msg.sender === 'assistant' && streamingMsgId !== msg.id && isLatest && (
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '6px',
              marginTop: '10px',
              paddingLeft: '4px'
            }}>
              {(msg.retrievedDocs && msg.retrievedDocs.length > 0 ? [
                "Can you summarize key takeaways in bullet points?",
                "Are there any limitations or exceptions mentioned?",
                "What are practical applications of this?"
              ] : [
                "What other tasks can you assist with?",
                "Can you provide a code or concrete example?",
                "How do I upload and query my documents?"
              ]).map((q, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="followup-chip"
                  onClick={() => onSendFollowup(q)}
                >
                  <ArrowRight size={11} color={THEME.burgundy} />
                  <span>{q}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

