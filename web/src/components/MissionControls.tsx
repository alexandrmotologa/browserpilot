import React, { useState } from 'react';
import { Play, Pause, Square, Sparkles, Globe } from 'lucide-react';
import { SessionStatus } from '../types';

interface MissionControlsProps {
  status: SessionStatus;
  onStart: (goal: string, startUrl?: string, model?: string) => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
}

export const MissionControls: React.FC<MissionControlsProps> = ({
  status,
  onStart,
  onPause,
  onResume,
  onStop,
}) => {
  const [goal, setGoal] = useState('');
  const [startUrl, setStartUrl] = useState('');
  const [model, setModel] = useState('gpt-4o');

  const isRunning = status.status === 'running' || status.status === 'takeover';
  const isPaused = status.status === 'paused';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim() || isRunning) return;
    onStart(goal, startUrl.trim() || undefined, model);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg space-y-4">
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Goal Input */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center space-x-1.5">
            <Sparkles className="w-3.5 h-3.5 text-sky-400" />
            <span>Agent Mission Goal</span>
          </label>
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            disabled={isRunning}
            placeholder="e.g. Find the top rated product on books.toscrape.com and tell me its price"
            rows={2}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 transition resize-none disabled:opacity-50"
          />
        </div>

        {/* Start URL & Model Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1 flex items-center space-x-1">
              <Globe className="w-3 h-3" />
              <span>Starting URL (Optional)</span>
            </label>
            <input
              type="text"
              value={startUrl}
              onChange={(e) => setStartUrl(e.target.value)}
              disabled={isRunning}
              placeholder="https://books.toscrape.com"
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 disabled:opacity-50"
            />
          </div>

          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">
              Reasoning Model
            </label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              disabled={isRunning}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-sky-500 disabled:opacity-50"
            >
              <option value="gpt-4o">OpenAI GPT-4o</option>
              <option value="gpt-4o-mini">OpenAI GPT-4o-mini</option>
              <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
              <option value="gemini-2.0-flash">Google Gemini 2.0 Flash</option>
              <option value="ollama/llama3">Local Ollama Llama 3</option>
            </select>
          </div>
        </div>

        {/* Action Button Controls */}
        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center space-x-2">
            {!isRunning && !isPaused ? (
              <button
                type="submit"
                disabled={!goal.trim()}
                className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 disabled:bg-slate-800 disabled:text-slate-600 text-slate-950 font-bold text-xs transition shadow-lg shadow-sky-500/20"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Launch Mission</span>
              </button>
            ) : isPaused ? (
              <button
                type="button"
                onClick={onResume}
                className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs transition"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Resume Mission</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={onPause}
                className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition"
              >
                <Pause className="w-3.5 h-3.5 fill-current" />
                <span>Pause Agent</span>
              </button>
            )}

            {(isRunning || isPaused) && (
              <button
                type="button"
                onClick={onStop}
                className="flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-rose-500/20 hover:text-rose-400 text-slate-300 font-medium text-xs transition border border-slate-700"
              >
                <Square className="w-3.5 h-3.5" />
                <span>Stop</span>
              </button>
            )}
          </div>

          <div className="text-[11px] text-slate-500 font-mono">
            Status: <span className="text-slate-300 uppercase font-semibold">{status.status}</span>
          </div>
        </div>
      </form>
    </div>
  );
};
