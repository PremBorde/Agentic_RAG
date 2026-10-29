import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, Database, Globe, Sparkles, Mail, Calendar, CheckSquare, Brain } from 'lucide-react';
import { THEME } from '../../constants/theme';

export function getDisplaySourceBadge(source?: string): {
  label: string;
  icon: React.ReactNode;
  color: string;
  bg: string;
  border: string;
} | null {
  if (!source) return null;
  const s = source.toLowerCase().trim();

  // Hide tool/source badge for ordinary conversational replies, simple greetings, or responses that did not use a tool
  if (
    s === 'assistant' ||
    s.includes('conversational') ||
    s.includes('direct response') ||
    s === 'agent ready' ||
    s === 'unknown'
  ) {
    return null;
  }

  // Gmail
  if (s.includes('gmail') || s.includes('email')) {
    return {
      label: 'Gmail',
      icon: <Mail size={11} />,
      color: '#b3261e',
      bg: '#fdf2f2',
      border: '#f8d7da'
    };
  }

  // Google Calendar
  if (s.includes('calendar')) {
    return {
      label: 'Google Calendar',
      icon: <Calendar size={11} />,
      color: '#1a73e8',
      bg: '#eff6ff',
      border: '#bfdbfe'
    };
  }

  // Tasks & Reminders
  if (s.includes('task') || s.includes('reminder')) {
    return {
      label: 'Tasks & Reminders',
      icon: <CheckSquare size={11} />,
      color: '#047857',
      bg: '#f0fdf4',
      border: '#bbf7d0'
    };
  }

  // Long-Term Memory
  if (s.includes('memory')) {
    return {
      label: 'Long-Term Memory',
      icon: <Brain size={11} />,
      color: '#6d28d9',
      bg: '#f5f3ff',
      border: '#ddd6fe'
    };
  }

  // Document Search: Concise plain-language label for local vector retrieval
  if (s.includes('document') || s.includes('faiss') || s.includes('vector')) {
    return {
      label: 'Document Search',
      icon: <Database size={11} />,
      color: '#7a1c30',
      bg: '#fbf0f2',
      border: '#f2cbd3'
    };
  }

  // Web Search: Concise plain-language label for live web search
  if (s.includes('web') || s.includes('duckduckgo')) {
    return {
      label: 'Web Search',
      icon: <Globe size={11} />,
      color: '#1e242a',
      bg: '#f1ebdE',
      border: '#d5cbbe'
    };
  }

  // System Guidance
  if (s.includes('system') || s.includes('guidance')) {
    return {
      label: 'System Guidance',
      icon: <Sparkles size={11} />,
      color: '#5e6b7c',
      bg: '#f7f4ee',
      border: '#e5ded2'
    };
  }

  return null;
}

export function CodeBlock({ className, children, ...props }: any) {
  const match = /language-(\w+)/.exec(className || '');
  const language = match ? match[1] : '';
  const codeString = String(children).replace(/\n$/, '');
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(codeString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isInline = !match && !codeString.includes('\n');

  if (isInline) {
    return (
      <code
        style={{
          backgroundColor: '#f2ece2',
          color: THEME.burgundy,
          padding: '2px 6px',
          borderRadius: '4px',
          fontSize: '0.88em',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          fontWeight: 600
        }}
        {...props}
      >
        {children}
      </code>
    );
  }

  return (
    <div style={{
      margin: '12px 0',
      borderRadius: '8px',
      overflow: 'hidden',
      backgroundColor: '#1b2028',
      boxShadow: '0 4px 14px rgba(0,0,0,0.12)',
      border: '1px solid #28313b'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '6px 14px',
        backgroundColor: '#151921',
        borderBottom: '1px solid #28313b',
        color: '#9ba8b8',
        fontSize: '12px'
      }}>
        <span style={{ textTransform: 'lowercase', fontWeight: 500 }}>
          {language || 'code'}
        </span>
        <button
          onClick={handleCopy}
          type="button"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            background: 'transparent',
            border: 'none',
            color: copied ? '#4ade80' : '#c5d1de',
            fontSize: '11.5px',
            cursor: 'pointer',
            padding: '3px 8px',
            borderRadius: '5px',
            transition: 'all 0.15s ease'
          }}
          title="Copy code"
        >
          {copied ? <Check size={13} /> : <Copy size={13} />}
          <span>{copied ? 'Copied!' : 'Copy code'}</span>
        </button>
      </div>

      <pre style={{
        margin: 0,
        padding: '14px 16px',
        overflowX: 'auto',
        fontSize: '13px',
        lineHeight: 1.6,
        color: '#e6edf3',
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
        whiteSpace: 'pre'
      }}>
        <code>{codeString}</code>
      </pre>
    </div>
  );
}

