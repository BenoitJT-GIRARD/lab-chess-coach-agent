// Typed contracts mirroring the FastAPI backend response models.

export interface MoveStat {
  uci: string;
  san: string;
  white: number;
  draws: number;
  black: number;
  total: number;
  source: string;
}

export interface ReferenceGame {
  game_id: string;
  white: string;
  black: string;
  white_rating: number;
  black_rating: number;
  winner: string;
  year: number | null;
  url: string;
  result: string;
}

export interface Evaluation {
  fen: string;
  evaluation_type: 'cp' | 'mate';
  value: number;
  perspective: string;
  best_move: string | null;
  best_move_san: string | null;
  depth: number;
}

export interface Passage {
  text: string;
  opening: string;
  source: string;
  score: number;
}

export interface VideoResult {
  video_id: string;
  title: string;
  channel: string;
  url: string;
  thumbnail: string;
}

export interface AgentResponse {
  fen: string;
  valid: boolean;
  opening_name: string | null;
  opening_eco: string | null;
  in_theory: boolean;
  total_games: number;
  theory_moves: MoveStat[];
  reference_games: ReferenceGame[];
  evaluation: Evaluation | null;
  passages: Passage[];
  videos: VideoResult[];
  opening_summary: string;
  recommendation: string;
  sources_used: string[];
  error: string | null;
}

export interface Interaction {
  fen: string;
  opening_name: string | null;
  in_theory: boolean;
  sources_used: string[];
  created_at: string;
}

export interface HistoryResponse {
  total: number;
  interactions: Interaction[];
}
