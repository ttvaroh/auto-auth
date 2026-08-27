const statusEl = document.getElementById("status");
const button = document.getElementById("test");

button.addEventListener("click", async () => {
  statusEl.textContent = "Running…";
  try {
    const result = await chrome.runtime.sendMessage({ type: "REQUEST_MFA_CODE" });
    if (result?.ok) {
      statusEl.textContent = `OK — got code ${result.code}`;
    } else {
      statusEl.textContent = `Error: ${result?.error || "unknown"}`;
    }
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
  }
});