interface MarkdownContentProps {
  content: string;
  isUser: boolean;
  isStreaming?: boolean;
  onCitationClick?: (chunkIndex: number) => void;
}

export function MarkdownContent({ 
  content, 
  isUser, 
  isStreaming,
  onCitationClick 
}: MarkdownContentProps) {
  if (isUser) {
    return <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{content}</div>;
  }

  const renderTextWithCitations = (children: React.ReactNode): React.ReactNode => {
    return React.Children.map(children, (child) => {
      if (typeof child !== 'string') return child;

      const parts: React.ReactNode[] = [];
      const regex = /\[(\d+)\]/g;
      let lastIndex = 0;
      let match: RegExpExecArray | null;

      while ((match = regex.exec(child)) !== null) {
        if (match.index > lastIndex) {
          parts.push(child.substring(lastIndex, match.index));
        }

        const num = parseInt(match[1], 10);
        const chunkIndex = num - 1;

        parts.push(
          <button
            key={`cit-${match.index}`}
            type="button"
            className="citation-badge"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onCitationClick?.(chunkIndex);
            }}
            title={`Jump to source chunk #${num}`}
            aria-label={`Jump to source chunk ${num}`}
          >
            [{num}]
          </button>
        );

        lastIndex = regex.lastIndex;
      }

      if (lastIndex < child.length) {
        parts.push(child.substring(lastIndex));
      }

      return parts.length > 0 ? parts : child;
    });
  };

  return (
    <div className={`prose-container ${isStreaming ? 'streaming-cursor' : ''}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code: CodeBlock,
          p: ({ children }) => (
            <p style={{ margin: '0 0 10px', lineHeight: 1.65, fontSize: '14.5px' }}>
              {renderTextWithCitations(children)}
            </p>
          ),
          li: ({ children }) => (
            <li style={{ margin: '4px 0', lineHeight: 1.6, fontSize: '14px' }}>
              {renderTextWithCitations(children)}
            </li>
          ),
          ul: ({ children }) => <ul style={{ paddingLeft: '22px', margin: '8px 0 12px' }}>{children}</ul>,
          ol: ({ children }) => <ol style={{ paddingLeft: '22px', margin: '8px 0 12px' }}>{children}</ol>,
          h1: ({ children }) => <h1 style={{ fontSize: '1.45em', fontWeight: 700, margin: '18px 0 10px', color: THEME.slateDark }}>{children}</h1>,
          h2: ({ children }) => <h2 style={{ fontSize: '1.25em', fontWeight: 650, margin: '16px 0 8px', color: THEME.slateDark }}>{children}</h2>,
          h3: ({ children }) => <h3 style={{ fontSize: '1.1em', fontWeight: 600, margin: '14px 0 6px', color: THEME.burgundy }}>{children}</h3>,
          table: ({ children }) => (
            <div style={{ overflowX: 'auto', margin: '14px 0', borderRadius: '8px', border: `1px solid ${THEME.beigeBorder}` }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th style={{ backgroundColor: THEME.beigeSurface, padding: '8px 12px', borderBottom: `2px solid ${THEME.beigeBorderDark}`, textAlign: 'left', fontWeight: 600, color: THEME.slateDark }}>
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td style={{ padding: '8px 12px', borderBottom: `1px solid ${THEME.beigeBorder}`, color: THEME.slateDark }}>
              {children}
            </td>
          ),
          blockquote: ({ children }) => (
            <blockquote style={{
              margin: '12px 0',
              padding: '8px 16px',
              borderLeft: `3px solid ${THEME.burgundy}`,
              backgroundColor: THEME.burgundySubtle,
              color: THEME.slateDark,
              borderRadius: '0 6px 6px 0',
              fontStyle: 'normal'
            }}>
              {children}
            </blockquote>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: THEME.burgundy, textDecoration: 'underline', fontWeight: 500 }}
            >
              {children}
            </a>
          )
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

