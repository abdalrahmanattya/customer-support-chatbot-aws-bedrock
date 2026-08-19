"""Lightweight Web Chat Server for Customer Support Chatbot (AWS Bedrock AgentCore)."""

import argparse
import json
import logging
import sys
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

# Ensure root directory is in sys.path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.agent.config import AgentConfig
from src.agent.core import CustomerSupportAgent
from src.agent.session import SessionMemory

logger = logging.getLogger("web_server")
logging.basicConfig(level=logging.INFO)

# In-memory sessions store
SESSIONS: dict[str, SessionMemory] = {}
AGENT_INSTANCE: CustomerSupportAgent | None = None


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Customer Support Assistant - AWS Bedrock AgentCore</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        :root {
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --bg: #0f172a;
            --card-bg: #1e293b;
            --card-border: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --user-bubble: #3b82f6;
            --bot-bubble: #1e293b;
            --tool-bg: #064e3b;
            --tool-border: #059669;
            --tool-text: #6ee7b7;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
        }

        body {
            background-color: var(--bg);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 16px;
        }

        .chat-container {
            width: 100%;
            max-width: 900px;
            height: 94vh;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            display: flex;
            flex-direction: column;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
            overflow: hidden;
        }

        .header {
            padding: 18px 24px;
            border-bottom: 1px solid var(--card-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(8px);
        }

        .header-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .bot-avatar {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }

        .header-text h1 {
            font-size: 1.1rem;
            font-weight: 600;
        }

        .header-text p {
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 500;
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
            box-shadow: 0 0 8px #10b981;
        }

        .messages-area {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 18px;
            scroll-behavior: smooth;
        }

        .message {
            display: flex;
            gap: 12px;
            max-width: 85%;
        }

        .message.user {
            align-self: flex-end;
            flex-direction: row-reverse;
        }

        .message.assistant {
            align-self: flex-start;
        }

        .bubble {
            padding: 14px 18px;
            border-radius: 14px;
            font-size: 0.95rem;
            line-height: 1.55;
            word-break: break-word;
        }

        .message.user .bubble {
            background: var(--user-bubble);
            color: #ffffff;
            border-bottom-right-radius: 4px;
        }

        .message.assistant .bubble {
            background: #0f172a;
            border: 1px solid var(--card-border);
            color: var(--text-main);
            border-bottom-left-radius: 4px;
        }

        .message.assistant .bubble p:not(:last-child) {
            margin-bottom: 8px;
        }

        .message.assistant .bubble ul, .message.assistant .bubble ol {
            margin-left: 20px;
            margin-bottom: 8px;
        }

        .tool-call-card {
            margin-top: 10px;
            padding: 10px 14px;
            background: var(--tool-bg);
            border: 1px solid var(--tool-border);
            border-radius: 8px;
            font-size: 0.82rem;
            color: var(--tool-text);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .chips-container {
            padding: 8px 24px;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            border-top: 1px solid rgba(51, 65, 85, 0.5);
            background: rgba(15, 23, 42, 0.4);
        }

        .chip {
            padding: 6px 12px;
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            font-size: 0.8rem;
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .chip:hover {
            background: #334155;
            color: var(--text-main);
            border-color: #475569;
        }

        .input-area {
            padding: 16px 24px;
            border-top: 1px solid var(--card-border);
            background: rgba(15, 23, 42, 0.6);
            display: flex;
            gap: 12px;
        }

        .input-box {
            flex: 1;
            background: #0f172a;
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 14px 18px;
            color: var(--text-main);
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s;
        }

        .input-box:focus {
            border-color: var(--primary);
        }

        .btn {
            padding: 0 22px;
            background: var(--primary);
            color: #ffffff;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            transition: background 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .btn:hover {
            background: var(--primary-hover);
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .typing-indicator {
            display: none;
            align-items: center;
            gap: 4px;
            padding: 10px 14px;
            background: #0f172a;
            border: 1px solid var(--card-border);
            border-radius: 14px;
            width: fit-content;
        }

        .typing-dot {
            width: 6px;
            height: 6px;
            background: var(--text-muted);
            border-radius: 50%;
            animation: typing 1.4s infinite ease-in-out both;
        }

        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }

        @keyframes typing {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
    </style>
</head>
<body>

<div class="chat-container">
    <div class="header">
        <div class="header-title">
            <div class="bot-avatar">🤖</div>
            <div class="header-text">
                <h1>Online Shop Support</h1>
                <p>Amazon Bedrock AgentCore &bull; Nova Pro</p>
            </div>
        </div>
        <div class="status-badge">
            <span class="status-dot"></span>
            <span>Live Agent</span>
        </div>
    </div>

    <div class="messages-area" id="messagesArea">
        <div class="message assistant">
            <div class="bubble">
                <p>Hello! Welcome to <strong>Online Shop Customer Support</strong>. 👋</p>
                <p>How can I assist you today? I can help you with order questions, shipping, returns & refunds, or file a bug report for our engineering team.</p>
            </div>
        </div>
        <div class="typing-indicator" id="typingIndicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    </div>

    <div class="chips-container">
        <div class="chip" onclick="sendChip('What is your return policy and refund time?')">📦 Return Policy & Refund Time</div>
        <div class="chip" onclick="sendChip('How long does shipping take?')">🚚 Shipping & Delivery</div>
        <div class="chip" onclick="sendChip('What payment methods are accepted?')">💳 Payment Methods</div>
        <div class="chip" onclick="sendChip('I found a bug on checkout: the submit button freezes on Safari iOS.')">🐛 Report a Bug</div>
    </div>

    <form class="input-area" id="chatForm" onsubmit="handleSend(event)">
        <input type="text" id="userInput" class="input-box" placeholder="Type your inquiry or report an issue..." autocomplete="off" required>
        <button type="submit" id="sendBtn" class="btn">Send</button>
    </form>
</div>

<script>
    const sessionId = "session-" + Math.random().toString(36).substring(2, 11);
    const messagesArea = document.getElementById("messagesArea");
    const userInput = document.getElementById("userInput");
    const sendBtn = document.getElementById("sendBtn");
    const typingIndicator = document.getElementById("typingIndicator");

    function sendChip(text) {
        userInput.value = text;
        handleSend(new Event("submit"));
    }

    async function handleSend(e) {
        e.preventDefault();
        const text = userInput.value.trim();
        if (!text) return;

        // Render user message
        appendMessage("user", text);
        userInput.value = "";
        userInput.disabled = true;
        sendBtn.disabled = true;

        showTyping(true);

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text, sessionId: sessionId })
            });
            const data = await response.json();

            showTyping(false);

            if (data.error) {
                appendMessage("assistant", "⚠️ Error: " + data.error);
            } else {
                appendMessage("assistant", data.text, data.toolCalls);
            }
        } catch (err) {
            showTyping(false);
            appendMessage("assistant", "⚠️ Failed to connect to server: " + err.message);
        } finally {
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
        }
    }

    function appendMessage(role, text, toolCalls = []) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "message " + role;

        const bubble = document.createElement("div");
        bubble.className = "bubble";

        if (role === "assistant") {
            bubble.innerHTML = marked.parse(text);
            if (toolCalls && toolCalls.length > 0) {
                toolCalls.forEach(tc => {
                    const toolCard = document.createElement("div");
                    toolCard.className = "tool-call-card";
                    toolCard.innerHTML = `🔧 <strong>Tool Invoked:</strong> ${tc.tool_name} &bull; Ticket: <strong>${tc.tool_result.ticketId || "OK"}</strong>`;
                    bubble.appendChild(toolCard);
                });
            }
        } else {
            bubble.textContent = text;
        }

        msgDiv.appendChild(bubble);
        messagesArea.insertBefore(msgDiv, typingIndicator);
        messagesArea.scrollTop = messagesArea.scrollHeight;
    }

    function showTyping(show) {
        typingIndicator.style.display = show ? "flex" : "none";
        messagesArea.scrollTop = messagesArea.scrollHeight;
    }
