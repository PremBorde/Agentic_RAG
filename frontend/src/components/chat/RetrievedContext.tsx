import React from 'react';
import { FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { RetrievedDoc } from '../../types';
import { THEME } from '../../constants/theme';

interface RetrievedContextProps {
  messageId: string;
  docs: RetrievedDoc[];
  isExpanded: boolean;
  onToggle: (msgId: string) => void;
  highlightedChunk: string | null;
}

export function RetrievedContext({
  messageId,
  docs,
  isExpanded,
  onToggle,
  highlightedChunk
}: RetrievedContextProps) {
  if (!docs || docs.length === 0) return null;

  return (
    <div style={{ marginTop: '10px', borderTop: `1px solid ${THEME.beigeBorder}`, paddingTop: '8px' }}>
      <button
        type="button"
        onClick={() => onToggle(messageId)}
        aria-label="Toggle retrieved context accordion"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          background: 'transparent',
          border: 'none',
          color: THEME.burgundy,
          cursor: 'pointer',
          fontSize: '12px',
          fontWeight: '600',
          padding: '2px 0'
        }}
      >
        <FileText size={13} />
        <span>Inspect Actual Retrieved Context ({docs.length} chunk{docs.length !== 1 ? 's' : ''})</span>
        {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>

      {isExpanded && (
        <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {docs.map((doc, idx) => (
            <div 
              key={idx} 
              id={`chunk-${messageId}-${idx}`}
              className={highlightedChunk === `chunk-${messageId}-${idx}` ? 'chunk-target-highlight' : ''}
              style={{
                backgroundColor: '#f8f4ec',
                padding: '10px 14px',
                borderRadius: '10px',
                border: `1px solid ${THEME.beigeBorderDark}`,
                fontSize: '12.5px',
                transition: 'all 0.3s ease'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontWeight: 650, color: THEME.burgundy, display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <FileText size={12} />
                  {doc.source}
                </span>
                <span style={{ fontSize: '11px', color: THEME.slateMuted, backgroundColor: '#ece4d6', padding: '2px 7px', borderRadius: '6px' }}>
                  Chunk #{idx + 1}
                </span>
              </div>
              <div style={{
                color: THEME.slateDark,
                lineHeight: 1.55,
                fontSize: '12px',
                whiteSpace: 'pre-wrap',
                maxHeight: '180px',
                overflowY: 'auto',
                backgroundColor: '#ffffff',
                padding: '8px 10px',
                borderRadius: '6px',
                border: `1px solid ${THEME.beigeBorder}`
              }}>
                {doc.content}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

