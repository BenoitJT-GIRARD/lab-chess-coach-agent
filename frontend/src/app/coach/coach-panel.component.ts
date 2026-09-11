import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { AgentResponse } from '../models/agent.models';

/** The move put forward, and why. */
interface NextMove {
  san: string;
  reason: string;
}

/**
 * Renders the agent's answer: opening, theoretical moves, reference games, engine
 * evaluation, retrieved passages and videos.
 *
 * Purely presentational: it makes no network call and only formats what it is handed.
 * A panel that fetched its own data would give the board and the panel two states that
 * can disagree.
 */
@Component({
  selector: 'app-coach-panel',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatChipsModule,
    MatDividerModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './coach-panel.component.html',
  styleUrl: './coach-panel.component.scss',
})
export class CoachPanelComponent {
  @Input() loading = false;
  @Input() error: string | null = null;
  @Input() result: AgentResponse | null = null;

  constructor(private readonly sanitizer: DomSanitizer) {}

  /**
   * The move to play now.
   *
   * Inside theory, the one most played in master games; outside it, the one the engine
   * recommends. The two cases are exclusive: the agent only calls Stockfish once the
   * position has left theory.
   */
  get nextMove(): NextMove | null {
    const result = this.result;
    if (!result) {
      return null;
    }

    if (result.in_theory && result.theory_moves.length) {
      const move = result.theory_moves[0];
      const games = this.gameCount(move.total);
      return {
        san: move.san,
        reason: games
          ? `le plus joué en parties de maîtres (${games})`
          : 'coup principal de la théorie',
      };
    }

    const evaluation = result.evaluation;
    if (evaluation?.best_move_san) {
      return {
        san: evaluation.best_move_san,
        reason: `recommandé par Stockfish (profondeur ${evaluation.depth})`,
      };
    }

    return null;
  }

  /** Build the embed URL of the first suggested video. */
  embedUrl(videoId: string): SafeResourceUrl {
    return this.sanitizer.bypassSecurityTrustResourceUrl(
      `https://www.youtube.com/embed/${videoId}`,
    );
  }

  /** Render the Stockfish evaluation in a readable form. */
  evaluationLabel(): string {
    const evaluation = this.result?.evaluation;
    if (!evaluation) {
      return '';
    }
    if (evaluation.evaluation_type === 'mate') {
      return `Mat en ${Math.abs(evaluation.value)}`;
    }
    const pawns = evaluation.value / 100;
    return `${pawns >= 0 ? '+' : ''}${pawns.toFixed(2)}`;
  }

  /** How many games a move was played in, formatted. */
  gameCount(total: number): string {
    return total > 0 ? total.toLocaleString('fr-FR') : '';
  }

  /** Readable name for one of the tools the agent used. */
  sourceLabel(source: string): string {
    const labels: Record<string, string> = {
      theory: 'Théorie Lichess',
      engine: 'Moteur Stockfish',
      rag: 'Base Wikichess',
      youtube: 'API YouTube',
      llm: 'Modèle de langage',
    };
    return labels[source] ?? source;
  }
}
