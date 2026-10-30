import React from 'react';
import { AgentStep } from '../types';
import { CheckCircle2, AlertCircle, Clock, Check, ChevronRight } from 'lucide-react';

interface ActionHistoryProps {
  steps: AgentStep[];
  finalAnswer: string | null;
}

export const ActionHistory: React.FC<ActionHistoryProps> = ({ steps, finalAnswer }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col h-[520px]">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
          <Clock className="w-3.5 h-3.5 text-sky-400" />
          <span>Execution Action Timeline ({steps.length})</span>
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {steps.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs text-center p-6">
            <span>No actions recorded yet.</span>
            <span className="text-[11px] text-slate-600 mt-1">
              Actions will appear here as the agent observes and interacts with the page.
            </span>
          </div>
        ) : (
          steps.map((s) => (
            <div
              key={s.step_number}
              className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-3 text-xs space-y-2 hover:border-slate-700 transition"
            >
              {/* Header */}
              <div className="flex items-center justify-between text-slate-400">
                <span className="font-semibold text-sky-400 flex items-center space-x-1">
                  <span>Step {s.step_number}</span>
                  <ChevronRight className="w-3 h-3 text-slate-600" />
                  <span className="truncate max-w-[180px] text-slate-300 font-normal">
                    {s.title || s.url}
                  </span>
                </span>
                <span className="font-mono text-[10px] text-slate-500">
                  {s.latency_ms.toFixed(0)}ms | {s.total_tokens} tok
                </span>
              </div>

              {/* LLM Thought */}
              <p className="text-slate-300 italic border-l-2 border-sky-500/40 pl-2 text-[11px] leading-relaxed">
                "{s.thought}"
              </p>

              {/* Action Badge */}
              <div className="flex items-center justify-between pt-1">
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 font-mono font-bold text-[10px] uppercase">
                    {s.action.action}
                    {s.action.element_id ? ` [${s.action.element_id}]` : ''}
                  </span>
                  {s.action.text && (
                    <span className="text-slate-400 truncate max-w-[140px] text-[11px]">
                      "{s.action.text}"
                    </span>
                  )}
                  {s.action.direction && (
                    <span className="text-slate-400 text-[11px]">
                      {s.action.direction} {s.action.amount}px
                    </span>
                  )}
                </div>

                {s.verification?.success ? (
                  <span className="flex items-center text-emerald-400 text-[10px] space-x-0.5">
                    <CheckCircle2 className="w-3 h-3" />
                    <span>Verified</span>
                  </span>
                ) : (
                  <span className="flex items-center text-amber-400 text-[10px] space-x-0.5">
                    <AlertCircle className="w-3 h-3" />
                    <span>Warning</span>
                  </span>
                )}
              </div>
            </div>
          ))
        )}

        {/* Final Mission Answer Box */}
        {finalAnswer && (
          <div className="bg-emerald-950/40 border border-emerald-500/40 rounded-lg p-3 text-xs space-y-1.5 mt-3">
            <div className="flex items-center space-x-1.5 text-emerald-400 font-bold">
              <Check className="w-4 h-4" />
              <span>Goal Accomplished</span>
            </div>
            <p className="text-slate-200 text-xs leading-relaxed whitespace-pre-wrap">
              {finalAnswer}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
