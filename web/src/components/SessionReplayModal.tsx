import React, { useState } from 'react';
import { ArchivedSessionSummary, AgentStep } from '../types';
import { History, X, ChevronLeft, ChevronRight, Calendar, DollarSign, Layers } from 'lucide-react';

interface SessionReplayModalProps {
  archives: ArchivedSessionSummary[];
  onClose: () => void;
}

export const SessionReplayModal: React.FC<SessionReplayModalProps> = ({ archives, onClose }) => {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [sessionData, setSessionData] = useState<any | null>(null);
  const [currentStepIdx, setCurrentStepIdx] = useState<number>(0);

  const loadSession = async (id: string) => {
    try {
      const res = await fetch(`/api/sessions/archive/${id}`);
      if (res.ok) {
        const data = await res.json();
        setSessionData(data);
        setSelectedSessionId(id);
        setCurrentStepIdx(0);
      }
    } catch {
      // Error handling
    }
  };

  const steps: AgentStep[] = sessionData?.steps || [];
  const currentStep = steps[currentStepIdx] || null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-6">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-5xl w-full h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/70">
          <div className="flex items-center space-x-2.5">
            <History className="w-5 h-5 text-sky-400" />
            <h2 className="text-sm font-bold text-slate-100">
              {selectedSessionId ? `Session Replay: ${selectedSessionId}` : 'Archived Mission Runs'}
            </h2>
          </div>
          <button
            onClick={() => {
              if (selectedSessionId) {
                setSelectedSessionId(null);
                setSessionData(null);
              } else {
                onClose();
              }
            }}
            className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        {!selectedSessionId ? (
          <div className="flex-1 overflow-y-auto p-6 space-y-3">
            {archives.length === 0 ? (
              <div className="text-center text-slate-500 py-16 text-sm">
                No archived sessions found yet. Completed missions will automatically be saved here.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {archives.map((item) => (
                  <div
                    key={item.session_id}
                    onClick={() => loadSession(item.session_id)}
                    className="bg-slate-950/60 border border-slate-800 hover:border-sky-500/50 rounded-xl p-4 cursor-pointer transition space-y-2.5 group"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-semibold text-sky-400 group-hover:text-sky-300">
                        {item.session_id}
                      </span>
                      <span className="text-[11px] text-slate-500 flex items-center space-x-1">
                        <Calendar className="w-3 h-3" />
                        <span>{new Date(item.created_at).toLocaleDateString()}</span>
                      </span>
                    </div>

                    <p className="text-xs text-slate-200 line-clamp-2 font-medium">
                      "{item.goal}"
                    </p>

                    <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-800/80">
                      <span className="flex items-center space-x-1">
                        <Layers className="w-3 h-3 text-slate-500" />
                        <span>{item.total_steps} steps</span>
                      </span>
                      <span className="flex items-center space-x-1 font-mono text-emerald-400">
                        <DollarSign className="w-3 h-3" />
                        <span>${item.total_cost_usd.toFixed(4)}</span>
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
            {/* Left: Step Frame Preview */}
            <div className="flex-1 bg-slate-950 flex flex-col items-center justify-center p-4 border-r border-slate-800">
              {currentStep?.screenshot_base64 ? (
                <img
                  src={`data:image/jpeg;base64,${currentStep.screenshot_base64}`}
                  alt={`Step ${currentStep.step_number}`}
                  className="max-h-[60vh] object-contain rounded-lg border border-slate-800 shadow-xl"
                />
              ) : (
                <div className="text-slate-500 text-xs">No screenshot recorded for this step</div>
              )}

              {/* Scrubber Controls */}
              <div className="flex items-center space-x-4 mt-4 w-full max-w-md">
                <button
                  disabled={currentStepIdx === 0}
                  onClick={() => setCurrentStepIdx((i) => Math.max(0, i - 1))}
                  className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 transition"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <input
                  type="range"
                  min={0}
                  max={Math.max(0, steps.length - 1)}
                  value={currentStepIdx}
                  onChange={(e) => setCurrentStepIdx(parseInt(e.target.value, 10))}
                  className="flex-1 accent-sky-500"
                />
                <button
                  disabled={currentStepIdx >= steps.length - 1}
                  onClick={() => setCurrentStepIdx((i) => Math.min(steps.length - 1, i + 1))}
                  className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 transition"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
                <span className="text-xs font-mono text-slate-400 whitespace-nowrap">
                  {currentStepIdx + 1} / {steps.length}
                </span>
              </div>
            </div>

            {/* Right: Step Metadata & Reasoning */}
            <div className="w-full md:w-80 p-5 overflow-y-auto space-y-4 bg-slate-900">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Mission Goal</span>
                <p className="text-xs text-slate-200 font-medium mt-0.5">{sessionData.goal}</p>
              </div>

              {currentStep && (
                <div className="space-y-3 pt-2 border-t border-slate-800 text-xs">
                  <div>
                    <span className="text-slate-400">Step {currentStep.step_number}:</span>
                    <p className="text-sky-400 font-medium truncate mt-0.5">{currentStep.url}</p>
                  </div>

                  <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-3 space-y-1">
                    <span className="text-[10px] text-slate-500 uppercase font-semibold">LLM Thought:</span>
                    <p className="text-slate-300 italic text-[11px] leading-relaxed">
                      "{currentStep.thought}"
                    </p>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <span className="px-2.5 py-1 rounded bg-sky-500/20 text-sky-300 font-mono font-bold uppercase text-[10px]">
                      {currentStep.action.action}
                      {currentStep.action.element_id ? ` [${currentStep.action.element_id}]` : ''}
                    </span>
                    <span className="text-slate-400 text-[10px]">
                      {currentStep.total_tokens} tokens
                    </span>
                  </div>
                </div>
              )}

              {sessionData.final_answer && (
                <div className="pt-3 border-t border-slate-800 text-xs space-y-1">
                  <span className="text-emerald-400 font-bold">Final Answer:</span>
                  <p className="text-slate-300 text-[11px] leading-relaxed whitespace-pre-wrap">
                    {sessionData.final_answer}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
