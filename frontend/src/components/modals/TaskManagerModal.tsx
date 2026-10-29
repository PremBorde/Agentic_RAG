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
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      backgroundColor: 'rgba(30, 24, 20, 0.45)',
      backdropFilter: 'blur(3px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '560px',
        maxHeight: '85vh',
        backgroundColor: '#ffffff',
        borderRadius: '16px',
        border: `1px solid ${THEME.beigeBorderDark}`,
        boxShadow: '0 20px 40px rgba(122, 28, 48, 0.15)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          backgroundColor: THEME.beigeSurface,
          borderBottom: `1px solid ${THEME.beigeBorder}`
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              backgroundColor: THEME.burgundy,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff'
            }}>
              <CheckSquare size={16} />
            </div>
            <div>
              <div style={{ fontSize: '15px', fontWeight: 650, color: THEME.slateDark }}>
                Tasks & Reminders
              </div>
              <div style={{ fontSize: '11px', color: THEME.slateMuted }}>
                Personal to-dos, priorities, and deadlines
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: THEME.slateMuted,
              padding: '4px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Task Creator Form */}
        <form onSubmit={handleCreateTask} style={{
          padding: '14px 20px',
          backgroundColor: THEME.beigeBg,
          borderBottom: `1px solid ${THEME.beigeBorder}`,
          display: 'flex',
          flexDirection: 'column',
          gap: '10px'
        }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              type="text"
              placeholder="Add a new task (e.g. Finish RAG report)..."
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: '8px',
                border: `1px solid ${THEME.beigeBorderDark}`,
                fontSize: '12.5px',
                outline: 'none',
                backgroundColor: '#ffffff',
                color: THEME.slateDark
              }}
            />
            <button
              type="submit"
              disabled={!newTitle.trim()}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '8px 14px',
                borderRadius: '8px',
                border: 'none',
                backgroundColor: THEME.burgundy,
                color: '#ffffff',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                opacity: newTitle.trim() ? 1 : 0.6
              }}
            >
              <Plus size={14} /> Add
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '12px', color: THEME.slateMuted }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span>Priority:</span>
              <select
                value={newPriority}
                onChange={(e: any) => setNewPriority(e.target.value)}
                style={{
                  padding: '4px 8px',
                  borderRadius: '6px',
                  border: `1px solid ${THEME.beigeBorderDark}`,
                  fontSize: '11.5px',
                  backgroundColor: '#ffffff',
                  outline: 'none'
                }}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Calendar size={13} />
              <span>Due:</span>
              <input
                type="date"
                value={newDueDate}
                onChange={(e) => setNewDueDate(e.target.value)}
                style={{
                  padding: '3px 6px',
                  borderRadius: '6px',
                  border: `1px solid ${THEME.beigeBorderDark}`,
                  fontSize: '11.5px',
                  backgroundColor: '#ffffff',
                  outline: 'none'
                }}
              />
            </div>
          </div>
        </form>

        {/* Filter Tabs */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '10px 20px',
          backgroundColor: '#ffffff',
          borderBottom: `1px solid ${THEME.beigeBorder}`
        }}>
          {(['all', 'pending', 'overdue', 'completed'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setFilter(tab)}
              style={{
                padding: '4px 10px',
                borderRadius: '12px',
                border: 'none',
                fontSize: '11.5px',
                fontWeight: 600,
                cursor: 'pointer',
                textTransform: 'capitalize',
                backgroundColor: filter === tab ? THEME.burgundy : THEME.beigeSurface,
                color: filter === tab ? '#ffffff' : THEME.slateMuted
              }}
            >
              {tab}
            </button>
          ))}
          <span style={{ marginLeft: 'auto', fontSize: '11px', color: THEME.slateLight }}>
            {filteredTasks.length} task{filteredTasks.length === 1 ? '' : 's'}
          </span>
        </div>

        {/* Task List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '14px 20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {filteredTasks.length === 0 ? (
            <div style={{ padding: '30px 0', textAlign: 'center', fontSize: '12.5px', color: THEME.slateLight }}>
              No tasks found in this view.
            </div>
          ) : (
            filteredTasks.map((t) => {
              const isOverdue = t.status === 'pending' && t.due_date && t.due_date < todayStr;
              return (
                <div
                  key={t.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 14px',
                    borderRadius: '10px',
                    border: `1px solid ${isOverdue ? '#fca5a5' : THEME.beigeBorder}`,
                    backgroundColor: t.status === 'completed' ? THEME.beigeBg : isOverdue ? '#fff5f5' : '#ffffff',
                    opacity: t.status === 'completed' ? 0.65 : 1
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <input
                      type="checkbox"
                      checked={t.status === 'completed'}
                      onChange={() => handleToggleComplete(t.id, t.status)}
                      style={{ width: '15px', height: '15px', accentColor: THEME.burgundy, cursor: 'pointer' }}
                    />
                    <div>
                      <div style={{
                        fontSize: '13px',
                        fontWeight: 550,
                        color: THEME.slateDark,
                        textDecoration: t.status === 'completed' ? 'line-through' : 'none'
                      }}>
                        {t.title}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px', fontSize: '11px', color: THEME.slateMuted }}>
                        <span style={{
                          padding: '1px 6px',
                          borderRadius: '4px',
                          fontSize: '10px',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          backgroundColor: t.priority === 'high' ? '#fee2e2' : t.priority === 'low' ? '#f3f4f6' : '#fef3c7',
                          color: t.priority === 'high' ? '#991b1b' : t.priority === 'low' ? '#4b5563' : '#92400e'
                        }}>
                          {t.priority}
                        </span>
                        {t.due_date && (
                          <span style={{ color: isOverdue ? '#dc2626' : THEME.slateMuted, fontWeight: isOverdue ? 650 : 400, display: 'flex', alignItems: 'center', gap: '3px' }}>
                            {isOverdue && <AlertCircle size={11} />}
                            Due: {t.due_date}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteTask(t.id)}
                    style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: THEME.slateLight, padding: '4px' }}
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