</script>

</body>
</html>
"""


class ChatRequestHandler(SimpleHTTPRequestHandler):
    """HTTP request handler providing chat API and web client UI."""

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif self.path == "/health":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"healthy"}')
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self):
        if self.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                payload = json.loads(body.decode("utf-8"))
                user_message = payload.get("message", "").strip()
                session_id = payload.get("sessionId", "default-session")

                if not user_message:
                    self._send_json({"error": "Empty message"}, HTTPStatus.BAD_REQUEST)
                    return

                if session_id not in SESSIONS:
                    SESSIONS[session_id] = SessionMemory(session_id=session_id)

                session = SESSIONS[session_id]
                response = AGENT_INSTANCE.chat(user_message, session=session)

                tool_calls_data = [
                    {
                        "tool_name": tc.tool_name,
                        "tool_result": tc.tool_result,
                    }
                    for tc in response.tool_calls
                ]

                self._send_json({
                    "text": response.text,
                    "toolCalls": tool_calls_data,
                    "sessionId": session_id,
                })

            except Exception as exc:
                logger.exception("Error processing chat turn")
                self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")

    def _send_json(self, data: dict, status: int = HTTPStatus.OK):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


def start_server(host: str = "127.0.0.1", port: int = 8000, mock: bool = False, model: str | None = None):
    global AGENT_INSTANCE

    config = AgentConfig(
        mock_mode=mock,
    )
    if model:
        config.model_id = model

    AGENT_INSTANCE = CustomerSupportAgent(config=config)

    server = HTTPServer((host, port), ChatRequestHandler)
    mode_str = "OFFLINE MOCK" if config.mock_mode else f"LIVE BEDROCK ({config.model_id})"
    print("=" * 65)
    print(" Customer Support Chatbot Web Server")
    print(f" Mode: {mode_str}")
    print(f" Web UI: http://{host}:{port}")
    print("=" * 65)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down web server...")
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start Web Chat UI Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode")
    parser.add_argument("--model", default=None, help="Bedrock Model ID")
    args = parser.parse_args()

    start_server(host=args.host, port=args.port, mock=args.mock, model=args.model)
