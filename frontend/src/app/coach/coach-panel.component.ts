import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { AgentResponse } from '../models/agent.models';

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
