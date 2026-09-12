import { useAuth } from '../context/AuthContext';
import ThemeToggle from './ThemeToggle';

export default function Sidebar({ sessions, activeSession, onSelectSession, onNewSession, onDeleteSession }) {
  const { user, logout } = useAuth();

  return (
    <aside className="sidebar" id="sidebar">
      {/* Brand */}
      <div className="sidebar-header">
        <span className="sidebar-brand">DYXN AI</span>
        <ThemeToggle />
      </div>

      {/* New Chat Button */}
      <button className="btn-new-session" onClick={onNewSession} id="btn-new-session">
        <span>＋</span>
        <span>New Chat</span>
      </button>

      {/* Sessions */}
      <div className="sidebar-section-label">Conversations</div>
      <div className="session-list" id="session-list">
        {sessions.length === 0 && (
          <div style={{
            padding: '16px',
            textAlign: 'center',
            color: 'var(--text-tertiary)',
            fontSize: '0.8rem',
          }}>
            No sessions yet. Start a new chat!
          </div>
        )}
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`session-item ${activeSession === session.id ? 'active' : ''}`}
            onClick={() => onSelectSession(session.id)}
            id={`session-${session.id}`}
          >
            <span className="session-icon">💬</span>
            <span className="session-title">{session.title || 'New Chat'}</span>
            <button
              className="btn-delete-session"
              onClick={(e) => {
                e.stopPropagation();
                onDeleteSession(session.id);
              }}
              title="Delete conversation"
              aria-label="Delete conversation"
            >
              🗑️
            </button>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="user-info">
          <div className="user-avatar">
            {user?.username?.charAt(0).toUpperCase() || '?'}
          </div>
          <span>{user?.username || 'User'}</span>
        </div>
        <button className="btn-logout" onClick={logout} id="btn-logout">
          Sign out
        </button>
      </div>
    </aside>
  );
}

