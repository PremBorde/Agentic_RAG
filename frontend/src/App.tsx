import React, { useState, useEffect, useRef } from 'react';
import '@bible-strong/avatar-react/styles.css';
import { 
  RetrievedDoc, 
  Message, 
  DocumentItem, 
  ChatSession, 
  AvatarState, 
  ToastFeedback 
} from './types';
import { THEME } from './constants/theme';
import { Sidebar } from './components/layout/Sidebar';
import { TopBar } from './components/layout/TopBar';
import { HeroWelcome } from './components/welcome/HeroWelcome';
import { ChatMessage } from './components/chat/ChatMessage';
import { ThinkingIndicator } from './components/chat/ThinkingIndicator';
import { Composer } from './components/composer/Composer';
import { TextModal } from './components/modals/TextModal';
import { YouTubeModal } from './components/modals/YouTubeModal';

const TaskManagerModal = React.lazy(() =>
  import('./components/modals/TaskManagerModal').then((m) => ({ default: m.TaskManagerModal }))
);
const GoogleConnectModal = React.lazy(() =>
  import('./components/modals/GoogleConnectModal').then((m) => ({ default: m.GoogleConnectModal }))
);

export default function App() {
  // Sessions & History
  const [sessions, setSessions] = useState<ChatSession[]>(() => {
    try {
      const saved = localStorage.getItem('rag_studio_sessions');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState<boolean>(() => {
    return typeof window !== 'undefined' ? window.innerWidth <= 768 : false;
  });
  const [historySearchQuery, setHistorySearchQuery] = useState('');

  // Messages & Stream State
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [streamingMsgId, setStreamingMsgId] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState<string>('thinking');
  const [userScrolledUp, setUserScrolledUp] = useState(false);

  // Avatar procedural animations & inactivity
  const [avatarState, setAvatarState] = useState<AvatarState>('idle');
  const idleTimerRef = useRef<any>(null);

  // Model & Documents State
  const [selectedModel, setSelectedModel] = useState('gemini-3.5-flash-lite');
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [docsPanelOpen, setDocsPanelOpen] = useState(false);

  // UI Menus & Ingestion Modals
  const [plusMenuOpen, setPlusMenuOpen] = useState(false);
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [activeModal, setActiveModal] = useState<'text' | 'youtube' | null>(null);
  const [taskManagerOpen, setTaskManagerOpen] = useState(false);
  const [googleConnectOpen, setGoogleConnectOpen] = useState(false);
  const [googleConnected, setGoogleConnected] = useState(false);

  // Modal Input states
  const [docTitle, setDocTitle] = useState('');
  const [docContent, setDocContent] = useState('');
  const [isSubmittingText, setIsSubmittingText] = useState(false);

  const [ytUrl, setYtUrl] = useState('');
  const [ytTitle, setYtTitle] = useState('');
  const [isSubmittingYt, setIsSubmittingYt] = useState(false);

  // File Upload State
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [uploadingFileName, setUploadingFileName] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStep, setUploadStep] = useState('');

  // Interactive Message States
  const [expandedDocs, setExpandedDocs] = useState<Record<string, boolean>>({});
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);
  const [likedMap, setLikedMap] = useState<Record<string, boolean>>({});
  const [highlightedChunk, setHighlightedChunk] = useState<string | null>(null);

  // Toast feedback banner
  const [toastFeedback, setToastFeedback] = useState<ToastFeedback | null>(null);

  // Refs
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Sync sessions to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('rag_studio_sessions', JSON.stringify(sessions));
    } catch (e) {
      console.error('Failed to save sessions:', e);
    }
  }, [sessions]);

  // Load conversation threads from SQLite backend on initial mount
  useEffect(() => {
    const loadBackendThreads = async () => {
      try {
        const res = await fetch('/api/conversations');
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data.conversations) && data.conversations.length > 0) {
            const serverSessions: ChatSession[] = await Promise.all(
              data.conversations.map(async (c: any) => {
                let msgs: Message[] = [];
                try {
                  const mRes = await fetch(`/api/conversations/${c.id}`);
                  if (mRes.ok) {
                    const mData = await mRes.json();
                    msgs = mData.messages || [];
                  }
                } catch {}
                return {
                  thread_id: c.id,
                  title: c.title,
                  messages: msgs,
                  model: c.model || 'gemini-3.5-flash-lite',
                  updatedAt: new Date(c.updated_at).getTime() || Date.now(),
                };
              })
            );
            setSessions((prev) => {
              const map = new Map<string, ChatSession>();
              prev.forEach((s) => map.set(s.thread_id, s));
              serverSessions.forEach((s) => map.set(s.thread_id, s));
              return Array.from(map.values()).sort((a, b) => b.updatedAt - a.updatedAt);
            });
          }
        }
      } catch (err) {
        console.error('Failed to sync conversations from backend:', err);
      }
    };
    loadBackendThreads();
  }, []);

  // Window resize listener
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth <= 768;
      setIsMobile(mobile);
      if (mobile) setSidebarOpen(false);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Inactivity tracking for procedural avatar sleeping animation
  useEffect(() => {
    const resetIdleTimer = () => {
      if (avatarState === 'sleeping') {
        setAvatarState('idle');
      }
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
      if (!isLoading && !streamingMsgId) {
        idleTimerRef.current = setTimeout(() => {
          setAvatarState('sleeping');
        }, 45000);
      }
    };

    const events = ['mousemove', 'keydown', 'mousedown', 'touchstart', 'scroll'];
    events.forEach((ev) => window.addEventListener(ev, resetIdleTimer));
    resetIdleTimer();

    return () => {
      events.forEach((ev) => window.removeEventListener(ev, resetIdleTimer));
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    };
  }, [isLoading, streamingMsgId, avatarState]);

  // Fetch documents list
  const fetchDocs = async () => {
    try {
      const res = await fetch('/api/documents');
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.documents || []);
      }
    } catch (e) {
      console.error('Error fetching documents:', e);
    }
  };

  useEffect(() => {
    fetchDocs();
    const interval = setInterval(fetchDocs, 12000);
    return () => clearInterval(interval);
  }, []);

  const checkGoogleStatus = async () => {
    try {
      const res = await fetch('/api/auth/status');
      if (res.ok) {
        const data = await res.json();
        setGoogleConnected(Boolean(data.connected));
      }
    } catch {
      // Ignored
    }
  };

  useEffect(() => {
    checkGoogleStatus();
  }, [googleConnectOpen]);

  // Auto scroll to bottom
  useEffect(() => {
    if (!userScrolledUp && messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, streamingMsgId, isLoading]);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    const distanceFromBottom = target.scrollHeight - target.scrollTop - target.clientHeight;
    setUserScrolledUp(distanceFromBottom > 110);
  };

  const showToast = (type: 'success' | 'error', message: string) => {
    setToastFeedback({ type, message });
    setTimeout(() => setToastFeedback(null), 4000);
  };

  // Chat Actions
  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedMsgId(id);
    setTimeout(() => setCopiedMsgId(null), 2000);
  };

  const handleLike = (id: string) => {
    setLikedMap((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleDislike = (id: string) => {
    setLikedMap((prev) => ({ ...prev, [id]: false }));
  };

  const handleToggleDocExpand = (id: string) => {
    setExpandedDocs((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleJumpToChunk = (msgId: string, chunkIdx: number) => {
    setExpandedDocs((prev) => ({ ...prev, [msgId]: true }));
    const targetId = `chunk-${msgId}-${chunkIdx}`;
    setHighlightedChunk(targetId);

    setTimeout(() => {
      const el = document.getElementById(targetId);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 120);

    setTimeout(() => setHighlightedChunk(null), 3200);
  };

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setStreamingMsgId(null);
    setAvatarState('idle');
  };

  const handleRegenerate = () => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].sender === 'user') {
        handleSendMessage(messages[i].text);
        return;
      }
    }
  };

  const handleStartNewChat = () => {
    setCurrentThreadId(null);
    setMessages([]);
    setInputMessage('');
    setPlusMenuOpen(false);
    setActiveModal(null);
  };

  const handleSelectThread = (threadId: string) => {
    const sess = sessions.find((s) => s.thread_id === threadId);
    if (sess) {
      setCurrentThreadId(sess.thread_id);
      setMessages(sess.messages || []);
      if (sess.model) {
        const validModel = ['gemini-3.5-flash-lite', 'gemini-3-flash-preview', 'gemini-flash-latest'].includes(sess.model)
          ? sess.model
          : 'gemini-3.5-flash-lite';
        setSelectedModel(validModel);
      }
    }
    setPlusMenuOpen(false);
    setActiveModal(null);
  };

  const handleRenameThread = async (threadId: string, newTitle: string) => {
    setSessions((prev) =>
      prev.map((s) => (s.thread_id === threadId ? { ...s, title: newTitle } : s))
    );
    try {
      await fetch(`/api/conversations/${threadId}/title`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle }),
      });
    } catch (e) {
      console.error('Failed to rename thread on server:', e);
    }
  };

  const handleDeleteThread = async (threadId: string) => {
    setSessions((prev) => prev.filter((s) => s.thread_id !== threadId));
    if (currentThreadId === threadId) {
      handleStartNewChat();
    }
    try {
      await fetch(`/api/conversations/${threadId}`, { method: 'DELETE' });
    } catch (e) {
      console.error('Failed to delete thread on server:', e);
    }
  };

  const handleClearDocs = async () => {
    try {
      await fetch('/api/documents/clear', { method: 'POST' });
      setDocuments([]);
      showToast('success', 'Vector store cleared.');
    } catch (e) {
      showToast('error', 'Failed to clear documents.');
    }
  };

  // Send Message / SSE Streaming
  const handleSendMessage = async (queryText?: string) => {
    const textToSend = queryText || inputMessage;
    if (!textToSend.trim() || isLoading) return;

    let activeThreadId = currentThreadId;
    let isBrandNewSession = false;
    if (!activeThreadId) {
      activeThreadId = `thread_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
      setCurrentThreadId(activeThreadId);
      isBrandNewSession = true;
    }

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInputMessage('');
    setUserScrolledUp(false);
    setIsLoading(true);
    setAvatarState('thinking');
    setCurrentStage('thinking');

    if (isBrandNewSession) {
      const newTitle = textToSend.trim().slice(0, 36) + (textToSend.trim().length > 36 ? '...' : '');
      setSessions((prev) => [
        {
          thread_id: activeThreadId!,
          title: newTitle,
          messages: nextMessages,
          model: selectedModel,
          updatedAt: Date.now()
        },
        ...prev
      ]);
    } else {
      setSessions((prev) =>
        prev.map((s) =>
          s.thread_id === activeThreadId ? { ...s, messages: nextMessages, updatedAt: Date.now() } : s
        )
      );
    }

    const assistantMsgId = `ai-${Date.now()}`;
    let streamedText = '';
    let metaSource = 'Assistant';
    let metaDocs: RetrievedDoc[] = [];
    let metaProposal: any = null;
    let metaRequiresGoogleAuth = false;
    let msgInserted = false;
    setStreamingMsgId(assistantMsgId);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: textToSend,
          model: selectedModel,
          thread_id: activeThreadId
        }),
        signal: controller.signal
      });

      if (!response.ok || !response.body) throw new Error(`Server error ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;
          let evt: any;
          try {
            evt = JSON.parse(raw);
          } catch {
            continue;
          }

          if (evt.type === 'stage') {
            setCurrentStage(evt.stage);
            if (['thinking', 'searching', 'generating', 'success', 'error'].includes(evt.stage)) {
              setAvatarState(evt.stage as AvatarState);
            } else if (['searching_gmail', 'searching_emails', 'checking_calendar', 'searching_docs', 'searching_web', 'organizing_tasks', 'preparing_draft'].includes(evt.stage)) {
              setAvatarState('searching');
            }
          } else if (evt.type === 'meta') {
            metaSource = evt.source ?? 'Assistant';
            metaDocs = evt.retrieved_docs ?? [];
            if (evt.proposal) {
              metaProposal = evt.proposal;
            }
            if (evt.requires_google_auth) {
              metaRequiresGoogleAuth = true;
            }
            if (metaDocs.length > 0) {
              setAvatarState('searching');
            }
          } else if (evt.type === 'token') {
            streamedText += evt.text;
            setAvatarState('generating');

            if (!msgInserted) {
              const aiMsg: Message = {
                id: assistantMsgId,
                sender: 'assistant',
                text: streamedText,
                source: metaSource,
                retrievedDocs: metaDocs,
                proposal: metaProposal,
                requiresGoogleAuth: metaRequiresGoogleAuth,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              };
              setMessages([...nextMessages, aiMsg]);
              msgInserted = true;
              setIsLoading(false);
            } else {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? { ...m, text: streamedText, source: metaSource, retrievedDocs: metaDocs, proposal: metaProposal, requiresGoogleAuth: metaRequiresGoogleAuth }
                    : m
                )
              );
            }
          } else if (evt.type === 'done') {
            setAvatarState('success');
            setTimeout(() => {
              setAvatarState((curr) => (curr === 'success' ? 'idle' : curr));
            }, 2600);

            const finalMsg: Message = {
              id: assistantMsgId,
              sender: 'assistant',
              text: streamedText || 'No answer generated.',
              source: metaSource,
              retrievedDocs: metaDocs,
              proposal: metaProposal,
              requiresGoogleAuth: metaRequiresGoogleAuth,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            };
            setMessages((prev) => {
              const without = prev.filter((m) => m.id !== assistantMsgId);
              return [...without, finalMsg];
            });
            setSessions((prev) =>
              prev.map((s) =>
                s.thread_id === activeThreadId
                  ? { ...s, messages: [...nextMessages, finalMsg], updatedAt: Date.now() }
                  : s
              )
            );
            // Background sync session to backend SQLite
            fetch('/api/conversations', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                thread_id: activeThreadId,
                title: textToSend.slice(0, 36).trim() || 'New Conversation',
                model: selectedModel,
                messages: [...nextMessages, finalMsg],
              }),
            }).catch(() => {});
            setStreamingMsgId(null);
            setCurrentStage('');
          } else if (evt.type === 'error') {
            setCurrentStage('');
            setAvatarState('error');
            setTimeout(() => {
              setAvatarState((curr) => (curr === 'error' ? 'idle' : curr));
            }, 3500);

            const errMsg: Message = {
              id: assistantMsgId,
              sender: 'system',
              text: evt.text ?? 'Something went wrong.',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            };
            setMessages((prev) => [...prev.filter((m) => m.id !== assistantMsgId), errMsg]);
            setStreamingMsgId(null);
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        setStreamingMsgId(null);
        setAvatarState('idle');
        return;
      }
      setAvatarState('error');
      setTimeout(() => setAvatarState((curr) => (curr === 'error' ? 'idle' : curr)), 3500);
      const errMsg: Message = {
        id: assistantMsgId,
        sender: 'system',
        text: `Error contacting backend: ${err.message ?? 'Make sure server.py is running on port 8000.'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev.filter((m) => m.id !== assistantMsgId), errMsg]);
    } finally {
      setIsLoading(false);
      setStreamingMsgId(null);
      abortControllerRef.current = null;
    }
  };

  // Ingestion helpers
  const injectDocUploadMessage = (
    title: string,
    chunkCount: number,
    sourceType: 'file' | 'notes' | 'youtube',
    preview?: string
  ) => {
    const icons: Record<string, string> = { file: '📄', notes: '📝', youtube: '▶️' };
    const typeLabels: Record<string, string> = {
      file: 'File Uploaded',
      notes: 'Notes Pasted',
      youtube: 'YouTube Transcript'
    };
    const text = [
      `**${icons[sourceType]} ${typeLabels[sourceType]}: ${title}**`,
      `**${chunkCount} page${chunkCount !== 1 ? 's' : ''} • Docs Uploaded**. You can now ask questions about this document.`
    ].join('\n\n');

    const docMsg: Message = {
      id: `doc-${Date.now()}`,
      sender: 'system',
      text,
      source: 'Document Indexed',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      docMeta: { title, chunkCount, sourceType }
    };

    const updated = [...messages, docMsg];
    setMessages(updated);
    if (currentThreadId) {
      setSessions((prev) =>
        prev.map((s) => (s.thread_id === currentThreadId ? { ...s, messages: updated, updatedAt: Date.now() } : s))
      );
    }
  };

  // Direct file upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploadingFile(true);
    setUploadingFileName(file.name);
    setUploadProgress(15);
    setUploadStep('Reading and analyzing document...');
    setAvatarState('searching');

    let currentVal = 15;
    const progressInterval = setInterval(() => {
      if (currentVal < 45) {
        currentVal += 5;
        setUploadStep('Extracting content...');
      } else if (currentVal < 75) {
        currentVal += 3;
        setUploadStep('Organizing sections...');
      } else if (currentVal < 92) {
        currentVal += 1;
        setUploadStep('Indexing into knowledge base...');
      }
      setUploadProgress(currentVal);
    }, 110);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData
      });

      clearInterval(progressInterval);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.message || 'Upload failed');

      setUploadProgress(100);
      setUploadStep('Indexed into knowledge base successfully!');
      setAvatarState('success');
      showToast('success', `✓ Successfully indexed "${file.name}" into Knowledge Base!`);
      fetchDocs();
      injectDocUploadMessage(
        data.document?.title || file.name,
        data.document?.chunk_count || 0,
        'file',
        data.document?.preview
      );
      setTimeout(() => setAvatarState('idle'), 2500);
    } catch (err: any) {
      clearInterval(progressInterval);
      setAvatarState('error');
      setTimeout(() => setAvatarState('idle'), 3000);
      showToast('error', `Failed to upload: ${err.message}`);
    } finally {
      setIsUploadingFile(false);
      setUploadingFileName(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Text ingestion
  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!docTitle.trim() || !docContent.trim()) return;

    setIsSubmittingText(true);
    try {
      const res = await fetch('/api/documents/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: docTitle, content: docContent })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.message || 'Ingestion failed');

      showToast('success', `✓ Successfully indexed "${docTitle}" into Knowledge Base!`);
      setDocTitle('');
      setDocContent('');
      setActiveModal(null);
      fetchDocs();
      injectDocUploadMessage(
        data.document?.title || docTitle,
        data.document?.chunk_count || 0,
        'notes',
        data.document?.preview
      );
    } catch (err: any) {
      showToast('error', `Failed to add notes: ${err.message}`);
    } finally {
      setIsSubmittingText(false);
    }
  };

  // YouTube transcript ingestion
  const handleYouTubeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ytUrl.trim()) return;

    setIsSubmittingYt(true);
    try {
      const res = await fetch('/api/documents/youtube', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_url_or_id: ytUrl.trim(), title: ytTitle.trim() || undefined })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.message || 'Transcript fetch failed');

      showToast('success', `✓ Ingested transcript for "${data.document?.title || ytUrl}"!`);
      setYtUrl('');
      setYtTitle('');
      setActiveModal(null);
      fetchDocs();
      injectDocUploadMessage(
        data.document?.title || ytUrl,
        data.document?.chunk_count || 0,
        'youtube',
        data.document?.preview
      );
    } catch (err: any) {
      showToast('error', `YouTube ingestion failed: ${err.message}`);
    } finally {
      setIsSubmittingYt(false);
    }
  };

  const activeThread = sessions.find((s) => s.thread_id === currentThreadId);
  const currentTitle = activeThread ? activeThread.title : 'New Chat';

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      width: '100vw',
      backgroundColor: THEME.beigeBg,
      color: THEME.slateDark,
      fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      overflow: 'hidden'
    }}>
      {/* Hidden File Input for Document Upload */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        accept=".pdf,.txt,.docx,.md,.csv,.json"
        style={{ display: 'none' }}
      />

      {/* Toast Feedback Notification Banner */}
      {toastFeedback && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '24px',
          zIndex: 9999,
          padding: '10px 18px',
          borderRadius: '10px',
          backgroundColor: toastFeedback.type === 'success' ? '#10b981' : THEME.burgundy,
          color: '#ffffff',
          fontSize: '13px',
          fontWeight: 500,
          boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          animation: 'fadeIn 0.2s ease-out'
        }}>
          <span>{toastFeedback.message}</span>
        </div>
      )}

      {/* Sidebar Navigation */}
      <Sidebar
        isOpen={sidebarOpen}
        isMobile={isMobile}
        sessions={sessions}
        currentThreadId={currentThreadId}
        historySearchQuery={historySearchQuery}
        docs={documents}
        docsPanelOpen={docsPanelOpen}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        onNewChat={handleStartNewChat}
        onSelectThread={handleSelectThread}
        onChangeHistorySearch={setHistorySearchQuery}
        onRenameThread={handleRenameThread}
        onDeleteThread={handleDeleteThread}
        onToggleDocsPanel={() => setDocsPanelOpen(!docsPanelOpen)}
        onClearDocs={handleClearDocs}
        onTriggerFileUpload={() => fileInputRef.current?.click()}
      />

      {/* Main Content Area */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minWidth: 0,
        position: 'relative'
      }}>
        {/* Top Header Bar */}
        <TopBar
          sidebarOpen={sidebarOpen}
          currentThreadTitle={currentTitle}
          currentThreadId={currentThreadId}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          onOpenTaskManager={() => setTaskManagerOpen(true)}
          onOpenGoogleConnect={() => setGoogleConnectOpen(true)}
        />

        {/* Chat or Hero View */}
        {messages.length === 0 ? (
          <HeroWelcome
            avatarState={avatarState}
            onSetAvatarState={setAvatarState}
            onSelectPrompt={(prompt) => handleSendMessage(prompt)}
            onOpenGoogleConnect={() => setGoogleConnectOpen(true)}
            onTriggerFileUpload={() => fileInputRef.current?.click()}
            googleConnected={googleConnected}
            docsCount={documents.length}
          >
            {/* Ingestion Modals in Hero */}
            <TextModal
              isOpen={activeModal === 'text'}
              docTitle={docTitle}
              docContent={docContent}
              isSubmitting={isSubmittingText}
              onChangeTitle={setDocTitle}
              onChangeContent={setDocContent}
              onSubmit={handleTextSubmit}
              onClose={() => setActiveModal(null)}
            />
            <YouTubeModal
              isOpen={activeModal === 'youtube'}
              ytUrl={ytUrl}
              ytTitle={ytTitle}
              isSubmitting={isSubmittingYt}
              onChangeUrl={setYtUrl}
              onChangeTitle={setYtTitle}
              onSubmit={handleYouTubeSubmit}
              onClose={() => setActiveModal(null)}
            />

            {/* Composer in Hero */}
            <Composer
              inputMessage={inputMessage}
              selectedModel={selectedModel}
              isLoading={isLoading}
              streamingMsgId={streamingMsgId}
              isUploadingFile={isUploadingFile}
              uploadingFileName={uploadingFileName}
              uploadProgress={uploadProgress}
              uploadStep={uploadStep}
              isHero={true}
              plusMenuOpen={plusMenuOpen}
              modelDropdownOpen={modelDropdownOpen}
              onChangeInput={setInputMessage}
              onSendMessage={handleSendMessage}
              onStopGeneration={handleStopGeneration}
              onSelectModel={setSelectedModel}
              onTogglePlusMenu={() => setPlusMenuOpen(!plusMenuOpen)}
              onClosePlusMenu={() => setPlusMenuOpen(false)}
              onToggleModelDropdown={() => setModelDropdownOpen(!modelDropdownOpen)}
              onCloseModelDropdown={() => setModelDropdownOpen(false)}
              onTriggerFileUpload={() => fileInputRef.current?.click()}
              onOpenTextModal={() => setActiveModal('text')}
              onOpenYouTubeModal={() => setActiveModal('youtube')}
            />
          </HeroWelcome>
        ) : (
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            position: 'relative'
          }}>
            {/* Scrollable Message Thread */}
            <div
              ref={scrollContainerRef}
              onScroll={handleScroll}
              style={{
                flex: 1,
                overflowY: 'auto',
                padding: '24px 20px'
              }}
            >
              <div style={{
                maxWidth: '820px',
                width: '100%',
                margin: '0 auto',
                display: 'flex',
                flexDirection: 'column',
                gap: '24px'
              }}>
                {messages.map((msg, index) => (
                  <ChatMessage
                    key={msg.id || index}
                    msg={msg}
                    isLatest={index === messages.length - 1}
                    streamingMsgId={streamingMsgId}
                    avatarState={avatarState}
                    copiedMsgId={copiedMsgId}
                    likedMsgId={likedMap}
                    expandedDocs={expandedDocs}
                    highlightedChunk={highlightedChunk}
                    onCopy={handleCopy}
                    onRetry={handleRegenerate}
                    onLike={handleLike}
                    onDislike={handleDislike}
                    onToggleDocExpand={handleToggleDocExpand}
                    onJumpToChunk={handleJumpToChunk}
                    onSendFollowup={(q) => handleSendMessage(q)}
                    onOpenGoogleConnect={() => setGoogleConnectOpen(true)}
                    currentStage={streamingMsgId === msg.id ? currentStage : undefined}
                  />
                ))}

                {/* Real-time Thinking Dots with Procedural Avatar */}
                {(isLoading || Boolean(streamingMsgId)) && (!messages.length || messages[messages.length - 1]?.sender === 'user') && (
                  <ThinkingIndicator avatarState={avatarState} currentStage={currentStage} />
                )}

                <div ref={messagesEndRef} style={{ height: '12px' }} />
              </div>
            </div>

            {/* Bottom Docked Composer */}
            <div style={{
              padding: '12px 20px 20px',
              backgroundColor: THEME.beigeBg,
              borderTop: `1px solid ${THEME.beigeBorder}`
            }}>
              <div style={{ maxWidth: '820px', margin: '0 auto', width: '100%' }}>
                {/* Ingestion Modals Docked */}
                <TextModal
                  isOpen={activeModal === 'text'}
                  docTitle={docTitle}
                  docContent={docContent}
                  isSubmitting={isSubmittingText}
                  onChangeTitle={setDocTitle}
                  onChangeContent={setDocContent}
                  onSubmit={handleTextSubmit}
                  onClose={() => setActiveModal(null)}
                />
                <YouTubeModal
                  isOpen={activeModal === 'youtube'}
                  ytUrl={ytUrl}
                  ytTitle={ytTitle}
                  isSubmitting={isSubmittingYt}
                  onChangeUrl={setYtUrl}
                  onChangeTitle={setYtTitle}
                  onSubmit={handleYouTubeSubmit}
                  onClose={() => setActiveModal(null)}
                />

                <Composer
                  inputMessage={inputMessage}
                  selectedModel={selectedModel}
                  isLoading={isLoading}
                  streamingMsgId={streamingMsgId}
                  isUploadingFile={isUploadingFile}
                  uploadingFileName={uploadingFileName}
                  uploadProgress={uploadProgress}
                  uploadStep={uploadStep}
                  isHero={false}
                  plusMenuOpen={plusMenuOpen}
                  modelDropdownOpen={modelDropdownOpen}
                  onChangeInput={setInputMessage}
                  onSendMessage={handleSendMessage}
                  onStopGeneration={handleStopGeneration}
                  onSelectModel={setSelectedModel}
                  onTogglePlusMenu={() => setPlusMenuOpen(!plusMenuOpen)}
                  onClosePlusMenu={() => setPlusMenuOpen(false)}
                  onToggleModelDropdown={() => setModelDropdownOpen(!modelDropdownOpen)}
                  onCloseModelDropdown={() => setModelDropdownOpen(false)}
                  onTriggerFileUpload={() => fileInputRef.current?.click()}
                  onOpenTextModal={() => setActiveModal('text')}
                  onOpenYouTubeModal={() => setActiveModal('youtube')}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Global Modals for Personal AI Agent */}
      <React.Suspense fallback={null}>
        {taskManagerOpen && (
          <TaskManagerModal
            isOpen={taskManagerOpen}
            onClose={() => setTaskManagerOpen(false)}
          />
        )}
        {googleConnectOpen && (
          <GoogleConnectModal
            isOpen={googleConnectOpen}
            onClose={() => setGoogleConnectOpen(false)}
          />
        )}
      </React.Suspense>
    </div>
  );
}
