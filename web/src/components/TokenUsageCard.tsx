import React from 'react';
import { DollarSign, Cpu, Zap, TrendingDown } from 'lucide-react';

interface TokenUsageCardProps {
  totalTokens: number;
  costUsd: number;
  stepCount: number;
  model: string;
}

export const TokenUsageCard: React.FC<TokenUsageCardProps> = ({
  totalTokens,
  costUsd,
  stepCount,
  model,
}) => {
  // Approximate full screenshot agent token consumption (typically 2,500 tokens per step)
  const fullScreenshotEstimate = stepCount * 2400;
  const tokensSaved = Math.max(0, fullScreenshotEstimate - totalTokens);
  const savingsPct =
    fullScreenshotEstimate > 0
      ? Math.round((tokensSaved / fullScreenshotEstimate) * 100)
      : 82;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
          <Zap className="w-3.5 h-3.5 text-sky-400" />
          <span>Token & Cost Telemetry</span>
        </h3>
        <span className="text-xs px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 font-mono">
          {model}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* Token Count */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
          <div className="text-[11px] text-slate-500 flex items-center space-x-1">
            <Cpu className="w-3 h-3 text-slate-400" />
            <span>Total Tokens</span>
          </div>
          <div className="text-lg font-bold text-slate-100 mt-0.5 font-mono">
            {totalTokens.toLocaleString()}
          </div>
          <div className="text-[10px] text-emerald-400 mt-1 flex items-center space-x-1">
            <TrendingDown className="w-3 h-3" />
            <span>~{savingsPct}% saved via a11y</span>
          </div>
        </div>

        {/* Total Cost */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
          <div className="text-[11px] text-slate-500 flex items-center space-x-1">
            <DollarSign className="w-3 h-3 text-slate-400" />
            <span>Cumulative Cost</span>
          </div>
          <div className="text-lg font-bold text-emerald-400 mt-0.5 font-mono">
            ${costUsd.toFixed(4)}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">
            {stepCount} executed steps
          </div>
        </div>
      </div>
    </div>
  );
};
