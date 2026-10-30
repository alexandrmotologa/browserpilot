"""Automated detection of CAPTCHAs, bot challenges, and two-factor authentication screens."""

import logging
from typing import Any
from pydantic import BaseModel

logger = logging.getLogger("browserpilot.human.captcha")

CAPTCHA_EVALUATION_SCRIPT = """
() => {
    // 1. Cloudflare Turnstile detection
    const cfIframes = document.querySelectorAll(
        'iframe[src*="challenges.cloudflare.com"], iframe[src*="cloudflare.com/turnstile"], .cf-turnstile, #cf-turnstile'
    );
    if (cfIframes.length > 0) {
        return { detected: true, type: 'turnstile', desc: 'Cloudflare Turnstile challenge widget' };
    }

    // 2. Google reCAPTCHA v2 / Enterprise
    const recaptcha = document.querySelectorAll(
        'iframe[src*="google.com/recaptcha"], iframe[src*="recaptcha/api2"], .g-recaptcha, #g-recaptcha'
    );
    if (recaptcha.length > 0) {
        return { detected: true, type: 'recaptcha', desc: 'Google reCAPTCHA challenge' };
    }

    // 3. hCaptcha
    const hcaptcha = document.querySelectorAll(
        'iframe[src*="hcaptcha.com"], .h-captcha, [data-hcaptcha-widget-id]'
    );
    if (hcaptcha.length > 0) {
        return { detected: true, type: 'hcaptcha', desc: 'hCaptcha challenge widget' };
    }

    // 4. Arkose Labs / FunCaptcha
    const arkose = document.querySelectorAll(
        'iframe[src*="arkoselabs"], iframe[src*="funcaptcha"], #fc-iframe-wrap'
    );
    if (arkose.length > 0) {
        return { detected: true, type: 'arkose', desc: 'Arkose Labs FunCaptcha' };
    }

    // 5. AWS WAF Captcha
    const awsWaf = document.querySelectorAll('#aws-waf-captcha, iframe[src*="awswaf"]');
    if (awsWaf.length > 0) {
        return { detected: true, type: 'aws_waf', desc: 'AWS WAF CAPTCHA puzzle' };
    }

    // 6. Two-Factor Authentication / OTP Inputs
    const otpInput = document.querySelector(
        'input[autocomplete="one-time-code"], input[name*="otp" i], input[name*="2fa" i], input[name*="token" i], input[placeholder*="verification code" i]'
    );
    if (otpInput) {
        return { detected: true, type: '2fa', desc: 'Two-factor or OTP verification input field' };
    }

    // 7. General verification prompt text
    const bodyText = (document.body ? document.body.innerText : '').toLowerCase();
    if (
        bodyText.includes('enter the 6-digit code') ||
        bodyText.includes('check your phone for a verification code') ||
        bodyText.includes('verify that you are human')
    ) {
        return { detected: true, type: 'verification', desc: 'Human verification security prompt in page body' };
    }

    return { detected: false, type: 'none', desc: '' };
}
"""


class CaptchaChallenge(BaseModel):
    """Details of a detected anti-bot or authentication hurdle."""

    is_detected: bool
    challenge_type: str = "none"
    description: str = ""


class CaptchaDetector:
    """Heuristic detector evaluating DOM and iframes for interactive hurdles."""

    @staticmethod
    async def detect(page: Any) -> CaptchaChallenge:
        """Scan active page context for CAPTCHA elements or 2FA prompts."""
        try:
            res = await page.evaluate(CAPTCHA_EVALUATION_SCRIPT)
            return CaptchaChallenge(
                is_detected=bool(res.get("detected", False)),
                challenge_type=res.get("type", "none"),
                description=res.get("desc", ""),
            )
        except Exception as ex:
            logger.debug(f"Captcha detection check failed: {ex}")
            return CaptchaChallenge(is_detected=False)
