import { useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';

export default function ChatWindow({ messages, isLoading }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="chat-messages">
        <div className="chat-empty">
          <div className="chat-empty-icon">🧠</div>
          <h2>Welcome to DYXN AI</h2>
          <p>
            Upload your textbooks or slides, then ask questions. 
            I'll help you study smarter with context-aware answers.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-messages" id="chat-messages">
      {messages.map((msg, index) => (
        <MessageBubble
          key={index}
          role={msg.role}
          content={msg.content}
          sources={msg.sources}
        />
      ))}
      {isLoading && (
        <div className="typing-indicator">
          <div className="message-avatar ai-avatar" aria-hidden="true">D</div>
          <div className="typing-dots">
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
