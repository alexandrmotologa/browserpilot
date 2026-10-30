import React from 'react';
import { AgentStep } from '../types';
import { CheckCircle2, AlertCircle, Clock, Check, ChevronRight, FileSpreadsheet, FileJson, CheckCheck } from 'lucide-react';

interface ActionHistoryProps {
  steps: AgentStep[];
  finalAnswer: string | null;
  hasExtractedData?: boolean;
  onDownloadData?: (format: 'json' | 'csv') => void;
}

export const ActionHistory: React.FC<ActionHistoryProps> = ({
  steps,
  finalAnswer,
  hasExtractedData,
  onDownloadData,
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5 sm:p-4 shadow-lg flex flex-col min-h-[380px] lg:h-[520px]">
      {/* Header */}
      <div className="flex flex-wrap sm:flex-nowrap items-center justify-between gap-2 pb-3 border-b border-slate-800 mb-3">
        <h3 className="text-[11px] sm:text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5 truncate">
          <Clock className="w-3.5 h-3.5 text-sky-400 flex-shrink-0" />
          <span>Execution Action Timeline ({steps.length})</span>
        </h3>

        {/* Download Extracted Dataset Buttons */}
        {hasExtractedData && onDownloadData && (
          <div className="flex items-center space-x-1.5 flex-shrink-0">
            <button
              onClick={() => onDownloadData('json')}
              className="flex items-center space-x-1 px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30 text-[10px] font-medium hover:bg-sky-500/30 transition"
              title="Download Extracted Data as JSON"
            >
              <FileJson className="w-3 h-3" />
              <span>JSON</span>
            </button>
            <button
              onClick={() => onDownloadData('csv')}
              className="flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-medium hover:bg-emerald-500/30 transition"
              title="Download Extracted Data as CSV"
            >
              <FileSpreadsheet className="w-3 h-3" />
              <span>CSV</span>
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto space-y-2.5 sm:space-y-3 pr-1">
        {steps.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs text-center p-6 space-y-1">
            <span className="font-medium text-slate-400">No actions recorded yet.</span>
            <span className="text-[11px] text-slate-600 max-w-xs">
              Actions will appear here as the agent observes and interacts with the page.
            </span>
          </div>
        ) : (
          steps.map((s) => (
            <div
              key={s.step_number}
              className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-2.5 sm:p-3 text-xs space-y-2 hover:border-slate-700 transition"
            >
              {/* Header */}
              <div className="flex items-center justify-between gap-2 text-slate-400">
                <span className="font-semibold text-sky-400 flex items-center space-x-1 min-w-0">
                  <span className="whitespace-nowrap">Step {s.step_number}</span>
                  <ChevronRight className="w-3 h-3 text-slate-600 flex-shrink-0" />
                  <span className="truncate max-w-[120px] xs:max-w-[180px] sm:max-w-[240px] text-slate-300 font-normal">
                    {s.title || s.url}
                  </span>
                </span>
                <span className="font-mono text-[10px] text-slate-400 whitespace-nowrap flex-shrink-0">
                  {s.latency_ms.toFixed(0)}ms | {s.total_tokens} tok
                </span>
              </div>

              {/* LLM Thought */}
              <p className="text-slate-300 italic border-l-2 border-sky-500/40 pl-2 text-[11px] leading-relaxed">
                "{s.thought}"
              </p>

              {/* Action Badge & Status */}
              <div className="flex flex-wrap items-center justify-between gap-1.5 pt-1.5 border-t border-slate-900/60">
                <div className="flex flex-wrap items-center gap-1.5 min-w-0">
                  <span className="px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 font-mono font-bold text-[10px] uppercase whitespace-nowrap">
                    {s.action.action}
                    {s.action.element_id ? ` [${s.action.element_id}]` : ''}
                    {s.action.tab_index !== undefined && s.action.tab_index !== null ? ` Tab ${s.action.tab_index}` : ''}
                  </span>
                  {s.action.text && (
                    <span className="text-slate-400 truncate max-w-[120px] sm:max-w-[160px] text-[11px]">
                      "{s.action.text}"
                    </span>
                  )}
                  {s.action.secret_key && (
                    <span className="text-amber-400 font-mono text-[10px] whitespace-nowrap">
                      🔑 ${s.action.secret_key}
                    </span>
                  )}
                  {s.action.direction && (
                    <span className="text-slate-400 text-[11px] whitespace-nowrap">
                      {s.action.direction} {s.action.amount}px
                    </span>
                  )}
                </div>

                {/* State Tag */}
                {s.verification?.success === false ? (
                  <span className="flex items-center text-amber-400 text-[10px] space-x-1 whitespace-nowrap flex-shrink-0">
                    <AlertCircle className="w-3 h-3" />
                    <span>Warning</span>
                  </span>
                ) : s.verification?.success === true ? (
                  <span className="flex items-center text-emerald-400 text-[10px] space-x-1 whitespace-nowrap flex-shrink-0">
                    <CheckCircle2 className="w-3 h-3" />
                    <span>Verified</span>
                  </span>
                ) : (
                  <span className="flex items-center text-emerald-400/90 text-[10px] space-x-1 whitespace-nowrap flex-shrink-0">
                    <Check className="w-3 h-3" />
                    <span>Executed</span>
                  </span>
                )}
              </div>
            </div>
          ))
        )}

        {/* Final Mission Answer Card */}
        {finalAnswer && (
          <div className="bg-emerald-950/30 border border-emerald-500/30 rounded-lg p-3 text-xs space-y-1.5">
            <div className="flex items-center space-x-1.5 text-emerald-400 font-bold">
              <CheckCheck className="w-4 h-4" />
              <span>Mission Completed</span>
            </div>
            <p className="text-slate-200 text-[11px] leading-relaxed whitespace-pre-wrap">
              {finalAnswer}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ActionHistory;
