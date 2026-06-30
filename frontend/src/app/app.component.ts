import { Component, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { NgxChessBoardModule, NgxChessBoardView } from 'ngx-chess-board';
import { AgentService } from './services/agent.service';
import { AgentResponse } from './models/agent.models';

interface DemoPosition {
  label: string;
  fen: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, NgxChessBoardModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  @ViewChild('board') board!: NgxChessBoardView;

  loading = false;
  error: string | null = null;
  result: AgentResponse | null = null;
  currentFen = '';

  /** A few interesting positions for the demonstration. */
  readonly demoPositions: DemoPosition[] = [
    { label: 'Position de départ', fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1' },
    {
      label: 'Ouverture italienne',
      fen: 'r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3',
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

  constructor(
    private readonly agent: AgentService,
    private readonly sanitizer: DomSanitizer,
  ) {}

  /** Called whenever a move is played on the board. */
  onMove(): void {
    this.analyze(this.board.getFEN());
  }

  /** Load a demo position on the board and analyse it. */
  loadDemo(position: DemoPosition): void {
    this.board.setFEN(position.fen);
    this.analyze(position.fen);
  }

  reset(): void {
    this.board.reset();
    this.result = null;
    this.error = null;
    this.currentFen = '';
  }

  /** Ask the backend agent to analyse the current position. */
  analyze(fen: string): void {
    this.loading = true;
    this.error = null;
    this.currentFen = fen;
    this.agent.analyze(fen).subscribe({
      next: (response) => {
        this.result = response;
        this.loading = false;
      },
      error: () => {
        this.error = "Impossible de contacter l'agent. Vérifiez que le backend est démarré.";
        this.loading = false;
      },
    });
  }

  /** Build a safe YouTube embed URL for the first suggested video. */
  embedUrl(videoId: string): SafeResourceUrl {
    return this.sanitizer.bypassSecurityTrustResourceUrl(
      `https://www.youtube.com/embed/${videoId}`,
    );
  }

  /** Format a Stockfish evaluation as a short, readable label. */
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
}
