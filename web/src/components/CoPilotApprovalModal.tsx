import React, { useState } from 'react';
import { AgentStep, ActionCommand } from '../types';
import { UserCheck, Check, Edit2, XCircle } from 'lucide-react';

interface CoPilotApprovalModalProps {
  step: AgentStep;
  onApprove: (modifiedAction?: ActionCommand) => void;
  onReject: () => void;
}

export const CoPilotApprovalModal: React.FC<CoPilotApprovalModalProps> = ({
  step,
  onApprove,
  onReject,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [actionType, setActionType] = useState(step.action.action);
  const [elementId, setElementId] = useState<string>(
    step.action.element_id !== null ? String(step.action.element_id) : ''
  );
  const [text, setText] = useState(step.action.text || '');

  const handleApprove = () => {
    if (isEditing) {
      const modified: ActionCommand = {
        ...step.action,
        action: actionType as any,
        element_id: elementId ? parseInt(elementId, 10) : null,
        text: text || null,
      };
      onApprove(modified);
    } else {
      onApprove();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 backdrop-blur-sm p-3 sm:p-4">
      <div className="bg-slate-900 border border-sky-500/40 rounded-2xl max-w-lg w-full p-4 sm:p-6 shadow-2xl space-y-3.5 animate-in fade-in zoom-in duration-150">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-sky-500/20 border border-sky-500/30 flex items-center justify-center text-sky-400 flex-shrink-0">
            <UserCheck className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xs sm:text-sm font-bold text-slate-100">Co-Pilot Step Approval Required</h2>
            <p className="text-[11px] sm:text-xs text-sky-400 font-medium">Step {step.step_number} Planned</p>
          </div>
        </div>

        {/* Thought Block */}
        <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-2.5 sm:p-3 text-xs space-y-1">
          <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Agent Reasoning:</span>
          <p className="text-slate-200 italic leading-relaxed text-[11px]">"{step.thought}"</p>
        </div>

        {/* Action Details */}
        {!isEditing ? (
          <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3 space-y-2 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-1.5">
              <span className="text-slate-400">Proposed Action:</span>
              <span className="px-2.5 py-1 rounded bg-sky-500/20 text-sky-300 font-mono font-bold uppercase text-[11px]">
                {step.action.action}
                {step.action.element_id ? ` [${step.action.element_id}]` : ''}
              </span>
            </div>
            {step.action.text && (
              <div className="flex flex-wrap items-center justify-between gap-1.5 text-slate-300">
                <span className="text-slate-400">Text to type:</span>
                <span className="font-mono text-emerald-400 break-all">"{step.action.text}"</span>
              </div>
            )}
            {step.action.direction && (
              <div className="flex items-center justify-between text-slate-300">
                <span className="text-slate-400">Scroll:</span>
                <span>{step.action.direction} ({step.action.amount}px)</span>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-slate-950/80 border border-slate-700 rounded-lg p-3 space-y-2.5 text-xs">
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Action Type</label>
              <select
                value={actionType}
                onChange={(e) => setActionType(e.target.value as any)}
                className="w-full bg-slate-900 border border-slate-700 rounded p-1.5 text-xs text-slate-200"
              >
                <option value="click">click</option>
                <option value="type">type</option>
                <option value="scroll">scroll</option>
                <option value="press_key">press_key</option>
                <option value="wait">wait</option>
                <option value="finish">finish</option>
              </select>
            </div>
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Target Element ID</label>
              <input
                type="number"
                value={elementId}
                onChange={(e) => setElementId(e.target.value)}
                placeholder="e.g. 14"
                className="w-full bg-slate-900 border border-slate-700 rounded p-1.5 text-xs text-slate-200"
              />
            </div>
            {actionType === 'type' && (
              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Text to Type</label>
                <input
                  type="text"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Text..."
                  className="w-full bg-slate-900 border border-slate-700 rounded p-1.5 text-xs text-slate-200"
                />
              </div>
            )}
          </div>
        )}

        {/* Buttons */}
        <div className="flex flex-col-reverse sm:flex-row sm:items-center sm:justify-between gap-2.5 pt-2">
          <button
            onClick={() => setIsEditing(!isEditing)}
            className="flex items-center justify-center sm:justify-start space-x-1.5 text-xs text-slate-400 hover:text-slate-200 transition py-1"
          >
            <Edit2 className="w-3.5 h-3.5" />
            <span>{isEditing ? 'Cancel Edit' : 'Edit Action'}</span>
          </button>

          <div className="flex items-center space-x-2 w-full sm:w-auto">
            <button
              onClick={onReject}
              className="flex-1 sm:flex-none flex items-center justify-center space-x-1 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700 text-xs transition"
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>Abort</span>
            </button>
            <button
              onClick={handleApprove}
              className="flex-1 sm:flex-none flex items-center justify-center space-x-1.5 px-4 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs transition shadow-lg shadow-sky-500/20 whitespace-nowrap"
            >
              <Check className="w-4 h-4" />
              <span>{isEditing ? 'Execute Modified' : 'Approve & Run Step'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CoPilotApprovalModal;
