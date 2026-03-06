interface ChatBubbleProps {
  message: {
    id: string;
    role: "customer" | "assistant";
    content: string;
    timestamp: Date;
  };
  primaryColor: string;
}

export function ChatBubble({ message, primaryColor }: ChatBubbleProps) {
  const isCustomer = message.role === "customer";

  return (
    <>
      <style>{`
        .bubble {
          max-width: 80%; padding: 10px 14px; border-radius: 12px;
          font-size: 14px; line-height: 1.5; word-wrap: break-word;
        }
        .bubble-customer {
          align-self: flex-end;
          background: ${primaryColor}; color: white;
          border-bottom-right-radius: 4px;
        }
        .bubble-assistant {
          align-self: flex-start;
          background: #f3f4f6; color: #1f2937;
          border-bottom-left-radius: 4px;
        }
        .bubble-time {
          font-size: 11px; color: #9ca3af; margin-top: 2px;
          ${isCustomer ? "text-align: right;" : "text-align: left;"}
        }
      `}</style>
      <div style={{ display: "flex", flexDirection: "column" }}>
        <div className={`bubble ${isCustomer ? "bubble-customer" : "bubble-assistant"}`}>
          {message.content}
        </div>
        <div className="bubble-time">
          {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>
    </>
  );
}
