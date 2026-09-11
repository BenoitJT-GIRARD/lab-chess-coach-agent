import { Component, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { NgxChessBoardModule, NgxChessBoardView } from 'ngx-chess-board';

import { AgentService } from '../services/agent.service';
import { AgentResponse, Interaction } from '../models/agent.models';
import { CoachPanelComponent } from '../coach/coach-panel.component';

/** One of the prepared demonstration positions. */
interface DemoPosition {
  label: string;
  fen: string;
}

/**
 * The working screen: the board on the left, the coach panel on the right.
 *
 * This component holds the state of the game and talks to the backend. The panel only
 * renders what it is given.
 */
@Component({
  selector: 'app-chessboard',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatIconModule,
    MatTooltipModule,
    NgxChessBoardModule,
    CoachPanelComponent,
  ],
  templateUrl: './chessboard.component.html',
  styleUrl: './chessboard.component.scss',
})
export class ChessboardComponent {
  @ViewChild('board') board!: NgxChessBoardView;

  /** Board size, in pixels. */
  readonly boardSize = 420;
  readonly lightSquare = '#f4f1ea';
  readonly darkSquare = '#7d8a99';

  loading = false;
  error: string | null = null;
  result: AgentResponse | null = null;
  currentFen = '';

  /** The last positions analysed, read back from MongoDB. */
  history: Interaction[] = [];
  analysisCount = 0;

  /** A few positions that show what the agent does. */
  readonly demoPositions: DemoPosition[] = [
    {
      label: 'Position de départ',
      fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
    },
    {
      label: 'Ouverture italienne',
      fen: 'r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3',
    },
    {
      label: 'Partie espagnole',
      fen: 'r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3',
    },
    {
      label: 'Défense sicilienne',
      fen: 'rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
    },
    {
      label: 'Hors théorie (2.Dh5)',
      fen: 'rnbqkbnr/pppp1ppp/8/4p2Q/4P3/8/PPPP1PPP/RNB1KBNR b KQkq - 1 2',
    },
  ];

  constructor(private readonly agent: AgentService) {
    this.refreshHistory();
  }

  /** Read back the last analyses the agent recorded. */
  refreshHistory(): void {
    this.agent.history(5).subscribe({
      next: (response) => {
        this.history = response.interactions;
        this.analysisCount = response.total;
      },
      // The history is a convenience: losing it must break nothing.
      error: () => undefined,
    });
  }

  /** Reload a position that has already been analysed. */
  replay(interaction: Interaction): void {
    this.board.setFEN(interaction.fen);
    this.analyse(interaction.fen);
  }

  /** Time only: the history covers the current session. */
  timeOf(timestamp: string): string {
    const date = new Date(timestamp);
    return isNaN(date.getTime())
      ? ''
      : date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  }

  /** Called on every move played on the board. */
  onMovePlayed(): void {
    this.analyse(this.board.getFEN());
  }

  /** Load a demonstration position, then analyse it. */
  loadDemo(position: DemoPosition): void {
    this.board.setFEN(position.fen);
    this.analyse(position.fen);
  }

  /** Step back one move. */
  undoMove(): void {
    this.board.undo();
    this.analyse(this.board.getFEN());
  }

  /** Flip the board, to see it from Black's side. */
  flipBoard(): void {
    this.board.reverse();
  }

  /** Back to the starting position, and clear the panel. */
  resetBoard(): void {
    this.board.reset();
    this.result = null;
    this.error = null;
    this.currentFen = '';
  }

  /** Ask the backend to analyse the current position. */
  analyse(fen: string): void {
    this.loading = true;
    this.error = null;
    this.currentFen = fen;
    this.agent.analyze(fen).subscribe({
      next: (response) => {
        this.result = response;
        this.loading = false;
        // The agent has just written one more row to MongoDB.
        this.refreshHistory();
      },
      error: () => {
        this.error = "Impossible de contacter l'agent. Vérifiez que le backend est démarré.";
        this.loading = false;
      },
    });
  }
}
