import { useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';

export default function ChatWindow({ messages, isLoading, onSendPrompt }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const starterPrompts = [
    { text: "Explain Fourier Transform in simple terms 📊", icon: "📊" },
    { text: "Generate 5 practice questions from my notes 📝", icon: "📝" },
    { text: "Summarize the key concepts of the syllabus 📚", icon: "📚" },
    { text: "Help me prepare a study plan for my exam 🧠", icon: "🧠" }
  ];

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="chat-messages">
        <div className="chat-empty">
          <div className="chat-empty-icon">🧠</div>
          <h2>This chat is empty</h2>
          <p>
            Upload course documents using the button in the header, or choose a quick study prompt below to start:
          </p>
          <div className="starter-prompts-grid">
            {starterPrompts.map((prompt, i) => (
              <button
                key={i}
                className="starter-prompt-card"
                onClick={() => onSendPrompt(prompt.text)}
              >
                <span className="starter-prompt-icon">{prompt.icon}</span>
                <span className="starter-prompt-text">{prompt.text}</span>
              </button>
            ))}
          </div>
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
