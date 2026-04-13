const API_BASE = "http://127.0.0.1:8088";
let isConnected = false;

// Poll for logs every 1.5 seconds
async function pollLogs() {
  try {
    const response = await fetch(`${API_BASE}/logs`);
    if (response.ok) {
      isConnected = true;
      const logs = await response.json();
      if (logs && logs.length > 0) {
        logs.forEach(log => {
          chrome.tabs.query({}, (tabs) => {
            tabs.forEach(tab => {
              try {
                chrome.tabs.sendMessage(tab.id, { type: "BACKEND_LOG", data: log });
              } catch (e) {}
            });
          });
        });
      }
    } else {
      isConnected = false;
    }
  } catch (err) {
    isConnected = false;
  }
  setTimeout(pollLogs, 1500);
}

pollLogs();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "START_PIPELINE") {
    fetch(`${API_BASE}/process_url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: message.url })
    })
    .then(res => res.json())
    .then(data => sendResponse({ status: "Started", data }))
    .catch(err => sendResponse({ status: "Error", error: err.message }));
    return true; 
  } 
  
  if (message.type === "GET_STATUS") {
    sendResponse({ connected: isConnected });
  }

  // NEW: Fetch profile via background to bypass CSP
  if (message.type === "GET_PROFILE") {
    fetch(`${API_BASE}/profile`)
      .then(res => res.json())
      .then(data => sendResponse(data))
      .catch(err => sendResponse({ error: err.message }));
    return true;
  }
});
