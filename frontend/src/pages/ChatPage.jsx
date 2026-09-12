import { useState, useCallback, useEffect } from 'react';
import api from '../api/client';
import Sidebar from '../components/Sidebar';
import ChatWindow from '../components/ChatWindow';
import ChatInput from '../components/ChatInput';
import UploadPanel from '../components/UploadPanel';
import toast from 'react-hot-toast';

export default function ChatPage() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  // Store messages per session: { [sessionId]: [{ role, content, sources }] }
  const [messagesBySession, setMessagesBySession] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);

  const activeMessages = activeSessionId ? (messagesBySession[activeSessionId] || []) : [];

  // Fetch all sessions on mount
  const fetchSessions = useCallback(async () => {
    try {
      const response = await api.get('/sessions');
      setSessions(response.data);
    } catch (error) {
      toast.error('Failed to load conversations.');
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const createNewSession = useCallback(async () => {
    try {
      const response = await api.post('/sessions');
      const newSession = response.data;
      setSessions((prev) => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
      setMessagesBySession((prev) => ({ ...prev, [newSession.id]: [] }));
    } catch (error) {
      toast.error('Failed to create session. Is the backend running?');
    }
  }, []);

  const selectSession = useCallback(async (sessionId) => {
    setActiveSessionId(sessionId);
    // Fetch messages from backend for the selected session
    setIsLoading(true);
    try {
      const response = await api.get(`/sessions/${sessionId}/messages`);
      setMessagesBySession((prev) => ({
        ...prev,
        [sessionId]: response.data,
      }));
    } catch (error) {
      toast.error('Failed to load conversation history.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const deleteSession = useCallback(async (sessionId) => {
    try {
      await api.delete(`/sessions/${sessionId}`);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      setMessagesBySession((prev) => {
        const copy = { ...prev };
        delete copy[sessionId];
        return copy;
      });
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
      }
      toast.success('Conversation deleted.');
    } catch (error) {
      toast.error('Failed to delete conversation.');
    }
  }, [activeSessionId]);

  const sendMessage = useCallback(async (text) => {
    if (!activeSessionId) {
      // Auto-create a session if none exists
      try {
        const response = await api.post('/sessions');
        const newSession = response.data;
        setSessions((prev) => [newSession, ...prev]);
        setActiveSessionId(newSession.id);
        setMessagesBySession((prev) => ({ ...prev, [newSession.id]: [] }));
        sendToSession(newSession.id, text);
      } catch (error) {
        toast.error('Failed to create session.');
      }
      return;
    }

    sendToSession(activeSessionId, text);
  }, [activeSessionId]);

  const sendToSession = async (sessionId, text) => {
    // Add user message immediately
    const userMsg = { role: 'user', content: text, sources: [] };
    setMessagesBySession((prev) => ({
      ...prev,
      [sessionId]: [...(prev[sessionId] || []), userMsg],
    }));

    // Update session title locally first
    setSessions((prev) =>
      prev.map((s) =>
        s.id === sessionId && s.title === 'New Chat'
          ? { ...s, title: text.substring(0, 40) + (text.length > 40 ? '...' : '') }
          : s
      )
    );

    setIsLoading(true);

    try {
      const response = await api.post(`/sessions/${sessionId}/chat`, {
        message: text,
      });

      const aiMsg = {
        role: 'ai',
        content: response.data.response,
        sources: response.data.sources || [],
      };

      setMessagesBySession((prev) => ({
        ...prev,
        [sessionId]: [...(prev[sessionId] || []), aiMsg],
      }));
    } catch (error) {
      const errMsg = error.response?.data?.detail || 'Failed to get response';
      toast.error(errMsg);

      // Add error message to chat
      setMessagesBySession((prev) => ({
        ...prev,
        [sessionId]: [
          ...(prev[sessionId] || []),
          { role: 'ai', content: '⚠️ Something went wrong. Please try again.', sources: [] },
        ],
      }));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-layout">
      <Sidebar
        sessions={sessions}
        activeSession={activeSessionId}
        onSelectSession={selectSession}
        onNewSession={createNewSession}
        onDeleteSession={deleteSession}
      />

      <main className="chat-area">
        {activeSessionId ? (
          <>
            <div className="chat-header">
              <h1 className="chat-header-title">
                {sessions.find((s) => s.id === activeSessionId)?.title || 'Chat'}
              </h1>
              <div className="chat-header-actions">
                <button
                  className="btn-upload-trigger"
                  onClick={() => setShowUploadModal(true)}
                  title="Upload course material"
                >
                  📚 Upload Materials
                </button>
              </div>
            </div>

            <ChatWindow
              messages={activeMessages}
              isLoading={isLoading}
              onSendPrompt={sendMessage}
            />

            <ChatInput onSend={sendMessage} disabled={isLoading} />
          </>
        ) : (
          <div className="chat-dashboard-container">
            <div className="chat-dashboard-card animate-fade-in-up">
              <span className="dashboard-logo-icon">🧠</span>
              <h2>Welcome to DYXN AI</h2>
              <p>
                Rethink your studying. Select an existing conversation from the sidebar or start a new chat below to begin.
              </p>
              <button className="btn-dashboard-start" onClick={createNewSession}>
                ＋ Start a New Chat
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Floating Upload Modal */}
      {showUploadModal && (
        <div className="modal-overlay" onClick={() => setShowUploadModal(false)}>
          <div className="modal-content animate-fade-in-up" onClick={(e) => e.stopPropagation()}>
            <UploadPanel onClose={() => setShowUploadModal(false)} />
          </div>
        </div>
      )}
    </div>
  );
}

