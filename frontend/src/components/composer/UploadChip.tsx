import React from 'react';
import { UploadCloud } from 'lucide-react';
import { THEME } from '../../constants/theme';

interface UploadChipProps {
  isUploading: boolean;
  fileName: string | null;
  progress: number;
  step: string;
}

export function UploadChip({
  isUploading,
  fileName,
  progress,
  step
}: UploadChipProps) {
  if (!isUploading) return null;

  return (
    <div style={{ marginBottom: '8px', display: 'flex' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: '10px',
        padding: '6px 12px 6px 8px',
        backgroundColor: '#ffffff',
        border: `1.5px solid ${THEME.burgundyBorder}`,
        borderRadius: '12px',
        maxWidth: '380px',
        width: '100%',
        boxShadow: '0 4px 14px rgba(122, 28, 48, 0.08)'
      }}>
        <div className="upload-cloud-pulse" style={{
          width: '24px',
          height: '24px',
          borderRadius: '6px',
          backgroundColor: THEME.burgundy,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0
        }}>
          <UploadCloud size={13} color="#fff" />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: THEME.burgundy, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {fileName || 'Uploading document...'}
            </span>
            <span style={{ fontSize: '11px', fontWeight: 600, color: progress < 100 ? THEME.burgundy : '#16a34a', whiteSpace: 'nowrap', flexShrink: 0 }}>
              {progress < 100 ? `${progress}%` : '✓ 100%'}
            </span>
          </div>
          {/* Dynamic Step Label */}
          <div style={{ fontSize: '10.5px', color: THEME.slateMuted, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginTop: '1px' }}>
            {step || 'Processing...'}
          </div>
          {/* Shimmering Animated Progress Bar */}
          <div style={{ height: '4px', backgroundColor: THEME.burgundyBorder, borderRadius: '4px', marginTop: '4px', overflow: 'hidden' }}>
            <div 
              className="upload-chip-bar"
              style={{ 
                height: '100%', 
                borderRadius: '4px', 
                width: `${progress}%`, 
                transition: 'width 0.25s cubic-bezier(0.4, 0, 0.2, 1)' 
              }} 
            />
          </div>
        </div>
      </div>
    </div>
  );
}

