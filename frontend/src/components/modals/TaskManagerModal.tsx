import React, { useState, useEffect } from 'react';
import { X, CheckSquare, Plus, Trash2, Calendar, AlertCircle } from 'lucide-react';
import { TaskItem } from '../../types';
import { THEME } from '../../constants/theme';

interface TaskManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const TaskManagerModal: React.FC<TaskManagerModalProps> = ({ isOpen, onClose }) => {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [filter, setFilter] = useState<'all' | 'pending' | 'completed' | 'overdue'>('all');
  const [newTitle, setNewTitle] = useState('');
  const [newPriority, setNewPriority] = useState<'low' | 'medium' | 'high'>('medium');
  const [newDueDate, setNewDueDate] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/tasks');
      if (res.ok) {
        const data = await res.json();
        setTasks(data);
      }
    } catch (e) {
      console.error('Failed to load tasks:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchTasks();
    }
  }, [isOpen]);

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    try {
      const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newTitle.trim(),
          priority: newPriority,
          due_date: newDueDate || null
        })
      });
      if (res.ok) {
        setNewTitle('');
        setNewDueDate('');
        fetchTasks();
      }
    } catch (e) {
      console.error('Failed to add task:', e);
    }
  };

  const handleToggleComplete = async (taskId: string, currentStatus: string) => {
    try {
      if (currentStatus === 'completed') {
        await fetch(`/api/tasks/${taskId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 'pending' })
        });
      } else {
        await fetch(`/api/tasks/${taskId}/complete`, { method: 'POST' });
      }
      fetchTasks();
    } catch (e) {
      console.error('Failed to update task:', e);
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    try {
      await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
      fetchTasks();
    } catch (e) {
      console.error('Failed to delete task:', e);
    }
  };

  if (!isOpen) return null;

  const todayStr = new Date().toISOString().split('T')[0];
  const filteredTasks = tasks.filter((t) => {
    if (filter === 'pending') return t.status === 'pending';
    if (filter === 'completed') return t.status === 'completed';
    if (filter === 'overdue') return t.status === 'pending' && t.due_date && t.due_date < todayStr;
    return true;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
      <div className="w-full max-w-xl rounded-2xl border border-[#e2d5c3] bg-[#faf7f2] shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-[#e8ded0] px-6 py-4 bg-[#f4ede1]">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#7a1c30] text-white">
              <CheckSquare size={16} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-[#2c2226]">Tasks & Reminders</h2>
              <p className="text-xs text-[#786b68]">Manage your AI-assisted to-dos and deadlines</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-[#786b68] hover:bg-[#ebdccf] transition-colors cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Task Creator Form */}
        <form onSubmit={handleCreateTask} className="border-b border-[#e8ded0] p-4 bg-white/70 space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Add a new task (e.g. Finish RAG presentation)..."
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="flex-1 rounded-xl border border-[#d8ccc0] bg-white px-3.5 py-2 text-xs text-[#2c2226] focus:outline-none focus:border-[#7a1c30]"
            />
            <button
              type="submit"
              disabled={!newTitle.trim()}
              className="flex items-center gap-1.5 rounded-xl bg-[#7a1c30] px-4 py-2 text-xs font-semibold text-white hover:bg-[#621626] transition-colors disabled:opacity-50 cursor-pointer"
            >
              <Plus size={14} /> Add
            </button>
          </div>
          <div className="flex items-center gap-3 text-xs text-[#6e6360]">
            <div className="flex items-center gap-1.5">
              <span>Priority:</span>
              <select
                value={newPriority}
                onChange={(e: any) => setNewPriority(e.target.value)}
                className="rounded-lg border border-[#d8ccc0] bg-white px-2 py-1 text-xs text-[#2c2226] focus:outline-none"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <div className="flex items-center gap-1.5">
              <Calendar size={13} />
              <span>Due:</span>
              <input
                type="date"
                value={newDueDate}
                onChange={(e) => setNewDueDate(e.target.value)}
                className="rounded-lg border border-[#d8ccc0] bg-white px-2 py-1 text-xs text-[#2c2226] focus:outline-none"
              >
              </input>
            </div>
          </div>
        </form>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 px-6 pt-3 pb-1 border-b border-[#ede4d7] bg-[#faf7f2]">
          {(['all', 'pending', 'overdue', 'completed'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors cursor-pointer ${
                filter === tab
                  ? 'bg-[#7a1c30] text-white shadow-xs'
                  : 'bg-[#eee5d8] text-[#5e5250] hover:bg-[#e4d8c8]'
              }`}
            >
              {tab}
            </button>
          ))}
          <span className="ml-auto text-[11px] text-[#8c807e]">
            {filteredTasks.length} task{filteredTasks.length === 1 ? '' : 's'}
          </span>
        </div>

        {/* Task Items List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {filteredTasks.length === 0 ? (
            <div className="py-8 text-center text-xs text-[#8c807e]">
              No tasks found in this view.
            </div>
          ) : (
            filteredTasks.map((t) => {
              const isOverdue = t.status === 'pending' && t.due_date && t.due_date < todayStr;
              return (
                <div
                  key={t.id}
                  className={`flex items-center justify-between rounded-xl border p-3 text-xs transition-colors ${
                    t.status === 'completed'
                      ? 'border-[#e4ded6] bg-[#f5f1eb] opacity-60'
                      : isOverdue
                      ? 'border-[#fecaca] bg-[#fff5f5]'
                      : 'border-[#e8ded0] bg-white shadow-xs'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={t.status === 'completed'}
                      onChange={() => handleToggleComplete(t.id, t.status)}
                      className="h-4 w-4 rounded accent-[#7a1c30] cursor-pointer"
                    />
                    <div>
                      <div className={`font-medium ${t.status === 'completed' ? 'line-through text-[#8c807e]' : 'text-[#2c2226]'}`}>
                        {t.title}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5 text-[11px] text-[#7a6e6b]">
                        <span className={`uppercase font-semibold text-[10px] px-1.5 py-0.5 rounded ${
                          t.priority === 'high' ? 'bg-[#fee2e2] text-[#991b1b]' :
                          t.priority === 'low' ? 'bg-[#f3f4f6] text-[#4b5563]' :
                          'bg-[#fef3c7] text-[#92400e]'
                        }`}>
                          {t.priority}
                        </span>
                        {t.due_date && (
                          <span className={isOverdue ? 'font-semibold text-[#dc2626] flex items-center gap-1' : ''}>
                            {isOverdue && <AlertCircle size={10} />}
                            Due: {t.due_date}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteTask(t.id)}
                    className="p-1 text-[#a39491] hover:text-[#dc2626] transition-colors cursor-pointer"
                    title="Delete task"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
