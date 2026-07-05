import { useState, useCallback } from 'react';
import api from '../api/client';
import Sidebar from '../components/Sidebar';
import ChatWindow from '../components/ChatWindow';
import ChatInput from '../components/ChatInput';
import toast from 'react-hot-toast';

export default function ChatPage() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  // Store messages per session: { [sessionId]: [{ role, content, sources }] }
  const [messagesBySession, setMessagesBySession] = useState({});
  const [isLoading, setIsLoading] = useState(false);

  const activeMessages = activeSessionId ? (messagesBySession[activeSessionId] || []) : [];

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

  const selectSession = useCallback((sessionId) => {
    setActiveSessionId(sessionId);
  }, []);

  const sendMessage = useCallback(async (text) => {
    if (!activeSessionId) {
      // Auto-create a session if none exists
      try {
        const response = await api.post('/sessions');
        const newSession = response.data;
        setSessions((prev) => [newSession, ...prev]);
        setActiveSessionId(newSession.id);
        setMessagesBySession((prev) => ({ ...prev, [newSession.id]: [] }));
        // Wait for state and send with the new session
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

    // Update session title to first message if it's still "New Chat"
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
      />

      <main className="chat-area">
        <div className="chat-header">
          <h1 className="chat-header-title">
            {activeSessionId
              ? sessions.find((s) => s.id === activeSessionId)?.title || 'Chat'
              : 'DYXN AI Assistant'}
          </h1>
        </div>

        <ChatWindow messages={activeMessages} isLoading={isLoading} />

        <ChatInput onSend={sendMessage} disabled={isLoading} />
      </main>
    </div>
  );
}
