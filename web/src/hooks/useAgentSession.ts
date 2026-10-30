import { useState, useEffect, useRef, useCallback } from 'react';
import {
  AgentStep,
  SessionStatus,
  ActionableElement,
  BrowserTab,
  ArchivedSessionSummary,
  ActionCommand,
} from '../types';

export function useAgentSession() {
  const [viewportFrame, setViewportFrame] = useState<string | null>(null);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [tabs, setTabs] = useState<BrowserTab[]>([]);
  const [profiles, setProfiles] = useState<string[]>([]);
  const [archives, setArchives] = useState<ArchivedSessionSummary[]>([]);
  const [pendingApprovalStep, setPendingApprovalStep] = useState<AgentStep | null>(null);

  const [status, setStatus] = useState<SessionStatus>({
    session_id: null,
    status: 'idle',
    goal: '',
    total_steps: 0,
    total_tokens: 0,
    total_cost_usd: 0,
    takeover_required: false,
    co_pilot_mode: false,
    awaiting_approval: false,
    final_answer: null,
  });

  const [takeoverChallenge, setTakeoverChallenge] = useState<string | null>(null);
  const [activeElements, setActiveElements] = useState<ActionableElement[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  // Poll current session status and tabs
  const refreshStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/sessions/status');
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
        if (data.takeover_required) {
          setTakeoverChallenge('challenge');
        }
      }
    } catch {
      // Backend not yet ready
    }
  }, []);

  const refreshTabs = useCallback(async () => {
    try {
      const res = await fetch('/api/tabs');
      if (res.ok) {
        const data = await res.json();
        setTabs(data);
      }
    } catch {
      // Ignore
    }
  }, []);

  const refreshProfiles = useCallback(async () => {
    try {
      const res = await fetch('/api/profiles');
      if (res.ok) {
        const data = await res.json();
        setProfiles(data);
      }
    } catch {
      // Ignore
    }
  }, []);

  const refreshArchives = useCallback(async () => {
    try {
      const res = await fetch('/api/sessions/archive');
      if (res.ok) {
        const data = await res.json();
        setArchives(data);
      }
    } catch {
      // Ignore
    }
  }, []);

  const refreshDomTree = useCallback(async () => {
    try {
      const res = await fetch('/api/dom/tree');
      if (res.ok) {
        const data = await res.json();
        setActiveElements(data);
      }
    } catch {
      // Ignore
    }
  }, []);

  // Connect WebSocket
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/telemetry`;

    function connect() {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        refreshStatus();
        refreshTabs();
        refreshProfiles();
        refreshArchives();
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'viewport_frame' && msg.frame) {
            setViewportFrame(msg.frame);
          } else if (msg.type === 'step_update' && msg.step) {
            setSteps((prev) => [...prev, msg.step]);
            if (msg.tabs) {
              setTabs(msg.tabs);
            }
            setStatus((prev) => ({
              ...prev,
              total_steps: msg.step.step_number,
              total_tokens: prev.total_tokens + msg.step.total_tokens,
              total_cost_usd: prev.total_cost_usd + msg.step.cost_usd,
            }));
            refreshDomTree();
          } else if (msg.type === 'step_awaiting_approval' && msg.step) {
            setPendingApprovalStep(msg.step);
            setStatus((prev) => ({ ...prev, awaiting_approval: true, status: 'awaiting_approval' }));
          } else if (msg.type === 'step_approved') {
            setPendingApprovalStep(null);
            setStatus((prev) => ({ ...prev, awaiting_approval: false, status: 'running' }));
          } else if (msg.type === 'tabs_updated' && msg.tabs) {
            setTabs(msg.tabs);
          } else if (msg.type === 'human_takeover_required') {
            setTakeoverChallenge(msg.challenge_type || 'verification');
            setStatus((prev) => ({ ...prev, takeover_required: true, status: 'takeover' }));
          } else if (msg.type === 'session_paused') {
            setStatus((prev) => ({ ...prev, status: 'paused' }));
          } else if (msg.type === 'session_resumed') {
            setTakeoverChallenge(null);
            setStatus((prev) => ({ ...prev, takeover_required: false, status: 'running' }));
          } else if (msg.type === 'session_stopped') {
            setPendingApprovalStep(null);
            setStatus((prev) => ({ ...prev, status: 'stopped' }));
          } else if (msg.type === 'session_completed') {
            setPendingApprovalStep(null);
            setStatus((prev) => ({
              ...prev,
              status: 'completed',
              final_answer: msg.final_answer,
              has_extracted_data: !!msg.has_extracted_data,
            }));
            refreshArchives();
          }
        } catch {
          // Non-JSON message
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        reconnectTimeoutRef.current = window.setTimeout(connect, 2000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [refreshStatus, refreshTabs, refreshProfiles, refreshArchives, refreshDomTree]);

  // Tab operations
  const switchTab = useCallback(async (index: number) => {
    await fetch(`/api/tabs/switch?index=${index}`, { method: 'POST' });
    refreshTabs();
  }, [refreshTabs]);

  const newTab = useCallback(async (url?: string) => {
    const query = url ? `?url=${encodeURIComponent(url)}` : '';
    await fetch(`/api/tabs/new${query}`, { method: 'POST' });
    refreshTabs();
  }, [refreshTabs]);

  const closeTab = useCallback(async (index?: number) => {
    const query = index !== undefined ? `?index=${index}` : '';
    await fetch(`/api/tabs/close${query}`, { method: 'POST' });
    refreshTabs();
  }, [refreshTabs]);

  // Co-Pilot approval
  const approveStep = useCallback(async (modifiedAction?: ActionCommand) => {
    await fetch('/api/sessions/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ modified_action: modifiedAction || null }),
    });
    setPendingApprovalStep(null);
  }, []);

  // Save profile state
  const saveProfile = useCallback(async (name: string) => {
    await fetch(`/api/profiles/save?name=${encodeURIComponent(name)}`, { method: 'POST' });
    refreshProfiles();
  }, [refreshProfiles]);

  // Download extracted dataset
  const downloadExtractedData = useCallback((format: 'json' | 'csv' = 'json') => {
    window.open(`/api/sessions/extracted-data?format=${format}`, '_blank');
  }, []);

  // Remote interactive actions
  const sendRemoteClick = useCallback((x: number, y: number, button = 'left') => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'mouse_click', x, y, button }));
    }
  }, []);

  const sendRemoteMove = useCallback((x: number, y: number) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'mouse_move', x, y }));
    }
  }, []);

  const sendRemoteScroll = useCallback((deltaX: number, deltaY: number) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'mouse_scroll', delta_x: deltaX, delta_y: deltaY }));
    }
  }, []);

  const sendRemoteType = useCallback((text: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'keyboard_type', text }));
    }
  }, []);

  const sendRemotePress = useCallback((key: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'keyboard_press', key }));
    }
  }, []);

  const startSession = useCallback(
    async (goal: string, startUrl?: string, model?: string, coPilot = false, profile?: string) => {
      setSteps([]);
      setTakeoverChallenge(null);
      setPendingApprovalStep(null);
      const res = await fetch('/api/sessions/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          goal,
          start_url: startUrl,
          model,
          co_pilot_mode: coPilot,
          profile: profile || null,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    },
    []
  );

  const pauseSession = useCallback(async () => {
    await fetch('/api/sessions/pause', { method: 'POST' });
    setStatus((prev) => ({ ...prev, status: 'paused' }));
  }, []);

  const resumeSession = useCallback(async () => {
    await fetch('/api/sessions/resume', { method: 'POST' });
    setTakeoverChallenge(null);
    setStatus((prev) => ({ ...prev, takeover_required: false, status: 'running' }));
  }, []);

  const stopSession = useCallback(async () => {
    await fetch('/api/sessions/stop', { method: 'POST' });
    setPendingApprovalStep(null);
    setStatus((prev) => ({ ...prev, status: 'stopped' }));
  }, []);

  return {
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
    sendRemoteMove,
    sendRemoteScroll,
    sendRemoteType,
    sendRemotePress,
    startSession,
    pauseSession,
    resumeSession,
    stopSession,
  };
}
