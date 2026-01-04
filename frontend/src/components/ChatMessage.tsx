import ReactMarkdown from 'react-markdown';
import './ChatMessage.css';

interface Message {
    id: string;
    type: 'user' | 'agent' | 'error';
    content: string;
    timestamp: Date;
}

interface ChatMessageProps {
    message: Message;
}

function ChatMessage({ message }: ChatMessageProps) {
    const formatTime = (date: Date) => {
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <div className={`message-wrapper ${message.type}`}>
            <div className="message-bubble">
                <div className="message-header">
                    <span className="message-sender">
                        {message.type === 'user' ? 'You' : message.type === 'error' ? '⚠️ Error' : 'Agent'}
                    </span>
                    <span className="message-time">{formatTime(message.timestamp)}</span>
                </div>
                <div className="message-content">
                    {message.type === 'error' ? (
                        <p className="error-text">{message.content}</p>
                    ) : (
                        <ReactMarkdown>{message.content}</ReactMarkdown>
                    )}
                </div>
            </div>
        </div>
    );
}

export default ChatMessage;
