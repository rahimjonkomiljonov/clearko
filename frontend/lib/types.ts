// Mirrors backend/app/explain/schemas.py (Explanation) and backend/app/api/main.py (JobOut).

export type Lang = "uz" | "ru" | "en";
export const LANGS: Lang[] = ["uz", "ru", "en"];

export type DocType = "rental" | "phone_plan" | "part_time";
export type Severity = "low" | "medium" | "high";

export interface KeyFact {
  label: string;
  value: string;
  original_text: string | null;
  quote_verified: boolean;
  numbers_verified: boolean;
}

export interface RedFlag {
  title: string;
  explanation: string;
  original_text: string | null;
  quote_verified: boolean;
  numbers_verified: boolean;
  severity: Severity;
}

export interface Todo {
  action: string;
  deadline: string | null;
}

export interface Explanation {
  summary: string;
  key_facts: KeyFact[];
  red_flags: RedFlag[];
  todos: Todo[];
  doc_type: DocType | "unsupported";
  language: string;
  disclaimer: string;
  ocr_confidence: number | null;
  warnings: string[];
}

export interface ApiError {
  code: string;
  message: string;
}

export interface JobStatus {
  job_id: string;
  status: "queued" | "running" | "done" | "failed";
  stage: string;
  result: Explanation | null;
  error: ApiError | null;
}
