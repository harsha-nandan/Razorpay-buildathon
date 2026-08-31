import { useEffect, useState } from "react";

export default function TypingIndicator() {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const id = setInterval(() => setElapsed(Math.round((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="chat-bubble assistant typing-bubble">
      <span className="typing-dots">
        <span />
        <span />
        <span />
      </span>
      {elapsed >= 6 && (
        <span className="typing-note">
          {elapsed >= 20 ? "Still working - local models can take a bit longer than cloud ones…" : "Thinking…"}
        </span>
      )}
    </div>
  );
}
