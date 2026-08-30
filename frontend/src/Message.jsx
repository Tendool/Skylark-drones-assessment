import { useState } from "react";
import MarkdownLite from "./markdownLite.jsx";
import { BotIcon, CheckIcon, CopyIcon, UserIcon } from "./icons.jsx";

export default function Message({ role, content }) {
  const [copied, setCopied] = useState(false);
  const isUser = role === "user";

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard API unavailable (e.g. insecure context) -- fail silently
    }
  }

  return (
    <div className={`message-row message-${role}`}>
      <div className={`avatar ${isUser ? "avatar-user" : "avatar-assistant"}`}>
        {isUser ? <UserIcon /> : <BotIcon />}
      </div>
      <div className="message-bubble-wrap">
        <div className="message-bubble">
          <MarkdownLite text={content} />
        </div>
        {!isUser && (
          <button className="copy-button" onClick={handleCopy} title="Copy response">
            {copied ? <CheckIcon /> : <CopyIcon />}
            {copied ? "Copied" : "Copy"}
          </button>
        )}
      </div>
    </div>
  );
}
