import React, { useRef, useEffect } from 'react';
import { 
  ArrowUp, 
  Square, 
  Plus, 
  UploadCloud, 
  FilePlus, 
  Video, 
  ChevronDown, 
  Cpu 
} from 'lucide-react';
import { THEME, GEMINI_MODELS } from '../../constants/theme';
import { UploadChip } from './UploadChip';

interface ComposerProps {
  inputMessage: string;
  selectedModel: string;
  isLoading: boolean;
  streamingMsgId: string | null;
  isUploadingFile: boolean;
  uploadingFileName: string | null;
  uploadProgress: number;
  uploadStep: string;
  isHero?: boolean;
  plusMenuOpen: boolean;
  modelDropdownOpen: boolean;
  onChangeInput: (text: string) => void;
  onSendMessage: (overrideMsg?: string) => void;
  onStopGeneration: () => void;
  onSelectModel: (modelId: string) => void;
  onTogglePlusMenu: () => void;
  onClosePlusMenu: () => void;
  onToggleModelDropdown: () => void;
  onCloseModelDropdown: () => void;
  onTriggerFileUpload: () => void;
  onOpenTextModal: () => void;
  onOpenYouTubeModal: () => void;
}

export function Composer({
  inputMessage,
  selectedModel,
  isLoading,
  streamingMsgId,
  isUploadingFile,
  uploadingFileName,
  uploadProgress,
  uploadStep,
  isHero = false,
  plusMenuOpen,
  modelDropdownOpen,
  onChangeInput,
  onSendMessage,
  onStopGeneration,
  onSelectModel,
  onTogglePlusMenu,
  onClosePlusMenu,
  onToggleModelDropdown,
  onCloseModelDropdown,
  onTriggerFileUpload,
  onOpenTextModal,
  onOpenYouTubeModal
}: ComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [inputMessage]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSendMessage();
    }
  };

  const currentModelLabel = GEMINI_MODELS.find(m => m.id === selectedModel)?.label || selectedModel;

  return (
    <div style={{ width: '100%', position: 'relative' }}>
      {/* Upload Progress Chip */}
      <UploadChip 
        isUploading={isUploadingFile}
        fileName={uploadingFileName}
        progress={uploadProgress}
        step={uploadStep}
      />

      {/* Docked / Hero Rounded Composer Box */}
      <div 
        className="composer-container"
        style={{
          backgroundColor: '#ffffff',
          borderRadius: isHero ? '20px' : '16px',
          border: `1.5px solid ${isHero ? '#e7dfd5' : THEME.beigeBorderDark}`,
          boxShadow: isHero ? '0 10px 32px rgba(122, 28, 48, 0.05), 0 2px 8px rgba(0,0,0,0.03)' : '0 2px 14px rgba(0,0,0,0.05)',
          padding: isHero ? '14px 18px 12px' : '8px 14px 6px',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        <textarea
          ref={textareaRef}
          className="composer-textarea"
          rows={1}
          placeholder={isHero ? "Ask anything, query your documents, or search the web..." : "Ask a question or query your documents..."}
          aria-label="Ask a question or query your documents"
          value={inputMessage}
          onChange={(e) => onChangeInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          style={{
            width: '100%',
            border: 'none',
            outline: 'none',
            boxShadow: 'none',
            resize: 'none',
            fontSize: isHero ? '15px' : '14px',
            fontFamily: 'inherit',
            backgroundColor: 'transparent',
            color: THEME.slateDark,
            lineHeight: '1.5',
            minHeight: isHero ? '38px' : '22px',
            maxHeight: '120px',
            padding: '2px 0'
          }}
        />

        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingTop: isHero ? '10px' : '6px',
          borderTop: isHero ? 'none' : `1px solid ${THEME.beigeBorder}`
        }}>
          {/* Left: '+' Popover Trigger */}
          <div style={{ position: 'relative' }}>
            <button
              type="button"
              onClick={onTogglePlusMenu}
              aria-label="Add sources menu"
              title="Add sources (Upload, Notes, YouTube)"
              style={{
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                backgroundColor: plusMenuOpen ? THEME.burgundy : THEME.beigeSurface,
                color: plusMenuOpen ? '#ffffff' : THEME.slateDark,
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              <Plus size={16} strokeWidth={2.2} />
            </button>

            {/* '+' Popover Menu */}
            {plusMenuOpen && (
              <div 
                style={{
                  position: 'absolute',
                  bottom: isHero ? 'auto' : '36px',
                  top: isHero ? '36px' : 'auto',
                  left: 0,
                  backgroundColor: '#ffffff',
                  border: `1px solid ${THEME.beigeBorderDark}`,
                  borderRadius: '12px',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
                  padding: '6px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '2px',
                  zIndex: 80,
                  width: '210px'
                }}
              >
                <button
                  type="button"
                  onClick={() => {
                    onClosePlusMenu();
                    onTriggerFileUpload();
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '8px 10px',
                    borderRadius: '8px',
                    background: 'transparent',
                    border: 'none',
                    color: THEME.slateDark,
                    fontSize: '12.5px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = THEME.beigeSurface}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <UploadCloud size={15} color={THEME.burgundy} />
                  <span>Upload Document</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    onClosePlusMenu();
                    onOpenTextModal();
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '8px 10px',
                    borderRadius: '8px',
                    background: 'transparent',
                    border: 'none',
                    color: THEME.slateDark,
                    fontSize: '12.5px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = THEME.beigeSurface}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <FilePlus size={15} color={THEME.burgundy} />
                  <span>Add Notes / Text</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    onClosePlusMenu();
                    onOpenYouTubeModal();
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '8px 10px',
                    borderRadius: '8px',
                    background: 'transparent',
                    border: 'none',
                    color: THEME.slateDark,
                    fontSize: '12.5px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = THEME.beigeSurface}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <Video size={15} color={THEME.burgundy} />
                  <span>YouTube Transcript</span>
                </button>
              </div>
            )}
          </div>

          {/* Right: Model Dropdown & Send/Stop Button */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {/* Model Selector Popover */}
            <div style={{ position: 'relative' }}>
              <button
                type="button"
                onClick={onToggleModelDropdown}
                aria-label="Model selector"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '3px 9px',
                  borderRadius: '10px',
                  backgroundColor: THEME.beigeSurface,
                  color: THEME.slateDark,
                  border: `1px solid ${THEME.beigeBorderDark}`,
                  fontSize: '11.5px',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <span>{currentModelLabel}</span>
                <ChevronDown size={11} color={THEME.slateMuted} />
              </button>

              {modelDropdownOpen && (
                <div 
                  style={{
                    position: 'absolute',
                    bottom: isHero ? 'auto' : '32px',
                    top: isHero ? '32px' : 'auto',
                    right: 0,
                    backgroundColor: '#ffffff',
                    border: `1px solid ${THEME.beigeBorderDark}`,
                    borderRadius: '12px',
                    boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
                    padding: '4px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '2px',
                    zIndex: 80,
                    width: '185px'
                  }}
                >
                  <div style={{ padding: '6px 8px 4px', fontSize: '10px', fontWeight: 700, color: THEME.slateMuted, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                    Select Gemini Model
                  </div>
                  {GEMINI_MODELS.map((m) => (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => {
                        onSelectModel(m.id);
                        onCloseModelDropdown();
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '6px 8px',
                        borderRadius: '6px',
                        background: selectedModel === m.id ? THEME.burgundySubtle : 'transparent',
                        border: 'none',
                        color: selectedModel === m.id ? THEME.burgundy : THEME.slateDark,
                        fontSize: '12px',
                        fontWeight: selectedModel === m.id ? 600 : 400,
                        cursor: 'pointer',
                        textAlign: 'left'
                      }}
                      onMouseEnter={(e) => {
                        if (selectedModel !== m.id) e.currentTarget.style.backgroundColor = THEME.beigeSurface;
                      }}
                      onMouseLeave={(e) => {
                        if (selectedModel !== m.id) e.currentTarget.style.backgroundColor = 'transparent';
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Cpu size={12} color={selectedModel === m.id ? THEME.burgundy : THEME.slateMuted} />
                        <span>{m.label}</span>
                      </div>
                      {selectedModel === m.id && (
                        <div style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: THEME.burgundy }} />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Send or Stop Button */}
            {isLoading || streamingMsgId ? (
              <button
                type="button"
                onClick={onStopGeneration}
                title="Stop generating"
                aria-label="Stop generation"
                style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  backgroundColor: THEME.burgundy,
                  color: '#ffffff',
                  border: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  boxShadow: '0 2px 6px rgba(122, 28, 48, 0.3)'
                }}
              >
                <Square size={11} fill="#ffffff" />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => onSendMessage()}
                disabled={!inputMessage.trim()}
                title="Send message"
                aria-label="Send message"
                style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  backgroundColor: inputMessage.trim() ? THEME.burgundy : THEME.beigeSurfaceDark,
                  color: inputMessage.trim() ? '#ffffff' : THEME.slateLight,
                  border: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: inputMessage.trim() ? 'pointer' : 'default',
                  transition: 'background-color 0.15s ease'
                }}
              >
                <ArrowUp size={15} strokeWidth={2.5} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

