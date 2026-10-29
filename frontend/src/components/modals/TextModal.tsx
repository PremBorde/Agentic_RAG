import React from 'react';
import { FilePlus, X } from 'lucide-react';
import { THEME } from '../../constants/theme';

interface TextModalProps {
  isOpen: boolean;
  docTitle: string;
  docContent: string;
  isSubmitting: boolean;
  onChangeTitle: (title: string) => void;
  onChangeContent: (content: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onClose: () => void;
}

export function TextModal({
  isOpen,
  docTitle,
  docContent,
  isSubmitting,
  onChangeTitle,
  onChangeContent,
  onSubmit,
  onClose
}: TextModalProps) {
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
          <FilePlus size={15} />
          <span>Add Custom Text / Notes into FAISS</span>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close text modal"
          style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: THEME.slateMuted }}
        >
          <X size={15} />
        </button>
      </div>

      <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <input
          type="text"
          placeholder="Title (e.g. System Design Notes)"
          aria-label="Note Title"
          value={docTitle}
          onChange={(e) => onChangeTitle(e.target.value)}
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
        <textarea
          rows={4}
          placeholder="Paste text, notes, or article content to index..."
          aria-label="Note Content"
          value={docContent}
          onChange={(e) => onChangeContent(e.target.value)}
          required
          style={{
            padding: '8px 10px',
            borderRadius: '8px',
            border: `1px solid ${THEME.beigeBorderDark}`,
            fontSize: '12.5px',
            outline: 'none',
            color: THEME.slateDark,
            resize: 'vertical',
            fontFamily: 'inherit'
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
            disabled={isSubmitting || !docTitle.trim() || !docContent.trim()}
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
            {isSubmitting ? 'Ingesting...' : 'Ingest Document'}
          </button>
        </div>
      </form>
    </div>
  );
}

