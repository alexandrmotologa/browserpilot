"""Browser fingerprint normalization and stealth evasions."""

# JavaScript snippet evaluated before any document scripts run to mask automated browser flags.
STEALTH_EVASION_SCRIPT = """
(() => {
    // 1. Mask navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', {
        get: () => false,
        configurable: true
    });

    // 2. Mock chrome runtime object
    if (!window.chrome) {
        window.chrome = {};
    }
    if (!window.chrome.runtime) {
        window.chrome.runtime = {
            id: undefined,
            connect: () => {},
            sendMessage: () => {},
            onMessage: { addListener: () => {}, removeListener: () => {} },
            onConnect: { addListener: () => {}, removeListener: () => {} }
        };
    }
    if (!window.chrome.csi) {
        window.chrome.csi = () => {};
    }
    if (!window.chrome.loadTimes) {
        window.chrome.loadTimes = () => ({
            requestTime: performance.now(),
            startLoadTime: performance.now(),
            commitLoadTime: performance.now(),
            finishDocumentLoadTime: performance.now(),
            finishLoadTime: performance.now(),
            firstPaintTime: performance.now(),
            firstPaintAfterLoadTime: performance.now(),
            navigationType: 'Other',
            wasFetchedViaSpdy: false,
            wasNpnNegotiated: false,
            npnNegotiatedProtocol: 'unknown',
            wasAlternateProtocolAvailable: false,
            connectionInfo: 'unknown'
        });
    }

    // 3. Mock navigator.plugins and mimeTypes
    const fakePlugins = [
        {
            name: 'PDF Viewer',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format',
            mimeTypes: [{ type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' }]
        },
        {
            name: 'Chrome PDF Viewer',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format',
            mimeTypes: [{ type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' }]
        },
        {
            name: 'Chromium PDF Viewer',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format',
            mimeTypes: [{ type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' }]
        }
    ];

    Object.defineProperty(navigator, 'plugins', {
        get: () => fakePlugins,
        configurable: true
    });

    // 4. Mock navigator.languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
        configurable: true
    });

    // 5. Mock permissions query
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => {
        if (parameters.name === 'notifications') {
            return Promise.resolve({ state: Notification.permission });
        }
        return originalQuery(parameters);
    };

    // 6. WebGL Vendor & Renderer spoofing
    const getParameterProto = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        // UNMASKED_VENDOR_WEBGL
        if (parameter === 37445) {
            return 'Google Inc. (NVIDIA)';
        }
        // UNMASKED_RENDERER_WEBGL
        if (parameter === 37446) {
            return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)';
        }
        return getParameterProto.apply(this, [parameter]);
    };

    if (window.WebGL2RenderingContext) {
        const getParameter2Proto = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Google Inc. (NVIDIA)';
            }
            if (parameter === 37446) {
                return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)';
            }
            return getParameter2Proto.apply(this, [parameter]);
        };
    }

    // 7. Subtle canvas noise to break automated canvas hash clustering
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(...args) {
        const ctx = this.getContext('2d');
        if (ctx && this.width > 16 && this.height > 16) {
            try {
                const imgData = ctx.getImageData(0, 0, 1, 1);
                // Introduce imperceptible 1-bit variation
                imgData.data[0] = (imgData.data[0] ^ 1);
                ctx.putImageData(imgData, 0, 0);
            } catch (e) {
                // Ignore cross-origin canvas security errors
            }
        }
        return originalToDataURL.apply(this, args);
    };
})();
"""


def get_stealth_scripts() -> list[str]:
    """Return list of JavaScript snippets to inject before page scripts execute."""
    return [STEALTH_EVASION_SCRIPT]
