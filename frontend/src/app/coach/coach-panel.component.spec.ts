import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { CoachPanelComponent } from './coach-panel.component';
import { AgentResponse } from '../models/agent.models';

const REPONSE: AgentResponse = {
  fen: 'r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3',
  valid: true,
  opening_name: 'Italian Game',
  opening_eco: 'C50',
  in_theory: true,
  theory_moves: [
    { uci: 'f8c5', san: 'Bc5', white: 1, draws: 1, black: 1, total: 25481, source: 'lichess' },
  ],
  reference_games: [
    {
      game_id: 'abc123',
      white: 'Caruana',
      black: 'Carlsen',
      white_rating: 2820,
      black_rating: 2863,
      winner: 'black',
      year: 2020,
      url: 'https://lichess.org/abc123',
      result: '0-1',
    },
  ],
  evaluation: null,
  passages: [
    { text: 'Le fou en c4 vise la case f7.', opening: 'Giuoco Piano', source: 'x.md', score: 0.7 },
  ],
  videos: [],
  recommendation: "Nous sommes dans l'ouverture italienne.",
  sources_used: ['theory', 'rag', 'llm'],
  error: null,
};

describe('CoachPanelComponent', () => {
  let fixture: ComponentFixture<CoachPanelComponent>;

  const texte = (): string => fixture.nativeElement.textContent as string;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CoachPanelComponent, NoopAnimationsModule],
    }).compileComponents();
    fixture = TestBed.createComponent(CoachPanelComponent);
  });

  it('invite à jouer un coup tant que rien n\'a été analysé', () => {
    fixture.detectChanges();

    expect(texte()).toContain('Jouez un coup');
  });

  it('affiche un indicateur pendant l\'analyse', () => {
    fixture.componentInstance.chargement = true;
    fixture.detectChanges();

    expect(texte()).toContain("L'agent analyse la position");
    expect(fixture.nativeElement.querySelector('mat-spinner')).toBeTruthy();
  });

  it('affiche le message quand le backend ne répond pas', () => {
    fixture.componentInstance.erreur = 'Impossible de contacter l\'agent.';
    fixture.detectChanges();

    expect(texte()).toContain('Impossible de contacter');
  });

  it("présente l'ouverture, les coups et les parties de référence", () => {
    fixture.componentInstance.resultat = REPONSE;
    fixture.detectChanges();

    const rendu = texte();
    expect(rendu).toContain('Italian Game');
    expect(rendu).toContain('C50');
    expect(rendu).toContain('Bc5');
    expect(rendu).toContain('Caruana');
    expect(rendu).toContain('0-1');
    expect(rendu).toContain('Le fou en c4 vise la case f7.');
  });

  it('nomme les outils utilisés en clair', () => {
    fixture.componentInstance.resultat = REPONSE;
    fixture.detectChanges();

    const rendu = texte();
    expect(rendu).toContain('Théorie Lichess');
    expect(rendu).toContain('Base Wikichess');
    expect(rendu).toContain('Modèle de langage');
  });

  it('met en forme les évaluations du moteur', () => {
    const composant = fixture.componentInstance;

    composant.resultat = {
      ...REPONSE,
      evaluation: {
        fen: REPONSE.fen,
        evaluation_type: 'cp',
        value: 29,
        perspective: 'white',
        best_move: 'b8c6',
        best_move_san: 'Nc6',
        depth: 15,
      },
    };
    expect(composant.libelleEvaluation()).toBe('+0.29');

    composant.resultat = {
      ...composant.resultat,
      evaluation: { ...composant.resultat.evaluation!, evaluation_type: 'mate', value: -3 },
    };
    expect(composant.libelleEvaluation()).toBe('Mat en 3');
  });
});
