import { Component } from '@angular/core';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatIconModule } from '@angular/material/icon';
import { ChessboardComponent } from './chessboard/chessboard.component';

/**
 * Coquille de l'application : la barre de titre et l'écran de travail.
 *
 * La structure suit un motif Angular Material classique :
 * une barre Material,
 * puis un composant qui porte l'échiquier.
 */
@Component({
  selector: 'app-root',
  standalone: true,
  imports: [MatToolbarModule, MatIconModule, ChessboardComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  readonly titre = 'Chess Coach';
  readonly subtitle = "Coach d'ouvertures";
}
