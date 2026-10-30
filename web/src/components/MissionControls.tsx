import React, { useState } from 'react';
import { Play, Pause, Square, Sparkles, Globe, UserCheck, Bookmark, Check } from 'lucide-react';
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
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5 sm:p-4 shadow-lg space-y-3.5">
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Goal Input */}
        <div>
          <label className="block text-[11px] sm:text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center space-x-1.5">
            <Sparkles className="w-3.5 h-3.5 text-sky-400 flex-shrink-0" />
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 sm:gap-3">
          <div className="min-w-0">
            <label className="block text-[11px] font-medium text-slate-400 mb-1 flex items-center space-x-1">
              <Globe className="w-3 h-3 flex-shrink-0 text-slate-400" />
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

          <div className="min-w-0">
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

          <div className="min-w-0 sm:col-span-2 lg:col-span-1">
            <label className="block text-[11px] font-medium text-slate-400 mb-1 flex items-center justify-between">
              <span className="flex items-center space-x-1 truncate">
                <Bookmark className="w-3 h-3 flex-shrink-0 text-slate-400" />
                <span>Saved Profile</span>
              </span>
              <button
                type="button"
                onClick={() => setShowSaveProfile(!showSaveProfile)}
                className="text-[10px] text-sky-400 hover:text-sky-300 font-medium whitespace-nowrap ml-1"
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
          <div className="flex flex-wrap sm:flex-nowrap items-center gap-2 p-2 bg-slate-950 border border-slate-800 rounded-lg">
            <input
              type="text"
              value={newProfileName}
              onChange={(e) => setNewProfileName(e.target.value)}
              placeholder="Profile name (e.g. github-auth)"
              className="flex-1 min-w-0 bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-200"
            />
            <button
              type="button"
              onClick={handleSaveProfile}
              className="px-3 py-1 bg-sky-500 hover:bg-sky-400 text-slate-950 rounded text-xs font-bold whitespace-nowrap flex items-center space-x-1"
            >
              <Check className="w-3 h-3" />
              <span>Save Session</span>
            </button>
          </div>
        )}

        {/* Action Controls & Co-Pilot Toggle */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-slate-800/80">
          <div className="flex flex-wrap items-center gap-2 sm:gap-2.5">
            {!isRunning && !isPaused ? (
              <button
                type="submit"
                disabled={!goal.trim()}
                className="flex items-center space-x-1.5 px-3.5 py-1.5 sm:px-4 sm:py-2 rounded-lg bg-sky-500 hover:bg-sky-400 disabled:bg-slate-800 disabled:text-slate-600 text-slate-950 font-bold text-xs transition shadow-lg shadow-sky-500/20 whitespace-nowrap"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Launch Mission</span>
              </button>
            ) : isPaused ? (
              <button
                type="button"
                onClick={onResume}
                className="flex items-center space-x-1.5 px-3.5 py-1.5 sm:px-4 sm:py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs transition whitespace-nowrap"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Resume Mission</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={onPause}
                className="flex items-center space-x-1.5 px-3.5 py-1.5 sm:px-4 sm:py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition whitespace-nowrap"
              >
                <Pause className="w-3.5 h-3.5 fill-current" />
                <span>Pause Agent</span>
              </button>
            )}

            {(isRunning || isPaused) && (
              <button
                type="button"
                onClick={onStop}
                className="flex items-center space-x-1.5 px-3 py-1.5 sm:py-2 rounded-lg bg-slate-800 hover:bg-rose-500/20 hover:text-rose-400 text-slate-300 font-medium text-xs transition border border-slate-700 whitespace-nowrap"
              >
                <Square className="w-3.5 h-3.5" />
                <span>Stop</span>
              </button>
            )}

            {/* Co-Pilot Checkbox Badge */}
            <label className="flex items-center space-x-1.5 text-xs text-slate-300 cursor-pointer select-none bg-slate-950/80 hover:bg-slate-800/60 border border-slate-800 px-2.5 py-1.5 rounded-lg transition whitespace-nowrap">
              <input
                type="checkbox"
                checked={coPilot}
                onChange={(e) => setCoPilot(e.target.checked)}
                disabled={isRunning}
                className="rounded border-slate-700 bg-slate-950 text-sky-500 focus:ring-0 w-3.5 h-3.5"
              />
              <UserCheck className="w-3.5 h-3.5 text-sky-400 flex-shrink-0" />
              <span className="font-medium text-[11px] sm:text-xs">Co-Pilot Approval</span>
            </label>
          </div>

          <div className="flex items-center justify-between sm:justify-end text-[11px] text-slate-400 font-mono pt-1 sm:pt-0 border-t sm:border-t-0 border-slate-800/40">
            <span>Status:</span>
            <span className="ml-1.5 px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-200 uppercase font-semibold text-[10px]">
              {status.status}
            </span>
          </div>
        </div>
      </form>
    </div>
  );
};

export default MissionControls;
