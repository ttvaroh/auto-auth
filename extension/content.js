(() => {
  const OTP_SELECTORS = [
    "#idTxtBx_SAOTCC_OTC",
    'input[name="otc"]',
    'input[aria-label*="code" i]',
    'input[placeholder*="code" i]',
  ];

  const SUBMIT_SELECTORS = [
    "#idSubmit_SAOTCC_Continue",
    'input[type="submit"]',
    'input[value="Verify"]',
    'input[value="Next"]',
    'button[type="submit"]',
  ];

  // Push / number-match screen → switch to code entry
  const CANT_USE_APP_PATTERNS = [
    /i can['’]?t use my microsoft authenticator app right now/i,
    /i can['’]?t use my authenticator app right now/i,
    /i can['’]?t use my microsoft authenticator/i,
  ];

  // After "can't use app", Microsoft often shows a method picker
  const OTP_METHOD_PATTERNS = [
    /use a verification code/i,
    /verification code/i,
    /enter a code/i,
  ];

  const OTP_METHOD_SELECTORS = [
    "#idA_SAASTO_TOTP",
    "#signInAnotherWay",
    'a[id*="TOTP"]',
    'div[data-value="PhoneAppOTP"]',
    'div[role="button"][data-value="PhoneAppOTP"]',
  ];

  let inFlight = false;
  let filledForElement = null;
  let lastFallbackClickAt = 0;
  let lastFallbackKey = "";

  function queryFirst(selectors, root = document) {
    for (const selector of selectors) {
      try {
        const el = root.querySelector(selector);
        if (el) return el;
      } catch {
        // invalid selector in older pages — ignore
      }
    }
    return null;
  }

  function visible(el) {
    if (!el) return false;
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") {
      return false;
    }
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function findOtpInput() {
    const input = queryFirst(OTP_SELECTORS);
    return visible(input) ? input : null;
  }

  function findSubmit(near) {
    const form = near?.closest?.("form");
    if (form) {
      const inForm = queryFirst(SUBMIT_SELECTORS, form);
      if (inForm) return inForm;
    }
    return queryFirst(SUBMIT_SELECTORS);
  }

  function clickableCandidates() {
    return [
      ...document.querySelectorAll("a, button, div[role='button'], span[role='button']"),
    ].filter(visible);
  }

  function findByTextPatterns(patterns) {
    for (const el of clickableCandidates()) {
      const text = (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();
      if (!text) continue;
      if (patterns.some((re) => re.test(text))) return el;
    }
    return null;
  }

  function setNativeValue(input, value) {
    const proto = Object.getPrototypeOf(input);
    const descriptor = Object.getOwnPropertyDescriptor(proto, "value");
    if (descriptor?.set) {
      descriptor.set.call(input, value);
    } else {
      input.value = value;
    }
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  async function requestCode() {
    return chrome.runtime.sendMessage({ type: "REQUEST_MFA_CODE" });
  }

  async function fillAndSubmit(input) {
    if (inFlight || filledForElement === input) return;
    inFlight = true;
    filledForElement = input;

    try {
      const result = await requestCode();
      if (!result?.ok) {
        console.warn("[Auto Microsoft Auth]", result?.error || "Failed to get code");
        filledForElement = null;
        return;
      }

      const code = result.code.replace(/\D/g, "").slice(0, 8);
      if (code.length < 6) {
        console.warn("[Auto Microsoft Auth] Invalid code from host:", result.code);
        filledForElement = null;
        return;
      }

      input.focus();
      setNativeValue(input, code);

      await new Promise((r) => setTimeout(r, 150));

      const submit = findSubmit(input);
      if (submit && !submit.disabled) {
        submit.click();
      }
    } catch (err) {
      console.warn("[Auto Microsoft Auth]", err);
      filledForElement = null;
    } finally {
      inFlight = false;
    }
  }

  function clickOnce(el, key) {
    if (!el) return false;
    const now = Date.now();
    // Avoid hammering the same control while the SPA transitions
    if (key === lastFallbackKey && now - lastFallbackClickAt < 2500) return false;
    lastFallbackKey = key;
    lastFallbackClickAt = now;
    el.click();
    return true;
  }

  /**
   * Wrong screen (push / number match) → "I can't use my Microsoft Authenticator app right now"
   * Then method picker → "Use a verification code" / PhoneAppOTP.
   */
  function maybeSwitchToCodeEntry() {
    if (findOtpInput()) return false;

    const cantUse = findByTextPatterns(CANT_USE_APP_PATTERNS);
    if (clickOnce(cantUse, "cant-use-app")) return true;

    const otpMethod =
      queryFirst(OTP_METHOD_SELECTORS.filter((s) => s !== "#signInAnotherWay")) ||
      findByTextPatterns(OTP_METHOD_PATTERNS);
    if (otpMethod && visible(otpMethod) && clickOnce(otpMethod, "otp-method")) return true;

    // Last resort on some tenants: generic "Sign in another way"
    const anotherWay =
      queryFirst(["#signInAnotherWay"]) ||
      findByTextPatterns([/sign in another way/i, /other ways to sign in/i]);
    if (anotherWay && clickOnce(anotherWay, "another-way")) return true;

    return false;
  }

  function scan() {
    if (maybeSwitchToCodeEntry()) return;

    const input = findOtpInput();
    if (!input || input.disabled || input.readOnly) return;
    if (input.value && input.value.trim().length >= 6) return;
    fillAndSubmit(input);
  }

  const observer = new MutationObserver(() => scan());
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });

  scan();
})();
