import React from 'react';
import { ShieldAlert, Play, XOctagon } from 'lucide-react';

interface HumanTakeoverModalProps {
  challengeType: string;
  onResume: () => void;
  onAbort: () => void;
}

export const HumanTakeoverModal: React.FC<HumanTakeoverModalProps> = ({
  challengeType,
  onResume,
  onAbort,
}) => {
  const getTitle = () => {
    switch (challengeType) {
      case 'turnstile':
        return 'Cloudflare Turnstile Detected';
      case 'recaptcha':
        return 'Google reCAPTCHA Challenge';
      case 'hcaptcha':
        return 'hCaptcha Verification';
      case '2fa':
        return 'Two-Factor Authentication (2FA) Required';
      default:
        return 'Human Verification Required';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-amber-500/40 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in duration-150">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100">{getTitle()}</h2>
            <p className="text-xs text-amber-400 font-medium">Autonomous Execution Paused</p>
          </div>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed">
          An interactive verification hurdle was encountered. BrowserPilot has paused the AI planner to let you complete the challenge safely.
        </p>

        <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 text-[11px] text-slate-400 space-y-1">
          <div className="font-semibold text-slate-200">Instructions:</div>
          <div>1. Use the interactive browser viewport on the left to click checkboxes or solve puzzles.</div>
          <div>2. If 2FA code is needed, type it directly into the input field.</div>
          <div>3. Once passed, click below to return control to the agent.</div>
        </div>

        <div className="flex items-center justify-end space-x-3 pt-2">
          <button
            onClick={onAbort}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700 text-xs font-medium transition"
          >
            <XOctagon className="w-3.5 h-3.5" />
            <span>Abort Mission</span>
          </button>
          <button
            onClick={onResume}
            className="flex items-center space-x-1.5 px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold transition shadow-lg shadow-emerald-500/20"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>I Solved It, Resume Agent</span>
          </button>
        </div>
      </div>
    </div>
  );
};
