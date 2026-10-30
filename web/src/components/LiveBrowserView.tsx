import React, { useState, useRef } from 'react';
import { ActionableElement, BrowserTab } from '../types';
import { Eye, EyeOff, MousePointer, ShieldAlert, Wifi, WifiOff, Plus, X, Globe } from 'lucide-react';

interface LiveBrowserViewProps {
  frame: string | null;
  isConnected: boolean;
  isTakeover: boolean;
  elements: ActionableElement[];
  tabs: BrowserTab[];
  onSwitchTab: (index: number) => void;
  onNewTab: (url?: string) => void;
  onCloseTab: (index?: number) => void;
  onRemoteClick: (x: number, y: number, button?: string) => void;
  onRemoteScroll: (deltaX: number, deltaY: number) => void;
  onRemoteType: (text: string) => void;
  onRemotePress: (key: string) => void;
}

export const LiveBrowserView: React.FC<LiveBrowserViewProps> = ({
  frame,
  isConnected,
  isTakeover,
  elements,
  tabs,
  onSwitchTab,
  onNewTab,
  onCloseTab,
  onRemoteClick,
  onRemoteScroll,
  onRemoteType,
  onRemotePress,
}) => {
  const [showOverlay, setShowOverlay] = useState(true);
  const [interactiveMode, setInteractiveMode] = useState(false);
  const [keyInput, setKeyInput] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  const isInteractive = isTakeover || interactiveMode;

  const handleCanvasClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isInteractive || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    // Scale to native 1280x800 browser coordinates
    const scaleX = 1280 / rect.width;
    const scaleY = 800 / rect.height;

    const nativeX = Math.round(clickX * scaleX);
    const nativeY = Math.round(clickY * scaleY);

    onRemoteClick(nativeX, nativeY, 'left');
  };

  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    if (!isInteractive) return;
    e.preventDefault();
    onRemoteScroll(e.deltaX, e.deltaY);
  };

  const handleSendText = (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyInput.trim()) return;
    onRemoteType(keyInput);
    setKeyInput('');
  };

  return (
    <div className="flex flex-col bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
      {/* Multi-Tab Bar */}
      <div className="flex items-center space-x-1 px-3 pt-2 bg-slate-950 border-b border-slate-800 overflow-x-auto">
        <div className="flex space-x-1.5 pr-2 items-center">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 inline-block" />
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 inline-block" />
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 inline-block" />
        </div>

        {/* Tab Items */}
        {tabs.map((tab) => (
          <div
            key={tab.index}
            onClick={() => onSwitchTab(tab.index)}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-t-lg text-xs cursor-pointer border-t border-x transition max-w-[200px] select-none ${
              tab.is_active
                ? 'bg-slate-900 border-slate-700 text-sky-400 font-semibold'
                : 'bg-slate-950/80 border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
            }`}
          >
            <Globe className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">{tab.title || tab.url || `Tab ${tab.index + 1}`}</span>
            {tabs.length > 1 && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onCloseTab(tab.index);
                }}
                className="hover:text-rose-400 rounded p-0.5"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        ))}

        {/* New Tab Button */}
        <button
          onClick={() => onNewTab()}
          className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          title="Open New Tab"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Viewport Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-3 sm:px-4 py-2 bg-slate-950/90 border-b border-slate-800">
        <span className="text-xs font-medium text-slate-400">
          1280 x 800 Viewport
        </span>

        {/* Action Toggles */}
        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
          <button
            onClick={() => setShowOverlay(!showOverlay)}
            className={`flex items-center space-x-1.5 px-2.5 py-1 rounded text-xs font-medium transition ${
              showOverlay
                ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
            title="Toggle Accessibility Element Badges"
          >
            {showOverlay ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            <span>Overlay ({elements.length})</span>
          </button>

          <button
            onClick={() => setInteractiveMode(!interactiveMode)}
            className={`flex items-center space-x-1.5 px-2.5 py-1 rounded text-xs font-medium transition ${
              isInteractive
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
            title="Toggle manual click and keystroke takeover"
          >
            <MousePointer className="w-3.5 h-3.5" />
            <span>{isInteractive ? 'Takeover Active' : 'Manual Mode'}</span>
          </button>

          <div className="flex items-center pl-2 text-xs text-slate-400">
            {isConnected ? (
              <span className="flex items-center text-emerald-400 space-x-1">
                <Wifi className="w-3.5 h-3.5" />
                <span>Live</span>
              </span>
            ) : (
              <span className="flex items-center text-slate-500 space-x-1">
                <WifiOff className="w-3.5 h-3.5" />
                <span>Disconnected</span>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Viewport Canvas Container */}
      <div
        ref={containerRef}
        onClick={handleCanvasClick}
        onWheel={handleWheel}
        className={`relative aspect-[16/10] w-full bg-slate-950 flex items-center justify-center select-none overflow-hidden ${
          isInteractive ? 'cursor-crosshair ring-2 ring-amber-500/40' : 'cursor-default'
        }`}
      >
        {frame ? (
          <>
            <img
              src={`data:image/jpeg;base64,${frame}`}
              alt="Live browser stream"
              className="w-full h-full object-contain pointer-events-none"
            />

            {/* Injected Accessibility Bounding Badges */}
            {showOverlay &&
              elements.map((el) => {
                const leftPct = (el.x / 1280) * 100;
                const topPct = (el.y / 800) * 100;
                const widthPct = (el.width / 1280) * 100;
                const heightPct = (el.height / 800) * 100;

                return (
                  <div
                    key={el.id}
                    style={{
                      left: `${leftPct}%`,
                      top: `${topPct}%`,
                      width: `${Math.max(widthPct, 1.2)}%`,
                      height: `${Math.max(heightPct, 1.2)}%`,
                    }}
                    className="absolute border border-sky-400/40 bg-sky-500/10 pointer-events-none transition-all"
                  >
                    <span className="absolute -top-3 -left-1 px-1 py-0.5 bg-slate-900 border border-sky-400 text-sky-300 font-mono text-[9px] font-bold rounded shadow-md leading-none">
                      {el.id}
                    </span>
                  </div>
                );
              })}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center text-center p-8 space-y-3">
            <div className="w-12 h-12 rounded-xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400">
              <MousePointer className="w-6 h-6 text-sky-400" />
            </div>
            <div className="text-sm font-medium text-slate-300">
              Browser Stream Idle
            </div>
            <p className="text-xs text-slate-500 max-w-sm">
              Launch a mission below or specify a starting URL to initiate autonomous navigation.
            </p>
          </div>
        )}

        {/* Takeover Active Banner */}
        {isTakeover && (
          <div className="absolute top-3 left-1/2 -translate-x-1/2 bg-amber-500/90 text-slate-950 px-4 py-1.5 rounded-full text-xs font-bold flex items-center space-x-2 shadow-lg backdrop-blur animate-bounce">
            <ShieldAlert className="w-4 h-4" />
            <span>Human Takeover Active - Click / Type in canvas</span>
          </div>
        )}
      </div>

      {/* Manual Remote Input Bar (active in takeover mode) */}
      {isInteractive && (
        <form
          onSubmit={handleSendText}
          className="flex items-center space-x-2 px-3 py-2 bg-slate-950 border-t border-slate-800"
        >
          <span className="text-xs font-medium text-amber-400">Remote Keystrokes:</span>
          <input
            type="text"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder="Type text and press Send to forward keystrokes..."
            className="flex-1 bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-400"
          />
          <button
            type="submit"
            className="px-3 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded text-xs transition"
          >
            Send
          </button>
          <button
            type="button"
            onClick={() => onRemotePress('Enter')}
            className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono rounded text-xs transition"
          >
            Enter ↵
          </button>
          <button
            type="button"
            onClick={() => onRemotePress('Tab')}
            className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono rounded text-xs transition"
          >
            Tab ⇥
          </button>
        </form>
      )}
    </div>
  );
};
