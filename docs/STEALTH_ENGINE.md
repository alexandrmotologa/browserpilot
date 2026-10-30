# Stealth Engine and Anti-Bot Architecture

Automated browsers are routinely flagged by anti-bot systems such as Cloudflare Turnstile, DataDome, and PerimeterX. BrowserPilot implements low-level mitigations across protocol, browser fingerprint, and input dynamics.

## Detection Vectors and Mitigations

### 1. CDP Runtime Leaks

**Problem**: Automated frameworks often enable the Chrome DevTools Protocol (`Runtime.enable`), which leaks execution contexts and automated evaluation flags to client-side scripts.

**Mitigation**:
- BrowserPilot prioritizes `patchright`, a fork of Playwright that patches Chromium source binaries directly to strip automation signatures from internal CDP bindings.
- When running standard Playwright, it avoids high-frequency CDP probes and injects stealth initialization scripts through `addInitScript` before any page scripts evaluate.

### 2. Navigator Property Inconsistencies

**Problem**: Stock Chromium reveals automation via `navigator.webdriver === true`, empty `navigator.plugins`, uniform `navigator.hardwareConcurrency`, and headless user agent flags.

**Mitigation**:
BrowserPilot injects the following evasions:
- Overrides `navigator.webdriver` via `Object.defineProperty` getter returning `false`.
- Fakes `navigator.plugins` and `navigator.mimeTypes` with realistic browser defaults (PDF Viewer, Chrome PDF Viewer).
- Standardizes `navigator.languages` to `["en-US", "en"]`.
- Masks `chrome.runtime` and `chrome.csi` to replicate authentic user desktop installations.
- Emulates realistic permissions queries so `navigator.permissions.query({name: 'notifications'})` matches typical desktop user profiles.

### 3. Canvas and WebGL Fingerprinting

**Problem**: Anti-bot engines extract canvas rendering hashes and WebGL GPU vendor strings. Virtualized environments often report SwiftShader or LLVMpipe renderers.

**Mitigation**:
- Replaces `WebGLRenderingContext.prototype.getParameter` for `UNMASKED_VENDOR_WEBGL` and `UNMASKED_RENDERER_WEBGL` with commercial desktop GPU strings (such as Google Inc., ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)).
- Introduces deterministic, micro-variance noise into canvas `toDataURL` and `getImageData` calls to disrupt signature clustering without breaking visual fidelity.

### 4. Human-like Cursor Motion

**Problem**: Bots typically jump straight to element bounding coordinates and dispatch instant click events. Modern behavioral profiling identifies linear coordinates, constant speed, and zero latency between mouseover and mousedown.

**Mitigation**:
The `CursorMotion` engine computes cubic Bézier curves:
1. Generates control points offset perpendicular to the travel vector.
2. Applies a non-linear velocity curve with slow start, rapid travel, and gradual deceleration.
3. Applies randomized micro-jitter (1 to 2 pixels) along the path to simulate natural hand tremors.
4. Pauses for 80 to 220 milliseconds over the target before dispatching the click sequence.
