// ChatWindow.jsx – scrollable chat message list with typing indicator
import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";

export default function ChatWindow({ messages, isLoading }) {
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isLoading]);

    return (
        <div className="chat-window">
            {messages.map((msg, i) => (
                <MessageBubble key={i} message={msg} />
            ))}
            {isLoading && (
                <div className="message-row assistant-row">
                    <div className="avatar assistant-avatar">
                        <span>🦅</span>
                    </div>
                    <div className="bubble assistant-bubble typing-bubble">
                        <div className="typing-indicator">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                        <p className="typing-label">Querying Monday.com + analysing data…</p>
                    </div>
                </div>
            )}
            <div ref={bottomRef} />
        </div>
    );
}
