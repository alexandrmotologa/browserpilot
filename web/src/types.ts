export interface ActionCommand {
  action:
    | "click"
    | "type"
    | "fill_secret"
    | "press_key"
    | "scroll"
    | "select"
    | "wait"
    | "goto"
    | "switch_tab"
    | "new_tab"
    | "close_tab"
    | "extract_data"
    | "finish"
    | "fail";
  element_id: number | null;
  text: string | null;
  secret_key?: string | null;
  key: string | null;
  press_enter: boolean;
  direction: "up" | "down" | null;
  amount: number | null;
  url: string | null;
  tab_index?: number | null;
  seconds: number | null;
  force_dispatch?: boolean;
  extracted_data?: any;
  reasoning: string;
  answer: string | null;
}

export interface VerificationResult {
  success: boolean;
  changed_url: boolean;
  new_url: string;
  dom_changed: boolean;
  detected_error: string | null;
  recovery_suggestion: string | null;
}

export interface AgentStep {
  step_number: number;
  url: string;
  title: string;
  thought: string;
  action: ActionCommand;
  verification: VerificationResult | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  latency_ms: number;
  screenshot_base64: string | null;
}

export interface SessionStatus {
  session_id: string | null;
  status:
    | "idle"
    | "running"
    | "paused"
    | "completed"
    | "stopped"
    | "takeover"
    | "awaiting_approval";
  goal: string;
  total_steps: number;
  total_tokens: number;
  total_cost_usd: number;
  takeover_required: boolean;
  co_pilot_mode: boolean;
  awaiting_approval: boolean;
  final_answer: string | null;
  has_extracted_data?: boolean;
}

export interface ActionableElement {
  id: number;
  role: string;
  name: string;
  value: string | null;
  x: number;
  y: number;
  width: number;
  height: number;
  is_focused?: boolean;
}

export interface BrowserTab {
  index: number;
  title: string;
  url: string;
  is_active: boolean;
}

export interface ArchivedSessionSummary {
  session_id: string;
  goal: string;
  created_at: string;
  total_steps: number;
  total_cost_usd: number;
  has_extracted_data: boolean;
}
