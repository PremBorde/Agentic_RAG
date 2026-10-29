import React from 'react';
import { Video, X } from 'lucide-react';
import { THEME } from '../../constants/theme';

interface YouTubeModalProps {
  isOpen: boolean;
  ytUrl: string;
  ytTitle: string;
  isSubmitting: boolean;
  onChangeUrl: (url: string) => void;
  onChangeTitle: (title: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onClose: () => void;
}

export function YouTubeModal({
  isOpen,
  ytUrl,
  ytTitle,
  isSubmitting,
  onChangeUrl,
  onChangeTitle,
  onSubmit,
  onClose
}: YouTubeModalProps) {
  if (!isOpen) return null;

  return (
    <div style={{
      marginBottom: '10px',
      backgroundColor: '#ffffff',
      border: `1.5px solid ${THEME.burgundyBorder}`,
      borderRadius: '14px',
      padding: '14px 16px',
      boxShadow: '0 8px 24px rgba(122, 28, 48, 0.08)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: 600, color: THEME.burgundy }}>
          <Video size={15} />
          <span>Index YouTube Video Transcript into Knowledge Base</span>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close YouTube modal"
          style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: THEME.slateMuted }}
        >
          <X size={15} />
        </button>
      </div>

      <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <input
          type="url"
          placeholder="https://www.youtube.com/watch?v=..."
          aria-label="YouTube URL"
          value={ytUrl}
          onChange={(e) => onChangeUrl(e.target.value)}
          required
          style={{
            padding: '7px 10px',
            borderRadius: '8px',
            border: `1px solid ${THEME.beigeBorderDark}`,
            fontSize: '13px',
            outline: 'none',
            color: THEME.slateDark
          }}
        />
        <input
          type="text"
          placeholder="Custom Title (optional, e.g. LangChain 101 Lecture)"
          aria-label="Video Title"
          value={ytTitle}
          onChange={(e) => onChangeTitle(e.target.value)}
          style={{
            padding: '7px 10px',
            borderRadius: '8px',
            border: `1px solid ${THEME.beigeBorderDark}`,
            fontSize: '13px',
            outline: 'none',
            color: THEME.slateDark
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '4px' }}>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '6px 12px',
              borderRadius: '8px',
              border: `1px solid ${THEME.beigeBorderDark}`,
              backgroundColor: 'transparent',
              color: THEME.slateMuted,
              fontSize: '12px',
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting || !ytUrl.trim()}
            style={{
              padding: '6px 14px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: THEME.burgundy,
              color: '#ffffff',
              fontSize: '12.5px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            {isSubmitting ? 'Fetching Transcript...' : 'Index Video'}
          </button>
        </div>
      </form>
    </div>
  );
}

