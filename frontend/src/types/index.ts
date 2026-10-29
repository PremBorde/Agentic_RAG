export type AvatarState = 
  | 'idle' 
  | 'thinking' 
  | 'searching' 
  | 'generating' 
  | 'success' 
  | 'error' 
  | 'sleeping'
  | 'searching_emails'
  | 'checking_calendar'
  | 'organizing_tasks'
  | 'preparing_draft';

export interface RetrievedDoc {
  content: string;
  source: string;
  doc_id?: string;
}

export interface ActionProposal {
  action_id: string;
  action_type: 'send_email' | 'create_calendar_event' | 'update_calendar_event' | 'delete_calendar_event';
  summary: string;
  payload: Record<string, any>;
  status: 'pending' | 'completed' | 'cancelled' | 'failed';
}

export interface Message {
  id: string;
  sender: 'user' | 'assistant' | 'system';
  text: string;
  source?: string;
  retrievedDocs?: RetrievedDoc[];
  proposal?: ActionProposal;
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

export interface TaskItem {
  id: string;
  title: string;
  description: string;
  due_date?: string;
  priority: 'low' | 'medium' | 'high';
  status: 'pending' | 'completed';
  category: string;
  created_at: string;
  updated_at: string;
}

export interface MemoryItem {
  id: string;
  category: string;
  content: string;
  created_at: string;
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
