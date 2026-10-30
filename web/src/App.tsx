import React, { useState } from 'react';
import { useAgentSession } from './hooks/useAgentSession';
import { LiveBrowserView } from './components/LiveBrowserView';
import { ActionHistory } from './components/ActionHistory';
import { TokenUsageCard } from './components/TokenUsageCard';
import { MissionControls } from './components/MissionControls';
import { HumanTakeoverModal } from './components/HumanTakeoverModal';
import { CoPilotApprovalModal } from './components/CoPilotApprovalModal';
import { SessionReplayModal } from './components/SessionReplayModal';
import { Compass, ShieldCheck, History } from 'lucide-react';

export const App: React.FC = () => {
  const {
    viewportFrame,
    steps,
    tabs,
    profiles,
    archives,
    pendingApprovalStep,
    status,
    takeoverChallenge,
    activeElements,
    isConnected,
    switchTab,
    newTab,
    closeTab,
    approveStep,
    saveProfile,
    downloadExtractedData,
    sendRemoteClick,
    sendRemoteScroll,
    sendRemoteType,
    sendRemotePress,
    startSession,
    pauseSession,
    resumeSession,
    stopSession,
  } = useAgentSession();

  const [showReplayModal, setShowReplayModal] = useState(false);

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-sky-500/20 border border-sky-500/30 flex items-center justify-center text-sky-400">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-sm font-bold tracking-tight text-white">BrowserPilot</h1>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
                v0.1.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Autonomous a11y & visual grounding browser agent
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Past Missions Archive Button */}
          <button
            onClick={() => setShowReplayModal(true)}
            className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:border-sky-500/40 text-xs text-slate-300 transition"
          >
            <History className="w-3.5 h-3.5 text-sky-400" />
            <span>Missions ({archives.length})</span>
          </button>

          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs text-slate-300">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Stealth CDP Active</span>
          </div>

          <div className="flex items-center space-x-2 text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                status.status === 'running'
                  ? 'bg-emerald-400 animate-pulse'
                  : status.status === 'takeover' || status.status === 'awaiting_approval'
                  ? 'bg-amber-400 animate-bounce'
                  : status.status === 'paused'
                  ? 'bg-amber-400'
                  : 'bg-slate-500'
              }`}
            />
            <span className="text-slate-400 capitalize">{status.status}</span>
          </div>
        </div>
      </header>

      {/* Main Studio Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Live Browser Canvas and Controls (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          <LiveBrowserView
            frame={viewportFrame}
            isConnected={isConnected}
            isTakeover={status.status === 'takeover'}
            elements={activeElements}
            tabs={tabs}
            onSwitchTab={switchTab}
            onNewTab={newTab}
            onCloseTab={closeTab}
            onRemoteClick={sendRemoteClick}
            onRemoteScroll={sendRemoteScroll}
            onRemoteType={sendRemoteType}
            onRemotePress={sendRemotePress}
          />

          <MissionControls
            status={status}
            profiles={profiles}
            onStart={startSession}
            onPause={pauseSession}
            onResume={resumeSession}
            onStop={stopSession}
            onSaveProfile={saveProfile}
          />
        </div>

        {/* Right Column: Telemetry & Step Action Timeline (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          <TokenUsageCard
            totalTokens={status.total_tokens}
            costUsd={status.total_cost_usd}
            stepCount={status.total_steps}
            model="gpt-4o"
          />

          <ActionHistory
            steps={steps}
            finalAnswer={status.final_answer}
            hasExtractedData={status.has_extracted_data}
            onDownloadData={downloadExtractedData}
          />
        </div>
      </main>

      {/* Human Takeover Modal (triggered on CAPTCHA / 2FA) */}
      {status.status === 'takeover' && (
        <HumanTakeoverModal
          challengeType={takeoverChallenge || 'challenge'}
          onResume={resumeSession}
          onAbort={stopSession}
        />
      )}

      {/* Co-Pilot Approval Modal */}
      {(status.awaiting_approval || pendingApprovalStep) && pendingApprovalStep && (
        <CoPilotApprovalModal
          step={pendingApprovalStep}
          onApprove={approveStep}
          onReject={stopSession}
        />
      )}

      {/* Session Replay Scrubber Modal */}
      {showReplayModal && (
        <SessionReplayModal
          archives={archives}
          onClose={() => setShowReplayModal(false)}
        />
      )}
    </div>
  );
};

export default App;
