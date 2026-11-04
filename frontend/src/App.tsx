import React, { useState, useEffect, useRef, useCallback } from 'react';
import '@bible-strong/avatar-react/styles.css';
import { 
  RetrievedDoc, 
  Message, 
  DocumentItem, 
  ChatSession, 
  AvatarState, 
  ToastFeedback,
  ImageItem
} from './types';
import { THEME } from './constants/theme';
import { UploadCloud, ChevronDown, CheckCircle2, AlertCircle, LogOut, X } from 'lucide-react';
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

function deduplicateMessages(msgs: Message[]): Message[] {
  const seen = new Set<string>();
  const out: Message[] = [];
  for (const m of msgs) {
    if (!m.id) {
      out.push(m);
    } else if (!seen.has(m.id)) {
      seen.add(m.id);
      out.push(m);
    }
  }
  return out;
}

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
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const dragCounter = useRef(0);

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
  const [selectedModel, setSelectedModel] = useState('gemini-2.5-flash');
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
  const isNearBottomRef = useRef<boolean>(true);
  const userScrolledUpRef = useRef<boolean>(false);
  const scrollRafIdRef = useRef<number | null>(null);

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
                    msgs = deduplicateMessages(mData.messages || []);
                  }
                } catch {}
                return {
                  thread_id: c.id,
                  title: c.title,
                  messages: msgs,
                  model: c.model || 'gemini-2.5-flash',
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

  // Jitter-free scroll pinning coordinator using requestAnimationFrame
  const pinScrollToBottom = useCallback(() => {
    if (!isNearBottomRef.current) return;
    if (scrollRafIdRef.current !== null) return;

    scrollRafIdRef.current = requestAnimationFrame(() => {
      scrollRafIdRef.current = null;
      const el = scrollContainerRef.current;
      if (el && isNearBottomRef.current) {
        el.scrollTop = el.scrollHeight;
      }
    });
  }, []);

  // Programmatic scroll to bottom (e.g. user submitted a message or clicked "Scroll to bottom" pill)
  const scrollToBottom = useCallback((smooth = true) => {
    isNearBottomRef.current = true;
    userScrolledUpRef.current = false;
    setUserScrolledUp(false);
    const el = scrollContainerRef.current;
    if (el) {
      if (smooth) {
        el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
      } else {
        el.scrollTop = el.scrollHeight;
      }
    }
  }, []);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    const distanceFromBottom = target.scrollHeight - target.scrollTop - target.clientHeight;
    // Comfortable threshold (140px) to distinguish active reading above vs bottom-docked viewing
    const isNear = distanceFromBottom <= 140;
    isNearBottomRef.current = isNear;
    userScrolledUpRef.current = !isNear;

    setUserScrolledUp((prev) => {
      const next = !isNear;
      return prev !== next ? next : prev;
    });
  }, []);

  const toastTimerRef = useRef<any>(null);

  const showToast = useCallback((type: 'success' | 'error' | 'info', message: string) => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToastFeedback({ type, message });
    toastTimerRef.current = setTimeout(() => {
      setToastFeedback(null);
    }, 4000);
  }, []);

  // Chat Actions (memoized to eliminate unnecessary re-renders of historical messages)
  const handleCopy = useCallback((id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedMsgId(id);
    setTimeout(() => setCopiedMsgId(null), 2000);
  }, []);

  const handleLike = useCallback((id: string) => {
    setLikedMap((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  const handleDislike = useCallback((id: string) => {
    setLikedMap((prev) => ({ ...prev, [id]: false }));
  }, []);

  const handleToggleDocExpand = useCallback((id: string) => {
    setExpandedDocs((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  const handleJumpToChunk = useCallback((msgId: string, chunkIdx: number) => {
    setExpandedDocs((prev) => ({ ...prev, [msgId]: true }));
    const targetId = `chunk-${msgId}-${chunkIdx}`;
    setHighlightedChunk(targetId);

    setTimeout(() => {
      const el = document.getElementById(targetId);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 120);

    setTimeout(() => setHighlightedChunk(null), 3200);
  }, []);

  const handleStopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setStreamingMsgId(null);
    setAvatarState('idle');
  }, []);

  const handleStartNewChat = () => {
    setCurrentThreadId(null);
    setMessages([]);
    setInputMessage('');
    setPlusMenuOpen(false);
    setActiveModal(null);
    const params = new URLSearchParams(window.location.search);
    if (params.has('thread_id')) {
      params.delete('thread_id');
      const qs = params.toString();
      window.history.replaceState({}, '', `${window.location.pathname}${qs ? `?${qs}` : ''}${window.location.hash}`);
    }
  };

  const handleSelectThread = async (threadId: string) => {
    const sess = sessions.find((s) => s.thread_id === threadId);
    if (sess) {
      setCurrentThreadId(sess.thread_id);
      setMessages(sess.messages || []);
      if (sess.model) {
        const validModel = ['gemini-2.5-flash', 'gemini-2.5-flash-lite', 'gemini-3.5-flash-lite'].includes(sess.model)
          ? sess.model
          : 'gemini-2.5-flash';
        setSelectedModel(validModel);
      }
    } else {
      setCurrentThreadId(threadId);
    }
    setPlusMenuOpen(false);
    setActiveModal(null);

    // Sync active thread_id into browser URL bar
    const params = new URLSearchParams(window.location.search);
    if (params.get('thread_id') !== threadId) {
      params.set('thread_id', threadId);
      window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}${window.location.hash}`);
    }

    // Hydrate fresh message history from backend
    try {
      const res = await fetch(`/api/conversations/${threadId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.messages && Array.isArray(data.messages)) {
          setMessages(deduplicateMessages(data.messages));
          setSessions((prev) => {
            const exists = prev.some((s) => s.thread_id === threadId);
            if (exists) {
              return prev.map((s) => (s.thread_id === threadId ? { ...s, messages: data.messages } : s));
            } else {
              return [
                {
                  thread_id: threadId,
                  title: data.conversation?.title || 'Chat',
                  messages: data.messages,
                  model: data.conversation?.model || 'gemini-2.5-flash',
                  updatedAt: new Date(data.conversation?.updated_at || Date.now()).getTime() || Date.now(),
                },
                ...prev
              ];
            }
          });
        }
      }
    } catch {}
  };

  // Restore conversation from URL or sessionStorage (e.g. after OAuth redirect or page refresh)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const threadIdParam = params.get('thread_id');
    const connectedParam = params.get('connected');
    const disconnectedParam = params.get('disconnected');
    const oauthErrorParam = params.get('oauth_error');

    let targetThreadId = threadIdParam;
    if (!targetThreadId) {
      try {
        const stored = sessionStorage.getItem('oauth_return_thread_id');
        if (stored) targetThreadId = stored;
      } catch {}
    }
    try {
      sessionStorage.removeItem('oauth_return_thread_id');
    } catch {}

    if (connectedParam === 'true') {
      showToast('success', 'Google account successfully connected.');
      setGoogleConnected(true);
      checkGoogleStatus();
    } else if (disconnectedParam === 'true') {
      showToast('info', 'Google account disconnected.');
      setGoogleConnected(false);
      checkGoogleStatus();
    } else if (oauthErrorParam) {
      showToast('error', `Google connection failed: ${decodeURIComponent(oauthErrorParam)}`);
    }

    if (connectedParam !== null || disconnectedParam !== null || oauthErrorParam !== null) {
      const cleanParams = new URLSearchParams(window.location.search);
      cleanParams.delete('connected');
      cleanParams.delete('disconnected');
      cleanParams.delete('oauth_error');
      if (targetThreadId) {
        cleanParams.set('thread_id', targetThreadId);
      }
      const qs = cleanParams.toString();
      const cleanUrl = `${window.location.pathname}${qs ? `?${qs}` : ''}${window.location.hash}`;
      window.history.replaceState({}, '', cleanUrl);
    }

    if (targetThreadId) {
      handleSelectThread(targetThreadId);
    }
  }, []);

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

  const handleDeleteDoc = async (docId: string, docTitle?: string) => {
    // Optimistic removal from frontend state
    setDocuments((prev) => prev.filter((d) => d.id !== docId && d.title !== docId));
    try {
      const res = await fetch(`/api/documents/${encodeURIComponent(docId)}`, { method: 'DELETE' });
      if (res.ok) {
        showToast('success', `Removed "${docTitle || docId}" from Knowledge Base.`);
      } else {
        // Fallback: try deleting by docTitle if distinct
        if (docTitle && docTitle !== docId) {
          const res2 = await fetch(`/api/documents/${encodeURIComponent(docTitle)}`, { method: 'DELETE' });
          if (res2.ok) {
            showToast('success', `Removed "${docTitle}" from Knowledge Base.`);
            return;
          }
        }
        showToast('error', 'Failed to remove document.');
        fetchDocs();
      }
    } catch (e) {
      console.error('Failed to delete document:', e);
      showToast('error', 'Failed to remove document.');
      fetchDocs();
    }
  };

  const handleClearDocs = async () => {
    setDocuments([]);
    try {
      const res = await fetch('/api/documents/clear', { method: 'DELETE' });
      if (res.ok) {
        showToast('success', 'Vector store cleared.');
      } else {
        await fetch('/api/documents/clear', { method: 'POST' });
        showToast('success', 'Vector store cleared.');
      }
    } catch (e) {
      console.error('Failed to clear documents:', e);
      showToast('error', 'Failed to clear documents.');
      fetchDocs();
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
      const params = new URLSearchParams(window.location.search);
      params.set('thread_id', activeThreadId);
      window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}${window.location.hash}`);
    }

    const userMsgId = `msg_user_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    const assistantMsgId = `msg_ai_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;

    const userMsg: Message = {
      id: userMsgId,
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInputMessage('');
    setUserScrolledUp(false);
    isNearBottomRef.current = true;
    userScrolledUpRef.current = false;
    setIsLoading(true);
    setAvatarState('thinking');
    setCurrentStage('thinking');

    // Smooth scroll down to reveal new user message and thinking indicator
    requestAnimationFrame(() => {
      scrollToBottom(true);
    });

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

    // assistantMsgId already generated synchronously
    let streamedText = '';
    let metaSource = 'Assistant';
    let metaDocs: RetrievedDoc[] = [];
    let metaImages: ImageItem[] = [];
    let metaProposal: any = null;
    let stagedProposal: any = null;
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
          message_id: userMsgId,
          assistant_message_id: assistantMsgId,
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
            pinScrollToBottom();
            if (evt.stage === 'greeting') {
              setAvatarState('thinking');
            } else if (['thinking', 'searching', 'generating', 'success', 'error'].includes(evt.stage)) {
              setAvatarState(evt.stage as AvatarState);
            } else if (['searching_gmail', 'searching_emails', 'checking_calendar', 'searching_docs', 'searching_web', 'searching_images', 'organizing_tasks', 'preparing_draft'].includes(evt.stage)) {
              setAvatarState('searching');
            }
          } else if (evt.type === 'meta') {
            metaSource = evt.source ?? 'Assistant';
            metaDocs = evt.retrieved_docs ?? [];
            if (evt.images) {
              metaImages = evt.images;
            }
            if (evt.proposal) {
              stagedProposal = evt.proposal;
            }
            if (evt.requires_google_auth) {
              metaRequiresGoogleAuth = true;
            }
            if (metaDocs.length > 0) {
              setAvatarState('searching');
            }
          } else if (evt.type === 'images') {
            if (evt.images) {
              metaImages = evt.images;
              pinScrollToBottom();
              if (msgInserted) {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId ? { ...m, images: metaImages } : m
                  )
                );
              }
            }
          } else if (evt.type === 'proposal') {
            metaProposal = evt.proposal;
            if (msgInserted) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId ? { ...m, proposal: metaProposal } : m
                )
              );
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
                images: metaImages,
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
                    ? { ...m, text: streamedText, source: metaSource, retrievedDocs: metaDocs, proposal: metaProposal, images: metaImages, requiresGoogleAuth: metaRequiresGoogleAuth }
                    : m
                )
              );
            }
            pinScrollToBottom();
          } else if (evt.type === 'done') {
            if (!metaProposal && stagedProposal) {
              metaProposal = stagedProposal;
            }
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
              images: metaImages,
              requiresGoogleAuth: metaRequiresGoogleAuth,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            };
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantMsgId ? finalMsg : m))
            );
            pinScrollToBottom();
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
        setIsLoading(false);
        setCurrentStage('');
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

  const handleRegenerate = useCallback(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].sender === 'user') {
        handleSendMessage(messages[i].text);
        return;
      }
    }
  }, [messages]);

  const handleSendFollowup = useCallback((q: string) => {
    handleSendMessage(q);
  }, []);

  const handleOpenGoogleConnect = useCallback(() => {
    setGoogleConnectOpen(true);
  }, []);

  const handleOpenDocsPanel = useCallback(() => {
    setSidebarOpen(true);
    setDocsPanelOpen(true);
  }, []);

  const handleOpenTaskManager = useCallback(() => {
    setTaskManagerOpen(true);
  }, []);

  const handleUploadFile = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

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

  // Upload a single file into the vector knowledge base
  const uploadSingleFile = async (file: File) => {
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
      showToast('error', `Failed to upload "${file.name}": ${err.message}`);
    } finally {
      setIsUploadingFile(false);
      setUploadingFileName(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Upload multiple files sequentially
  const uploadMultipleFiles = async (files: FileList | File[]) => {
    const fileArray = Array.from(files);
    if (!fileArray.length) return;
    for (const f of fileArray) {
      await uploadSingleFile(f);
    }
  };

  // Direct file input change (supports multi-selection)
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      await uploadMultipleFiles(e.target.files);
    }
  };

  // Global Drag and Drop event handlers
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer?.types && Array.from(e.dataTransfer.types).includes('Files')) {
      dragCounter.current += 1;
      setIsDraggingFile(true);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'copy';
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current -= 1;
    if (dragCounter.current <= 0) {
      dragCounter.current = 0;
      setIsDraggingFile(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current = 0;
    setIsDraggingFile(false);

    if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
      await uploadMultipleFiles(e.dataTransfer.files);
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
        multiple
        style={{ display: 'none' }}
      />

      {/* Studio Floating Toast Badge */}
      {toastFeedback && (
        <div 
          className="studio-toast-banner"
          style={{
            position: 'fixed',
            top: '20px',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 99999,
            display: 'flex',
            alignItems: 'center',
            gap: '9px',
            padding: '6px 14px 6px 8px',
            borderRadius: '9999px',
            backgroundColor: 'rgba(255, 255, 255, 0.96)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            border: toastFeedback.type === 'success' 
              ? '1px solid rgba(16, 185, 129, 0.35)' 
              : toastFeedback.type === 'error'
              ? '1px solid rgba(225, 29, 72, 0.35)'
              : '1px solid rgba(148, 163, 184, 0.35)',
            boxShadow: '0 12px 32px -4px rgba(24, 24, 27, 0.12), 0 4px 12px -2px rgba(24, 24, 27, 0.05)',
            maxWidth: '90vw',
            pointerEvents: 'auto'
          }}
        >
          {/* Leading Icon Avatar */}
          <div 
            style={{
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              backgroundColor: toastFeedback.type === 'success' 
                ? '#ecfdf5' 
                : toastFeedback.type === 'error'
                ? '#fff1f2'
                : '#f1f5f9'
            }}
          >
            {toastFeedback.type === 'success' ? (
              <CheckCircle2 size={13} color="#059669" strokeWidth={2.5} />
            ) : toastFeedback.type === 'error' ? (
              <AlertCircle size={13} color="#e11d48" strokeWidth={2.5} />
            ) : (
              <LogOut size={12} color="#475569" strokeWidth={2.2} />
            )}
          </div>

          {/* Badge Label (e.g. Success / Google / Notice) */}
          <span 
            style={{
              fontSize: '10px',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              padding: '2px 7px',
              borderRadius: '9999px',
              backgroundColor: toastFeedback.type === 'success'
                ? '#d1fae5'
                : toastFeedback.type === 'error'
                ? '#ffe4e6'
                : '#e2e8f0',
              color: toastFeedback.type === 'success'
                ? '#047857'
                : toastFeedback.type === 'error'
                ? '#be123c'
                : '#334155',
              flexShrink: 0
            }}
          >
            {toastFeedback.type === 'success' ? 'Success' : toastFeedback.type === 'error' ? 'Notice' : 'Google'}
          </span>

          {/* Message Text */}
          <span 
            style={{
              color: '#0f172a',
              fontSize: '12.5px',
              fontWeight: 550,
              letterSpacing: '-0.01em',
              lineHeight: 1.3,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}
          >
            {toastFeedback.message}
          </span>

          {/* Close Dismiss Button */}
          <button
            type="button"
            onClick={() => setToastFeedback(null)}
            aria-label="Dismiss notification"
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: '#94a3b8',
              padding: '3px',
              marginLeft: '2px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'color 0.15s ease, background-color 0.15s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = '#334155';
              e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.06)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = '#94a3b8';
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            <X size={13} strokeWidth={2.2} />
          </button>
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
        onDeleteDoc={handleDeleteDoc}
        onTriggerFileUpload={() => fileInputRef.current?.click()}
      />

      {/* Main Content Area with Direct Drag & Drop */}
      <div 
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          minWidth: 0,
          position: 'relative'
        }}
      >
        {/* Visual Drag & Drop Upload Overlay */}
        {isDraggingFile && (
          <div 
            style={{
              position: 'absolute',
              inset: '14px',
              zIndex: 2000,
              borderRadius: '20px',
              backgroundColor: 'rgba(253, 248, 246, 0.95)',
              backdropFilter: 'blur(8px)',
              WebkitBackdropFilter: 'blur(8px)',
              border: `2px dashed ${THEME.burgundy}`,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '16px',
              pointerEvents: 'none',
              boxShadow: '0 20px 50px rgba(122, 28, 48, 0.16)',
              animation: 'fadeSlideIn 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards'
            }}
          >
            <div style={{
              width: '76px',
              height: '76px',
              borderRadius: '50%',
              backgroundColor: '#fbf0f2',
              border: '2px solid #f0c2cc',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 8px 24px rgba(122, 28, 48, 0.12)'
            }}>
              <UploadCloud size={40} color={THEME.burgundy} style={{ animation: 'floatAnim 2s ease-in-out infinite' }} />
            </div>
            <div style={{ textAlign: 'center' }}>
              <h3 style={{
                fontFamily: "'Newsreader', 'Georgia', serif",
                fontSize: '24px',
                fontWeight: 650,
                color: THEME.burgundy,
                margin: '0 0 6px 0'
              }}>
                Drop files to index into Knowledge Base
              </h3>
              <p style={{
                fontSize: '13.5px',
                color: THEME.slateMuted,
                margin: 0
              }}>
                Release to immediately vectorize PDFs, TXT, DOCX, CSV, or Markdown
              </p>
            </div>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 14px',
              borderRadius: '20px',
              backgroundColor: '#ffffff',
              border: '1px solid #ebdcd3',
              fontSize: '11.5px',
              fontWeight: 600,
              color: THEME.slateDark,
              boxShadow: '0 2px 6px rgba(0,0,0,0.04)'
            }}>
              <span>✓ Instant RAG Indexing</span>
              <span>•</span>
              <span>Multi-file Drag & Drop</span>
            </div>
          </div>
        )}
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
                overflowAnchor: 'auto',
                padding: '24px 20px',
                contain: 'layout style'
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
                    key={msg.id || `msg-${index}`}
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
                    onSendFollowup={handleSendFollowup}
                    onOpenGoogleConnect={handleOpenGoogleConnect}
                    currentThreadId={currentThreadId}
                    onOpenDocsPanel={handleOpenDocsPanel}
                    onOpenTaskManager={handleOpenTaskManager}
                    onUploadFile={handleUploadFile}
                    currentStage={streamingMsgId === msg.id ? currentStage : undefined}
                  />
                ))}

                {/* Real-time Thinking Dots with Procedural Avatar */}
                {(isLoading || Boolean(streamingMsgId)) && (!messages.length || messages[messages.length - 1]?.sender === 'user') && (
                  <ThinkingIndicator avatarState={avatarState} currentStage={currentStage} />
                )}

                <div ref={messagesEndRef} style={{ height: '16px', flexShrink: 0 }} />
              </div>
            </div>

            {/* Floating "Scroll to bottom" button when user scrolled up during reading or streaming */}
            {userScrolledUp && (
              <button
                type="button"
                onClick={() => scrollToBottom(true)}
                className="scroll-to-bottom-pill"
                style={{
                  position: 'absolute',
                  bottom: '16px',
                  right: '28px',
                  zIndex: 20,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '7px 14px',
                  borderRadius: '20px',
                  backgroundColor: '#ffffff',
                  color: THEME.burgundy,
                  border: `1.5px solid ${THEME.burgundyBorder}`,
                  boxShadow: '0 4px 14px rgba(122, 28, 48, 0.16)',
                  fontSize: '12px',
                  fontWeight: 650,
                  cursor: 'pointer',
                  transition: 'all 0.18s ease'
                }}
                title="Scroll down to latest response"
              >
                <ChevronDown size={14} />
                <span>Scroll to bottom</span>
              </button>
            )}

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
            currentThreadId={currentThreadId}
          />
        )}
      </React.Suspense>
    </div>
  );
}
