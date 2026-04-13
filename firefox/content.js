// Create UI elements
const container = document.createElement("div");
container.id = "gemini-job-agent-ui";
document.body.appendChild(container);

// Basic Styles
const style = document.createElement("style");
style.textContent = `
  #gemini-job-agent-ui { position: fixed; bottom: 20px; right: 20px; z-index: 10000; font-family: 'Segoe UI', sans-serif; }
  .gemini-fab { background: #2563eb; color: white; border: none; padding: 12px 20px; border-radius: 30px; cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,0.3); font-weight: bold; display: flex; align-items: center; gap: 8px; transition: transform 0.2s; }
  .gemini-fab:hover { transform: scale(1.05); }
  .gemini-log-panel { background: #0f172a; color: #4ade80; width: 300px; height: 200px; margin-bottom: 10px; padding: 10px; border-radius: 12px; font-size: 11px; font-family: monospace; overflow-y: auto; border: 1px solid #334155; display: none; }
`;
document.head.appendChild(style);

const logPanel = document.createElement("div");
logPanel.className = "gemini-log-panel";
container.appendChild(logPanel);

const runBtn = document.createElement("button");
runBtn.className = "gemini-fab";
runBtn.innerHTML = "✨ Run Gemini Pipeline";
runBtn.onclick = () => {
  logPanel.style.display = "block";
  addLog(">>> Sending current URL to Gemini Backend...");
  chrome.runtime.sendMessage({ type: "START_PIPELINE", url: window.location.href });
};
container.appendChild(runBtn);

function addLog(text) {
  const line = document.createElement("div");
  line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
  logPanel.appendChild(line);
  logPanel.scrollTop = logPanel.scrollHeight;
}

// Receive logs
chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "BACKEND_LOG") {
    let logData = message.data;
    if (typeof logData === 'string' && (logData.startsWith('{') || logData.startsWith('['))) {
      try {
        const parsed = JSON.parse(logData);
        if (parsed.type === 'log') addLog(parsed.data);
        else if (parsed.type === 'agent_activity') addLog(`[${parsed.data.stage}] ${parsed.data.activity}`);
        else addLog(JSON.stringify(parsed.data || parsed));
      } catch (e) { addLog(logData); }
    } else {
      addLog(typeof logData === 'string' ? logData : JSON.stringify(logData));
    }
  }
});
