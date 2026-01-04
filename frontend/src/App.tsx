import { useState, useEffect, useRef } from 'react';
import './App.css';
import ChatMessage from './components/ChatMessage';
import FileUpload from './components/FileUpload';

interface Message {
  id: string;
  type: 'user' | 'agent' | 'error';
  content: string;
  timestamp: Date;
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize or retrieve session ID
  useEffect(() => {
    let storedSessionId = localStorage.getItem('session_id');
    if (!storedSessionId) {
      // Generate a new UUID-like session ID
      storedSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 15);
      localStorage.setItem('session_id', storedSessionId);
    }
    setSessionId(storedSessionId);
    console.log('📋 Session ID:', storedSessionId);
  }, []);

  // Connect to WebSocket
  useEffect(() => {
    if (!sessionId) return; // Wait for session ID to be initialized

    const connectWebSocket = () => {
      const ws = new WebSocket(`ws://localhost:8000/ws?session_id=${sessionId}`);

      ws.onopen = () => {
        console.log('✅ WebSocket connected');
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'token') {
          setIsLoading(false);
          setMessages(prev => {
            const lastMsg = prev[prev.length - 1];
            // If the last message is from agent, append to it
            if (lastMsg && lastMsg.type === 'agent') {
              return [
                ...prev.slice(0, -1),
                { ...lastMsg, content: lastMsg.content + data.content }
              ];
            }
            // Otherwise create new agent message
            return [...prev, {
              id: Date.now().toString(),
              type: 'agent',
              content: data.content,
              timestamp: new Date()
            }];
          });
        } else if (data.type === 'agent_message') {
          setIsLoading(false);
          // If content is provided and we haven't already streamed it (simple check), add/update?
          // To be safe and simple: if we have content and checking last message didn't cover it:
          if (data.content) {
            setMessages(prev => {
              const lastMsg = prev[prev.length - 1];
              // If we already have an agent message at the end, assume it's the stream we just finished.
              // We update it to ensure final consistency (e.g. formatting fixed by backend?), or ignore.
              // Let's ignore to prevent jitter/duplication if backend sends full content.
              if (lastMsg && lastMsg.type === 'agent') {
                return prev;
              }
              return [...prev, {
                id: Date.now().toString(),
                type: 'agent',
                content: data.content,
                timestamp: new Date()
              }];
            });
          }
        } else if (data.type === 'error') {
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            type: 'error',
            content: "Sorry, couldn't process your request at this moment",
            timestamp: new Date()
          }]);
          setIsLoading(false);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        setIsConnected(false);
      };

      ws.onclose = () => {
        console.log('🔌 WebSocket disconnected');
        setIsConnected(false);
        // Attempt to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };

      wsRef.current = ws;
    };

    connectWebSocket();

    return () => {
      wsRef.current?.close();
    };
  }, [sessionId]);

  const handleSendMessage = () => {
    if (!inputValue.trim() || !isConnected || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    // Send message via WebSocket
    wsRef.current?.send(JSON.stringify({
      message: inputValue
    }));

    setInputValue('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleFileUploadSuccess = (files: any[]) => {
    const fileNames = files.map(f => f.filename).join(', ');
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      type: 'agent',
      content: `Successfully uploaded: ${fileNames}`,
      timestamp: new Date()
    }]);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Conversational Bot</h1>
        <div className="connection-status">
          <span className={`${isConnected ? 'connected' : 'disconnected'}`}></span>
          <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </header>

      <div className="chat-container">
        <div className="messages-container">
          {messages.length === 0 && (
            <div className="welcome-message">
              <h2>Welcome!</h2>
              <p>Start a conversation or upload files to get started.</p>
            </div>
          )}

          {messages.map(message => (
            <ChatMessage key={message.id} message={message} />
          ))}

          {isLoading && (
            <div className="loading-indicator">
              <div className="typing-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <FileUpload onUploadSuccess={handleFileUploadSuccess} sessionId={sessionId} />

          <textarea
            className="message-input"
            placeholder="Type your message..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={!isConnected}
            rows={1}
          />

          <button
            className="send-button"
            onClick={handleSendMessage}
            disabled={!isConnected || !inputValue.trim() || isLoading}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
