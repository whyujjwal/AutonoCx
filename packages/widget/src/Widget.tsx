import { useState, useEffect, useRef, useCallback } from "react";
import { ChatBubble } from "./ChatBubble";

interface Message {
  id: string;
  role: "customer" | "assistant";
  content: string;
  timestamp: Date;
}

interface WidgetProps {
  config: {
    apiUrl: string;
    agentId?: string;
    theme?: {
      primaryColor?: string;
      fontFamily?: string;
      position?: "bottom-right" | "bottom-left";
    };
    customer?: {
      id?: string;
      name?: string;
      email?: string;
    };
  };
}

export function Widget({ config }: WidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const primaryColor = config.theme?.primaryColor || "#6366f1";
  const position = config.theme?.position || "bottom-right";

  useEffect(() => {
    const handleOpen = () => setIsOpen(true);
    const handleClose = () => setIsOpen(false);
    document.addEventListener("autonomocx:open", handleOpen);
    document.addEventListener("autonomocx:close", handleClose);
    return () => {
      document.removeEventListener("autonomocx:open", handleOpen);
      document.removeEventListener("autonomocx:close", handleClose);
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const connectWebSocket = useCallback(
    (convId: string) => {
      const wsUrl = config.apiUrl.replace(/^http/, "ws");
      const ws = new WebSocket(`${wsUrl}/chat/ws/${convId}`);

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "message.received") {
          setMessages((prev) => [
            ...prev,
            {
              id: data.data.message_id,
              role: "assistant",
              content: data.data.content,
              timestamp: new Date(),
            },
          ]);
          setIsLoading(false);
        }
      };

      wsRef.current = ws;
    },
    [config.apiUrl]
  );

  const startConversation = async () => {
    const res = await fetch(`${config.apiUrl}/conversations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        channel: "webchat",
        agent_id: config.agentId,
        customer_id: config.customer?.id,
        customer_name: config.customer?.name,
        customer_email: config.customer?.email,
      }),
    });
    const data = await res.json();
    setConversationId(data.id);
    connectWebSocket(data.id);
    return data.id;
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const content = input.trim();
    setInput("");
    setIsLoading(true);

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "customer",
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    let convId = conversationId;
    if (!convId) {
      convId = await startConversation();
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({ type: "message.send", data: { content, content_type: "text" } })
      );
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        .widget-container {
          position: fixed;
          ${position === "bottom-right" ? "right: 20px;" : "left: 20px;"}
          bottom: 20px;
          z-index: 999999;
          font-family: ${config.theme?.fontFamily || "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"};
        }
        .widget-button {
          width: 56px; height: 56px; border-radius: 50%;
          background: ${primaryColor}; border: none; cursor: pointer;
          display: flex; align-items: center; justify-content: center;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          transition: transform 0.2s;
        }
        .widget-button:hover { transform: scale(1.05); }
        .widget-button svg { width: 24px; height: 24px; fill: white; }
        .chat-window {
          position: absolute; bottom: 70px;
          ${position === "bottom-right" ? "right: 0;" : "left: 0;"}
          width: 380px; height: 520px;
          background: white; border-radius: 16px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.12);
          display: flex; flex-direction: column; overflow: hidden;
        }
        .chat-header {
          background: ${primaryColor}; color: white;
          padding: 16px 20px; font-weight: 600; font-size: 16px;
          display: flex; justify-content: space-between; align-items: center;
        }
        .close-btn { background: none; border: none; color: white; cursor: pointer; font-size: 20px; }
        .messages {
          flex: 1; overflow-y: auto; padding: 16px;
          display: flex; flex-direction: column; gap: 8px;
        }
        .input-area {
          padding: 12px; border-top: 1px solid #e5e7eb;
          display: flex; gap: 8px;
        }
        .input-area textarea {
          flex: 1; border: 1px solid #d1d5db; border-radius: 8px;
          padding: 8px 12px; font-size: 14px; resize: none;
          font-family: inherit; outline: none;
        }
        .input-area textarea:focus { border-color: ${primaryColor}; }
        .send-btn {
          background: ${primaryColor}; color: white; border: none;
          border-radius: 8px; padding: 8px 16px; cursor: pointer; font-weight: 500;
        }
        .send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .typing { padding: 8px 12px; color: #6b7280; font-size: 13px; font-style: italic; }
      `}</style>

      <div className="widget-container">
        {isOpen && (
          <div className="chat-window">
            <div className="chat-header">
              <span>AutonoCX Support</span>
              <button className="close-btn" onClick={() => setIsOpen(false)}>
                &times;
              </button>
            </div>
            <div className="messages">
              {messages.length === 0 && (
                <div style={{ color: "#9ca3af", textAlign: "center", marginTop: 40, fontSize: 14 }}>
                  Hi! How can we help you today?
                </div>
              )}
              {messages.map((msg) => (
                <ChatBubble key={msg.id} message={msg} primaryColor={primaryColor} />
              ))}
              {isLoading && <div className="typing">Agent is typing...</div>}
              <div ref={messagesEndRef} />
            </div>
            <div className="input-area">
              <textarea
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type a message..."
              />
              <button className="send-btn" onClick={sendMessage} disabled={!input.trim() || isLoading}>
                Send
              </button>
            </div>
          </div>
        )}
        <button className="widget-button" onClick={() => setIsOpen(!isOpen)}>
          <svg viewBox="0 0 24 24">
            {isOpen ? (
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
            ) : (
              <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z" />
            )}
          </svg>
        </button>
      </div>
    </>
  );
}
