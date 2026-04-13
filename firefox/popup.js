function updateStatus() {
  chrome.runtime.sendMessage({ type: "GET_STATUS" }, (response) => {
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    
    if (response && response.connected) {
      dot.classList.add('connected');
      text.textContent = "Connected to Backend";
    } else {
      dot.classList.remove('connected');
      text.textContent = "Disconnected from Backend";
    }
  });
}

document.getElementById('reconnect-btn').addEventListener('click', updateStatus);

// Initial check
updateStatus();
