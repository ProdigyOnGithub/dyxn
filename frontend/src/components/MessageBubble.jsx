import SourceCard from './SourceCard';
import toast from 'react-hot-toast';

export default function MessageBubble({ role, content, sources }) {
  const isUser = role === 'user';

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    toast.success('Copied response to clipboard!');
  };

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
          {!isUser && (
            <button
              className="btn-copy-bubble"
              onClick={handleCopy}
              title="Copy response to clipboard"
              aria-label="Copy response to clipboard"
            >
              📋
            </button>
          )}
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

