import React, { useState, useEffect } from 'react';
import { X, Mail, Calendar, CheckCircle2, AlertTriangle, ShieldCheck, ExternalLink } from 'lucide-react';
import { THEME } from '../../constants/theme';

interface GoogleConnectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStatusChanged?: () => void;
}

export const GoogleConnectModal: React.FC<GoogleConnectModalProps> = ({
  isOpen,
  onClose,
  onStatusChanged
}) => {
  const [status, setStatus] = useState<{ connected: boolean; email?: string | null }>({
    connected: false,
    email: null
  });
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/auth/google/status');
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch {
      // Ignored
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
      setErrorMsg('');
    }
  }, [isOpen]);

  const handleConnect = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await fetch('/api/auth/google/url');
      const data = await res.json();
      if (res.ok && data.url) {
        window.location.href = data.url;
      } else {
        setErrorMsg(data.detail || 'Google OAuth is not configured. Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env.');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start Google sign-in.');
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setLoading(true);
    try {
      await fetch('/api/auth/google/disconnect', { method: 'POST' });
      await fetchStatus();
      if (onStatusChanged) onStatusChanged();
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to disconnect.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
      <div className="w-full max-w-md rounded-2xl border border-[#e2d5c3] bg-[#faf7f2] shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#e8ded0] px-6 py-4 bg-[#f4ede1]">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#7a1c30] text-white">
              <Mail size={16} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-[#2c2226]">Google Workspace</h2>
              <p className="text-xs text-[#786b68]">Gmail & Google Calendar Integrations</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-[#786b68] hover:bg-[#ebdccf] transition-colors cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4 text-xs text-[#4a3e3d]">
          {/* Status Banner */}
          {status.connected ? (
            <div className="rounded-xl border border-[#a7f3d0] bg-[#ecfdf5] p-3.5 flex items-center gap-3 text-[#065f46]">
              <CheckCircle2 size={18} className="text-[#059669] shrink-0" />
              <div>
                <div className="font-semibold text-[13px]">Google Account Connected</div>
                <div className="text-[11px] text-[#047857]">{status.email || 'Authorized'}</div>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-[#fde68a] bg-[#fffbeb] p-3.5 flex items-center gap-3 text-[#92400e]">
              <AlertTriangle size={18} className="text-[#d97706] shrink-0" />
              <div>
                <div className="font-semibold text-[13px]">Not Connected</div>
                <div className="text-[11px] text-[#b45309]">Connect to search emails, read threads, and schedule events.</div>
              </div>
            </div>
          )}

          {errorMsg && (
            <div className="rounded-xl border border-[#fecaca] bg-[#fef2f2] p-3 text-[11px] text-[#b91c1c]">
              {errorMsg}
            </div>
          )}

          {/* Capabilities & Scopes List */}
          <div className="rounded-xl border border-[#e8ded0] bg-white/70 p-3.5 space-y-2">
            <div className="font-semibold text-[#2c2226] text-xs flex items-center gap-1.5">
              <ShieldCheck size={14} className="text-[#7a1c30]" /> Security & Permissions
            </div>
            <ul className="space-y-1.5 text-[11px] text-[#6e6360] list-disc list-inside">
              <li><strong>Gmail Read & Search:</strong> Inspect inbox and summarize email threads.</li>
              <li><strong>Drafting & Sending:</strong> Drafts are created safely; emails are sent <em>only</em> upon your explicit approval.</li>
              <li><strong>Calendar:</strong> Check free slots and propose meeting events.</li>
              <li>Tokens are held strictly on the backend and never exposed to the browser.</li>
            </ul>
          </div>

          {/* Action Buttons */}
          <div className="pt-2">
            {status.connected ? (
              <button
                onClick={handleDisconnect}
                disabled={loading}
                className="w-full rounded-xl border border-[#dc2626] bg-white py-2.5 font-semibold text-xs text-[#dc2626] hover:bg-[#fef2f2] transition-colors cursor-pointer disabled:opacity-50"
              >
                {loading ? 'Disconnecting...' : 'Disconnect Google Account'}
              </button>
            ) : (
              <button
                onClick={handleConnect}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-[#7a1c30] py-2.5 font-semibold text-xs text-white hover:bg-[#621626] transition-colors shadow-xs cursor-pointer disabled:opacity-50"
              >
                <ExternalLink size={14} />
                {loading ? 'Starting OAuth...' : 'Connect Google Account'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
