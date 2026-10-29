import React, { useState } from 'react';
import { 
  Plus, 
  Search, 
  MessageSquare, 
  Edit2, 
  Check, 
  Trash2, 
  Database, 
  PanelLeftClose, 
  ChevronDown, 
  ChevronUp, 
  FileText, 
  Video 
} from 'lucide-react';
import { ChatSession, DocumentItem } from '../../types';
import { THEME } from '../../constants/theme';
import { StudioBrandLogo } from '../avatar/StudioBrandLogo';

interface SidebarProps {
  isOpen: boolean;
  isMobile: boolean;
  sessions: ChatSession[];
  currentThreadId: string | null;
  historySearchQuery: string;
  docs: DocumentItem[];
  docsPanelOpen: boolean;
  onToggleSidebar: () => void;
  onNewChat: () => void;
  onSelectThread: (threadId: string) => void;
  onChangeHistorySearch: (q: string) => void;
  onRenameThread: (threadId: string, newTitle: string) => void;
  onDeleteThread: (threadId: string) => void;
  onToggleDocsPanel: () => void;
  onClearDocs: () => void;
  onTriggerFileUpload: () => void;
}

export function Sidebar({
  isOpen,
  isMobile,
  sessions,
  currentThreadId,
  historySearchQuery,
  docs,
  docsPanelOpen,
  onToggleSidebar,
  onNewChat,
  onSelectThread,
  onChangeHistorySearch,
  onRenameThread,
  onDeleteThread,
  onToggleDocsPanel,
  onClearDocs,
  onTriggerFileUpload
}: SidebarProps) {
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const [editingTitleText, setEditingTitleText] = useState('');

  const filteredSessions = sessions.filter(s => 
    !historySearchQuery.trim() || 
    s.title.toLowerCase().includes(historySearchQuery.toLowerCase()) ||
    s.messages.some(m => m.text.toLowerCase().includes(historySearchQuery.toLowerCase()))
  );

  return (
    <>
      {/* Mobile Drawer Backdrop */}
      {isMobile && isOpen && (
        <div 
          className="mobile-backdrop" 
          onClick={onToggleSidebar} 
          aria-label="Close sidebar overlay"
        />
      )}

      <aside 
        className={isMobile && isOpen ? 'mobile-drawer' : ''}
        style={{
          width: isOpen ? (isMobile ? '280px' : '260px') : '0px',
          minWidth: isOpen ? (isMobile ? '280px' : '260px') : '0px',
          height: '100%',
          backgroundColor: THEME.beigeSurface,
          borderRight: isOpen ? `1px solid ${THEME.beigeBorder}` : 'none',
          display: 'flex',
          flexDirection: 'column',
          transition: 'width 0.25s ease, min-width 0.25s ease',
          overflow: 'hidden',
          zIndex: isMobile ? 100 : 40,
          position: 'relative'
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '16px 14px' }}>
          
          {/* Sidebar Header with Close */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <StudioBrandLogo size={26} />
              <span style={{
                fontFamily: "'Newsreader', Georgia, serif",
                fontSize: '16px',
                fontWeight: '600',
                color: THEME.slateDark,
                letterSpacing: '-0.3px'
              }}>
                Agentic Studio
              </span>
            </div>

            <button
              type="button"
              onClick={onToggleSidebar}
              title="Close sidebar"
              aria-label="Close sidebar"
              style={{
                background: 'transparent',
                border: 'none',
                color: THEME.slateMuted,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '4px',
                borderRadius: '6px'
              }}
            >
              <PanelLeftClose size={17} />
            </button>
          </div>

          {/* New Chat Button */}
          <button
            type="button"
            onClick={onNewChat}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '10px 14px',
              backgroundColor: '#ffffff',
              color: THEME.burgundy,
              border: `1px solid ${THEME.beigeBorderDark}`,
              borderRadius: '20px',
              fontSize: '13.5px',
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 1px 4px rgba(0,0,0,0.03)',
              marginBottom: '12px',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = THEME.burgundySubtle;
              e.currentTarget.style.borderColor = THEME.burgundyBorder;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#ffffff';
              e.currentTarget.style.borderColor = THEME.beigeBorderDark;
            }}
          >
            <Plus size={16} strokeWidth={2.4} />
            <span>New chat</span>
          </button>

          {/* Search Conversation History */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: '#ffffff',
            border: `1px solid ${THEME.beigeBorder}`,
            borderRadius: '10px',
            padding: '5px 8px',
            marginBottom: '12px'
          }}>
            <Search size={13} color={THEME.slateMuted} />
            <input
              type="text"
              placeholder="Search history..."
              aria-label="Search conversation history"
              value={historySearchQuery}
              onChange={(e) => onChangeHistorySearch(e.target.value)}
              style={{
                width: '100%',
                border: 'none',
                outline: 'none',
                fontSize: '12px',
                color: THEME.slateDark,
                backgroundColor: 'transparent'
              }}
            />
          </div>

          {/* Chat History List Header */}
          <div style={{
            fontSize: '11px',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.4px',
            color: THEME.slateMuted,
            marginBottom: '6px',
            paddingLeft: '4px'
          }}>
            Chat History
          </div>

          {/* Chat History Scrollable List */}
          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '3px', paddingRight: '2px' }}>
            {filteredSessions.length === 0 ? (
              <div style={{ fontSize: '12px', color: THEME.slateLight, padding: '12px 6px', textAlign: 'center' }}>
                {historySearchQuery ? 'No matching chats found' : 'No previous conversations'}
              </div>
            ) : (
              filteredSessions.map((s) => {
                const isActive = s.thread_id === currentThreadId;
                const isEditing = editingThreadId === s.thread_id;

                return (
                  <div
                    key={s.thread_id}
                    className="sidebar-chat-item ui-no-select"
                    onClick={() => {
                      if (!isEditing) onSelectThread(s.thread_id);
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '7px 10px',
                      borderRadius: '10px',
                      cursor: 'pointer',
                      userSelect: 'none',
                      WebkitUserSelect: 'none',
                      backgroundColor: isActive ? THEME.burgundySubtle : 'transparent',
                      color: isActive ? THEME.burgundy : THEME.slateDark,
                      border: isActive ? `1px solid ${THEME.burgundyBorder}` : '1px solid transparent',
                      fontSize: '12.5px',
                      fontWeight: isActive ? 600 : 400,
                      transition: 'background-color 0.15s ease'
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) e.currentTarget.style.backgroundColor = 'rgba(0,0,0,0.03)';
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: 0, userSelect: 'none' }}>
                      <MessageSquare size={13} style={{ flexShrink: 0, opacity: isActive ? 1 : 0.6 }} />
                      
                      {isEditing ? (
                        <input
                          type="text"
                          autoFocus
                          value={editingTitleText}
                          onChange={(e) => setEditingTitleText(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              onRenameThread(s.thread_id, editingTitleText);
                              setEditingThreadId(null);
                            } else if (e.key === 'Escape') {
                              setEditingThreadId(null);
                            }
                          }}
                          onClick={(e) => e.stopPropagation()}
                          style={{
                            width: '100%',
                            fontSize: '12px',
                            border: `1px solid ${THEME.burgundyBorder}`,
                            borderRadius: '4px',
                            padding: '1px 4px',
                            outline: 'none',
                            color: THEME.slateDark
                          }}
                        />
                      ) : (
                        <span style={{
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          flex: 1,
                          userSelect: 'none',
                          WebkitUserSelect: 'none',
                          pointerEvents: 'none'
                        }}>
                          {s.title}
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '3px', marginLeft: '4px', flexShrink: 0 }}>
                      {isEditing ? (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onRenameThread(s.thread_id, editingTitleText);
                            setEditingThreadId(null);
                          }}
                          title="Save title"
                          aria-label="Save title"
                          style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#16a34a', padding: '2px' }}
                        >
                          <Check size={12} />
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingThreadId(s.thread_id);
                            setEditingTitleText(s.title);
                          }}
                          title="Rename chat"
                          aria-label="Rename chat"
                          style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: THEME.slateLight, padding: '2px' }}
                        >
                          <Edit2 size={12} />
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteThread(s.thread_id);
                        }}
                        title="Delete chat"
                        aria-label="Delete chat"
                        style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: THEME.slateLight, padding: '2px' }}
                        onMouseEnter={(e) => e.currentTarget.style.color = '#dc2626'}
                        onMouseLeave={(e) => e.currentTarget.style.color = THEME.slateLight}
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Bottom Document Knowledge Base Tray */}
          <div style={{
            borderTop: `1px solid ${THEME.beigeBorder}`,
            paddingTop: '10px',
            marginTop: '8px'
          }}>
            <button
              type="button"
              onClick={onToggleDocsPanel}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 8px',
                borderRadius: '8px',
                background: 'transparent',
                border: 'none',
                color: THEME.slateDark,
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = THEME.beigeSurfaceDark}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Database size={13} color={THEME.burgundy} />
                <span>Knowledge Base ({docs.length})</span>
              </div>
              {docsPanelOpen ? <ChevronDown size={13} /> : <ChevronUp size={13} />}
            </button>

            {docsPanelOpen && (
              <div style={{
                marginTop: '6px',
                padding: '6px',
                backgroundColor: '#ffffff',
                borderRadius: '8px',
                border: `1px solid ${THEME.beigeBorderDark}`,
                maxHeight: '130px',
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px'
              }}>
                {docs.length === 0 ? (
                  <div style={{ fontSize: '11px', color: THEME.slateMuted, padding: '8px 6px', textAlign: 'center', lineHeight: '1.4' }}>
                    Upload a PDF, DOCX, or YouTube link to get started.
                  </div>
                ) : (
                  docs.map((d) => (
                    <div 
                      key={d.id}
                      style={{
                        fontSize: '11px',
                        padding: '4px 6px',
                        backgroundColor: THEME.beigeBg,
                        borderRadius: '4px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '6px'
                      }}
                    >
                      <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: THEME.slateDark, fontWeight: 500 }}>
                        {d.title}
                      </span>
                      <span style={{ fontSize: '10px', color: THEME.slateMuted, flexShrink: 0 }}>
                        {d.chunk_count} chunks
                      </span>
                    </div>
                  ))
                )}

                {docs.length > 0 && (
                  <button
                    type="button"
                    onClick={onClearDocs}
                    style={{
                      marginTop: '4px',
                      padding: '4px',
                      fontSize: '10.5px',
                      color: '#dc2626',
                      backgroundColor: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      textAlign: 'center',
                      fontWeight: 600
                    }}
                  >
                    Clear Vector Store
                  </button>
                )}
              </div>
            )}
          </div>

        </div>
      </aside>
    </>
  );
}

