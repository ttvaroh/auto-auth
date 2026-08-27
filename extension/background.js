const NATIVE_HOST = "com.autoauth.microsoft";

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "REQUEST_MFA_CODE") return;

  chrome.runtime.sendNativeMessage(NATIVE_HOST, { action: "generate" }, (response) => {
    if (chrome.runtime.lastError) {
      sendResponse({
        ok: false,
        error: chrome.runtime.lastError.message,
      });
      return;
    }

    if (!response?.ok || !response?.code) {
      sendResponse({
        ok: false,
        error: response?.error || "Native host returned no code",
      });
      return;
    }

    sendResponse({ ok: true, code: String(response.code).trim() });
  });

  return true; // keep channel open for async sendResponse
});
