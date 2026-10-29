import React, { useState } from 'react';
import { Check, X, Mail, Calendar, AlertCircle, Loader2 } from 'lucide-react';
import { ActionProposal } from '../../types';
import { THEME } from '../../constants/theme';

interface ActionProposalCardProps {
  proposal: ActionProposal;
  onActionComplete?: (actionId: string, status: 'completed' | 'cancelled', message?: string) => void;
}

export const ActionProposalCard: React.FC<ActionProposalCardProps> = ({
  proposal,
  onActionComplete
}) => {
  const [status, setStatus] = useState<'pending' | 'executing' | 'completed' | 'cancelled' | 'failed'>(
    proposal.status || 'pending'
  );
  const [statusMessage, setStatusMessage] = useState<string>('');

  const handleApprove = async () => {
    setStatus('executing');
    try {
      const res = await fetch(`/api/actions/${proposal.action_id}/approve`, {
        method: 'POST'
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setStatus('completed');
        const msg = data.result?.message || 'Action executed successfully.';
        setStatusMessage(msg);
        if (onActionComplete) onActionComplete(proposal.action_id, 'completed', msg);
      } else {
        setStatus('failed');
        setStatusMessage(data.error || 'Execution failed.');
      }
    } catch (err: any) {
      setStatus('failed');
      setStatusMessage(err.message || 'Network error.');
    }
  };

  const handleCancel = async () => {
    try {
      await fetch(`/api/actions/${proposal.action_id}/reject`, {
        method: 'POST'
      });
      setStatus('cancelled');
      setStatusMessage('Action proposal cancelled.');
      if (onActionComplete) onActionComplete(proposal.action_id, 'cancelled');
    } catch {
      setStatus('cancelled');
    }
  };

  const isEmail = proposal.action_type === 'send_email';
  const isCalendar = proposal.action_type === 'create_calendar_event';

  return (
    <div style={{
      marginTop: '12px',
      borderRadius: '12px',
      border: `1.5px solid ${THEME.burgundyBorder}`,
      backgroundColor: '#ffffff',
      padding: '14px 16px',
      boxShadow: '0 4px 14px rgba(122, 28, 48, 0.08)',
      fontSize: '13px',
      display: 'flex',
      flexDirection: 'column',
      gap: '10px'
    }}>
      {/* Header Pill */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingBottom: '8px',
        borderBottom: `1px solid ${THEME.beigeBorder}`
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: THEME.burgundy
          }} />
          <span style={{
            fontSize: '11px',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.4px',
            color: THEME.burgundy
          }}>
            Human Approval Required
          </span>
        </div>
        <span style={{ fontSize: '10.5px', color: THEME.slateLight, fontFamily: 'monospace' }}>
          ID: {proposal.action_id}
        </span>
      </div>

      {/* Summary */}
      <div style={{ fontSize: '13.5px', fontWeight: 650, color: THEME.slateDark }}>
        {proposal.summary}
      </div>

      {/* Details Box */}
      <div style={{
        borderRadius: '8px',
        backgroundColor: THEME.beigeBg,
        border: `1px solid ${THEME.beigeBorder}`,
        padding: '10px 12px',
        fontSize: '12px',
        color: THEME.slateDark,
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
      }}>
        {isEmail && (
          <>
            <div><strong style={{ color: THEME.burgundy }}>To:</strong> {proposal.payload.to}</div>
            <div><strong style={{ color: THEME.burgundy }}>Subject:</strong> {proposal.payload.subject}</div>
            <div style={{
              marginTop: '4px',
              paddingTop: '6px',
              borderTop: `1px dashed ${THEME.beigeBorder}`,
              fontFamily: 'serif',
              fontStyle: 'italic',
              color: THEME.slateMuted,
              whiteSpace: 'pre-wrap'
            }}>
              "{proposal.payload.body}"
            </div>
          </>
        )}

        {isCalendar && (
          <>
            <div><strong style={{ color: THEME.burgundy }}>Event:</strong> {proposal.payload.summary}</div>
            <div><strong style={{ color: THEME.burgundy }}>Start:</strong> {new Date(proposal.payload.start_time).toLocaleString()}</div>
            <div><strong style={{ color: THEME.burgundy }}>End:</strong> {new Date(proposal.payload.end_time).toLocaleString()}</div>
            {proposal.payload.description && (
              <div style={{ fontSize: '11px', color: THEME.slateMuted, marginTop: '2px' }}>
                {proposal.payload.description}
              </div>
            )}
          </>
        )}

        {!isEmail && !isCalendar && (
          <pre style={{ margin: 0, fontSize: '11px', fontFamily: 'monospace', overflowX: 'auto' }}>
            {JSON.stringify(proposal.payload, null, 2)}
          </pre>
        )}
      </div>

      {/* Result Status Badges */}
      {status === 'completed' && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '8px 12px',
          borderRadius: '8px',
          backgroundColor: '#ecfdf5',
          border: '1px solid #a7f3d0',
          color: '#065f46',
          fontSize: '12px',
          fontWeight: 600
        }}>
          <Check size={14} color="#059669" />
          <span>{statusMessage || 'Action approved and executed successfully.'}</span>
        </div>
      )}

      {status === 'cancelled' && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '8px 12px',
          borderRadius: '8px',
          backgroundColor: '#f3f4f6',
          border: '1px solid #e5e7eb',
          color: '#4b5563',
          fontSize: '12px',
          fontWeight: 600
        }}>
          <X size={14} color="#6b7280" />
          <span>Action was cancelled. No changes were made.</span>
        </div>
      )}

      {status === 'failed' && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '8px 12px',
          borderRadius: '8px',
          backgroundColor: '#fef2f2',
          border: '1px solid #fecaca',
          color: '#991b1b',
          fontSize: '12px'
        }}>
          <AlertCircle size={14} color="#dc2626" />
          <span>{statusMessage || 'Action failed to execute.'}</span>
        </div>
      )}

      {/* Control Buttons */}
      {status === 'pending' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
          <button
            type="button"
            onClick={handleApprove}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 14px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: THEME.burgundy,
              color: '#ffffff',
              fontSize: '12px',
              fontWeight: 650,
              cursor: 'pointer',
              boxShadow: '0 2px 6px rgba(122, 28, 48, 0.2)'
            }}
          >
            <Check size={13} />
            Approve & Execute
          </button>
          <button
            type="button"
            onClick={handleCancel}
            style={{
              padding: '7px 12px',
              borderRadius: '8px',
              border: `1px solid ${THEME.beigeBorderDark}`,
              backgroundColor: 'transparent',
              color: THEME.slateMuted,
              fontSize: '12px',
              fontWeight: 500,
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
        </div>
      )}

      {status === 'executing' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: THEME.burgundy, fontWeight: 600 }}>
          <Loader2 size={14} className="animate-spin" />
          Executing approved action...
        </div>
      )}
    </div>
  );
};
