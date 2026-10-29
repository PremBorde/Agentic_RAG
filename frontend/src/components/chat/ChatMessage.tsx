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
  Sparkles, 
  Video, 
  ChevronDown, 
  ChevronUp 
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
  onSendFollowup
}: ChatMessageProps) {
  // System Document Ingestion Notification Card
  if (msg.sender === 'system' && msg.source === 'Document Indexed') {
    return (
      <div style={{
        width: '100%',
        maxWidth: '640px',
        background: `linear-gradient(135deg, ${THEME.beigeBg} 0%, #fffbf5 100%)`,
        border: `1.5px solid ${THEME.burgundyBorder}`,
        borderRadius: '14px',
        padding: '14px 18px',
        boxShadow: '0 3px 12px rgba(122, 28, 48, 0.06)',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '28px',
              height: '28px',
              borderRadius: '7px',
              backgroundColor: THEME.burgundy,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              {msg.docMeta?.sourceType === 'youtube' ? (
                <Video size={14} color="#fff" />
              ) : msg.docMeta?.sourceType === 'notes' ? (
                <Sparkles size={14} color="#fff" />
              ) : (
                <FileText size={14} color="#fff" />
              )}
            </div>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 650, color: THEME.burgundy }}>
                {msg.docMeta?.title || 'Document Indexed'}
              </div>
              <div style={{ fontSize: '11px', color: THEME.slateMuted }}>
                {msg.docMeta?.sourceType === 'youtube' ? 'YouTube Transcript' : msg.docMeta?.sourceType === 'notes' ? 'Custom Notes' : 'Uploaded File'} • {msg.docMeta?.chunkCount || 1} semantic chunks in FAISS
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
            border: '1px solid #c2e0c4'
          }}>
            ✓ Active
          </span>
        </div>

        {msg.docMeta?.preview && (
          <div style={{
            backgroundColor: '#ffffff',
            padding: '8px 12px',
            borderRadius: '8px',
            fontSize: '11.5px',
            color: THEME.slateDark,
            lineHeight: 1.5,
            border: `1px solid ${THEME.beigeBorder}`,
            maxHeight: '90px',
            overflowY: 'auto'
          }}>
            <span style={{ fontWeight: 600, color: THEME.slateMuted }}>Preview: </span>
            {msg.docMeta.preview}
          </div>
        )}
      </div>
    );
  }

  // System Error Banner
  if (msg.sender === 'system') {
    return (
      <div style={{
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
        gap: '12px',
        maxWidth: '100%',
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
              width: '30px',
              height: '30px',
              borderRadius: '50%',
              backgroundColor: THEME.burgundy,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <User size={15} color="#fff" />
            </div>
          ) : (
            <StudioBrandLogo 
              size={32} 
              animation={streamingMsgId === msg.id ? avatarState : 'idle'} 
            />
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
            padding: msg.sender === 'user' ? '10px 16px' : '16px 22px',
            borderRadius: msg.sender === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
            border: msg.sender === 'user' ? 'none' : `1px solid ${THEME.beigeBorder}`,
            boxShadow: msg.sender === 'user' 
              ? '0 2px 8px rgba(122, 28, 48, 0.16)' 
              : '0 2px 10px rgba(0,0,0,0.03)',
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
                  <Sparkles size={11} color={THEME.burgundy} />
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

