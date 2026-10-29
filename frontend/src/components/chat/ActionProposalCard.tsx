import React, { useState } from 'react';
import { ActionProposal } from '../../types';

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
    <div className="mt-4 rounded-xl border border-[#e2d5c3] bg-[#fffefb] p-4.5 shadow-sm text-sm font-sans transition-all">
      {/* Header Badge */}
      <div className="flex items-center justify-between pb-3 border-b border-[#f0e6d8]">
        <div className="flex items-center gap-2">
          <span className="flex h-2.5 w-2.5 rounded-full bg-[#b84b5f] animate-pulse"></span>
          <span className="text-xs font-semibold uppercase tracking-wider text-[#7a1c30]">
            Action Proposal Requires Approval
          </span>
        </div>
        <span className="text-[11px] text-[#8c827a] font-mono">
          ID: {proposal.action_id}
        </span>
      </div>

      {/* Action Title */}
      <div className="pt-3 font-semibold text-[#2c2226] text-base">
        {proposal.summary}
      </div>

      {/* Details Box */}
      <div className="mt-3 rounded-lg bg-[#faf7f2] border border-[#eee5d8] p-3 text-[13px] text-[#4a3e3d] space-y-1.5">
        {isEmail && (
          <>
            <div><span className="font-semibold text-[#7a1c30]">To:</span> {proposal.payload.to}</div>
            <div><span className="font-semibold text-[#7a1c30]">Subject:</span> {proposal.payload.subject}</div>
            <div className="pt-1.5 border-t border-[#ebdccf] text-[#332b2b] whitespace-pre-wrap font-serif italic text-xs leading-relaxed">
              "{proposal.payload.body}"
            </div>
          </>
        )}

        {isCalendar && (
          <>
            <div><span className="font-semibold text-[#7a1c30]">Event:</span> {proposal.payload.summary}</div>
            <div><span className="font-semibold text-[#7a1c30]">Start Time:</span> {new Date(proposal.payload.start_time).toLocaleString()}</div>
            <div><span className="font-semibold text-[#7a1c30]">End Time:</span> {new Date(proposal.payload.end_time).toLocaleString()}</div>
            {proposal.payload.description && (
              <div className="text-xs text-[#6e6360] pt-1">
                {proposal.payload.description}
              </div>
            )}
          </>
        )}

        {!isEmail && !isCalendar && (
          <pre className="text-xs overflow-x-auto font-mono text-[#5a4e4d]">
            {JSON.stringify(proposal.payload, null, 2)}
          </pre>
        )}
      </div>

      {/* Execution Feedback / Status Alert */}
      {status === 'completed' && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-[#ecfdf5] border border-[#a7f3d0] px-3 py-2 text-xs font-medium text-[#065f46]">
          <svg className="w-4 h-4 text-[#059669]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span>{statusMessage || 'Action confirmed and executed successfully.'}</span>
        </div>
      )}

      {status === 'cancelled' && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-[#f3f4f6] border border-[#e5e7eb] px-3 py-2 text-xs font-medium text-[#4b5563]">
          <svg className="w-4 h-4 text-[#6b7280]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
          <span>Action was cancelled. No changes were made.</span>
        </div>
      )}

      {status === 'failed' && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-[#fef2f2] border border-[#fecaca] px-3 py-2 text-xs font-medium text-[#991b1b]">
          <span>✕ {statusMessage || 'Action failed to execute.'}</span>
        </div>
      )}

      {/* Approval Buttons */}
      {status === 'pending' && (
        <div className="mt-4 flex items-center gap-2.5">
          <button
            onClick={handleApprove}
            className="flex items-center gap-1.5 rounded-lg bg-[#7a1c30] px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-[#621626] transition-colors cursor-pointer"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
            Approve & Execute
          </button>
          <button
            onClick={handleCancel}
            className="rounded-lg border border-[#d8ccc0] bg-white px-3.5 py-2 text-xs font-medium text-[#5c4f4e] hover:bg-[#faf7f2] transition-colors cursor-pointer"
          >
            Cancel
          </button>
        </div>
      )}

      {status === 'executing' && (
        <div className="mt-3 flex items-center gap-2 text-xs text-[#7a1c30] font-medium">
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
          </svg>
          Executing approved action...
        </div>
      )}
    </div>
  );
};
