import SourceCard from './SourceCard';

export default function MessageBubble({ role, content, sources }) {
  const isUser = role === 'user';

  return (
    <div className={`message-row ${isUser ? 'user' : 'ai'}`}>
      {!isUser && (
        <div className="message-avatar ai-avatar" aria-hidden="true">
          D
        </div>
      )}
      <div className="message-content-wrapper">
        <div className={`message-bubble ${isUser ? 'user-bubble' : 'ai-bubble'}`}>
          {content}
        </div>
        {!isUser && sources && sources.length > 0 && (
          <div className="sources-container">
            {sources.map((src, i) => (
              <SourceCard key={i} source={src} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
