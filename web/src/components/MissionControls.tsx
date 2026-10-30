import React, { useState } from 'react';
import { Play, Pause, Square, Sparkles, Globe, UserCheck, Bookmark } from 'lucide-react';
import { SessionStatus } from '../types';

interface MissionControlsProps {
  status: SessionStatus;
  profiles: string[];
  onStart: (goal: string, startUrl?: string, model?: string, coPilot?: boolean, profile?: string) => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onSaveProfile: (name: string) => void;
}

export const MissionControls: React.FC<MissionControlsProps> = ({
  status,
  profiles,
  onStart,
  onPause,
  onResume,
  onStop,
  onSaveProfile,
}) => {
  const [goal, setGoal] = useState('');
  const [startUrl, setStartUrl] = useState('');
  const [model, setModel] = useState('gpt-4o');
  const [coPilot, setCoPilot] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState('');
  const [newProfileName, setNewProfileName] = useState('');
  const [showSaveProfile, setShowSaveProfile] = useState(false);

  const isRunning =
    status.status === 'running' ||
    status.status === 'takeover' ||
    status.status === 'awaiting_approval';
  const isPaused = status.status === 'paused';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim() || isRunning) return;
    onStart(goal, startUrl.trim() || undefined, model, coPilot, selectedProfile || undefined);
  };

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProfileName.trim()) return;
    onSaveProfile(newProfileName.trim());
    setNewProfileName('');
    setShowSaveProfile(false);
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
            placeholder="e.g. Find the top rated product on books.toscrape.com and extract its price"
            rows={2}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 transition resize-none disabled:opacity-50"
          />
        </div>

        {/* Start URL & Model Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1 flex items-center space-x-1">
              <Globe className="w-3 h-3" />
              <span>Starting URL</span>
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

          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1 flex items-center justify-between">
              <span className="flex items-center space-x-1">
                <Bookmark className="w-3 h-3" />
                <span>Saved Profile</span>
              </span>
              <button
                type="button"
                onClick={() => setShowSaveProfile(!showSaveProfile)}
                className="text-[10px] text-sky-400 hover:text-sky-300"
              >
                + Save Current
              </button>
            </label>
            <select
              value={selectedProfile}
              onChange={(e) => setSelectedProfile(e.target.value)}
              disabled={isRunning}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-sky-500 disabled:opacity-50"
            >
              <option value="">Clean Profile (Incognito)</option>
              {profiles.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Save Profile Mini Bar */}
        {showSaveProfile && (
          <div className="flex items-center space-x-2 p-2 bg-slate-950 border border-slate-800 rounded-lg">
            <input
              type="text"
              value={newProfileName}
              onChange={(e) => setNewProfileName(e.target.value)}
              placeholder="Profile name (e.g. amazon-login)"
              className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200"
            />
            <button
              type="button"
              onClick={handleSaveProfile}
              className="px-3 py-1 bg-sky-500 text-slate-950 rounded text-xs font-bold"
            >
              Save Session Cookies
            </button>
          </div>
        )}

        {/* Co-Pilot Toggle & Action Button Controls */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
          <div className="flex items-center space-x-3">
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

            {/* Co-Pilot Checkbox */}
            <label className="flex items-center space-x-2 text-xs text-slate-300 cursor-pointer select-none pl-2">
              <input
                type="checkbox"
                checked={coPilot}
                onChange={(e) => setCoPilot(e.target.checked)}
                disabled={isRunning}
                className="rounded border-slate-700 bg-slate-950 text-sky-500 focus:ring-0"
              />
              <span className="flex items-center space-x-1">
                <UserCheck className="w-3.5 h-3.5 text-sky-400" />
                <span>Co-Pilot Mode (Approve each step)</span>
              </span>
            </label>
          </div>

          <div className="text-[11px] text-slate-500 font-mono">
            Status: <span className="text-slate-300 uppercase font-semibold">{status.status}</span>
          </div>
        </div>
      </form>
    </div>
  );
};
