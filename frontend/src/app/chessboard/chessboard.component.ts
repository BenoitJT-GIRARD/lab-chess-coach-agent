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

/** Une position préparée pour la démonstration. */
interface PositionDemo {
  libelle: string;
  fen: string;
}

/**
 * L'écran de travail : l'échiquier à gauche, le panneau du coach à droite.
 *
 * Ce composant tient l'état de la partie et parle au backend. Le panneau, lui,
 * ne fait qu'afficher ce qu'on lui donne.
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

  /** Taille de l'échiquier, en pixels. */
  readonly taille = 420;
  readonly caseClaire = '#f4f1ea';
  readonly caseSombre = '#7d8a99';

  chargement = false;
  erreur: string | null = null;
  resultat: AgentResponse | null = null;
  fenCourante = '';

  /** Dernières positions analysées, relues depuis MongoDB. */
  historique: Interaction[] = [];
  totalAnalyses = 0;

  /** Quelques positions parlantes pour la démonstration au client. */
  readonly positionsDemo: PositionDemo[] = [
    {
      libelle: 'Position de départ',
      fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
    },
    {
      libelle: 'Ouverture italienne',
      fen: 'r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3',
    },
    {
      libelle: 'Partie espagnole',
      fen: 'r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3',
    },
    {
      libelle: 'Défense sicilienne',
      fen: 'rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
    },
    {
      libelle: 'Hors théorie (2.Dh5)',
      fen: 'rnbqkbnr/pppp1ppp/8/4p2Q/4P3/8/PPPP1PPP/RNB1KBNR b KQkq - 1 2',
    },
  ];

  constructor(private readonly agent: AgentService) {
    this.rafraichirHistorique();
  }

  /** Relit les dernières analyses enregistrées par l'agent. */
  rafraichirHistorique(): void {
    this.agent.history(5).subscribe({
      next: (reponse) => {
        this.historique = reponse.interactions;
        this.totalAnalyses = reponse.total;
      },
      // L'historique est un confort : son absence ne doit rien casser.
      error: () => undefined,
    });
  }

  /** Recharge une position déjà analysée. */
  rejouer(interaction: Interaction): void {
    this.board.setFEN(interaction.fen);
    this.analyser(interaction.fen);
  }

  /** N'affiche que l'heure : l'historique porte sur la session en cours. */
  heure(horodatage: string): string {
    const date = new Date(horodatage);
    return isNaN(date.getTime())
      ? ''
      : date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  }

  /** Appelé à chaque coup joué sur l'échiquier. */
  auCoupJoue(): void {
    this.analyser(this.board.getFEN());
  }

  /** Charge une position de démonstration puis l'analyse. */
  chargerDemo(position: PositionDemo): void {
    this.board.setFEN(position.fen);
    this.analyser(position.fen);
  }

  /** Revient au coup précédent. */
  annulerCoup(): void {
    this.board.undo();
    this.analyser(this.board.getFEN());
  }

  /** Retourne l'échiquier, pour se mettre du point de vue des Noirs. */
  retourner(): void {
    this.board.reverse();
  }

  /** Remet la position de départ et vide le panneau. */
  reinitialiser(): void {
    this.board.reset();
    this.resultat = null;
    this.erreur = null;
    this.fenCourante = '';
  }

  /** Demande au backend l'analyse de la position courante. */
  analyser(fen: string): void {
    this.chargement = true;
    this.erreur = null;
    this.fenCourante = fen;
    this.agent.analyze(fen).subscribe({
      next: (reponse) => {
        this.resultat = reponse;
        this.chargement = false;
        // L'agent vient d'écrire une ligne de plus dans MongoDB.
        this.rafraichirHistorique();
      },
      error: () => {
        this.erreur = "Impossible de contacter l'agent. Vérifiez que le backend est démarré.";
        this.chargement = false;
      },
    });
  }
}
