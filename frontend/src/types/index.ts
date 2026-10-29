export type AvatarState = 'idle' | 'thinking' | 'searching' | 'generating' | 'success' | 'error' | 'sleeping';

export interface RetrievedDoc {
  content: string;
  source: string;
  doc_id?: string;
}

export interface Message {
  id: string;
  sender: 'user' | 'assistant' | 'system';
  text: string;
  source?: string;
  retrievedDocs?: RetrievedDoc[];
  timestamp: string;
  docMeta?: {
    title: string;
    chunkCount: number;
    sourceType: 'file' | 'notes' | 'youtube';
    preview?: string;
  };
}

export interface DocumentItem {
  id: string;
  title: string;
  source_type: string;
  chunk_count: number;
  created_at: string;
  preview: string;
  full_content: string;
}

export interface ChatSession {
  thread_id: string;
  title: string;
  messages: Message[];
  model: string;
  updatedAt: number;
}

export interface ToastFeedback {
  type: 'success' | 'error';
  message: string;
}

