import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { AgentResponse } from '../models/agent.models';

/** Le coup mis en avant, avec la raison qui le justifie. */
interface ProchainCoup {
  san: string;
  raison: string;
}

/**
 * Affiche la réponse de l'agent : ouverture, coups théoriques, parties de
 * référence, évaluation du moteur, extraits de la base et vidéos.
 *
 * Composant purement présentatif : il ne fait aucun appel réseau et se contente
 * de mettre en forme ce qu'on lui passe.
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
  @Input() chargement = false;
  @Input() erreur: string | null = null;
  @Input() resultat: AgentResponse | null = null;

  constructor(private readonly sanitizer: DomSanitizer) {}

  /**
   * Le coup à jouer maintenant.
   *
   * Dans la théorie, c'est le coup le plus joué en parties de maîtres. Hors
   * théorie, c'est celui que recommande le moteur. Les deux cas s'excluent :
   * l'agent n'appelle Stockfish que lorsqu'il sort de la théorie.
   */
  get prochainCoup(): ProchainCoup | null {
    const resultat = this.resultat;
    if (!resultat) {
      return null;
    }

    if (resultat.in_theory && resultat.theory_moves.length) {
      const coup = resultat.theory_moves[0];
      const parties = this.nombreDeParties(coup.total);
      return {
        san: coup.san,
        raison: parties
          ? `le plus joué en parties de maîtres (${parties})`
          : 'coup principal de la théorie',
      };
    }

    const evaluation = resultat.evaluation;
    if (evaluation?.best_move_san) {
      return {
        san: evaluation.best_move_san,
        raison: `recommandé par Stockfish (profondeur ${evaluation.depth})`,
      };
    }

    return null;
  }

  /** Construit l'URL d'intégration de la première vidéo proposée. */
  urlIntegration(videoId: string): SafeResourceUrl {
    return this.sanitizer.bypassSecurityTrustResourceUrl(
      `https://www.youtube.com/embed/${videoId}`,
    );
  }

  /** Met l'évaluation Stockfish sous une forme lisible. */
  libelleEvaluation(): string {
    const evaluation = this.resultat?.evaluation;
    if (!evaluation) {
      return '';
    }
    if (evaluation.evaluation_type === 'mate') {
      return `Mat en ${Math.abs(evaluation.value)}`;
    }
    const pions = evaluation.value / 100;
    return `${pions >= 0 ? '+' : ''}${pions.toFixed(2)}`;
  }

  /** Nombre de parties dans lesquelles un coup a été joué, formaté. */
  nombreDeParties(total: number): string {
    return total > 0 ? total.toLocaleString('fr-FR') : '';
  }

  /** Nom lisible d'un outil utilisé par l'agent. */
  libelleSource(source: string): string {
    const libelles: Record<string, string> = {
      theory: 'Théorie Lichess',
      engine: 'Moteur Stockfish',
      rag: 'Base Wikichess',
      youtube: 'API YouTube',
      llm: 'Modèle de langage',
    };
    return libelles[source] ?? source;
  }
}
