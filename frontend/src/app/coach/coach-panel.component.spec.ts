import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { CoachPanelComponent } from './coach-panel.component';
import { AgentResponse } from '../models/agent.models';

const ANSWER: AgentResponse = {
  fen: 'r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3',
  valid: true,
  opening_name: 'Italian Game',
  opening_eco: 'C50',
  in_theory: true,
  total_games: 48726,
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
  opening_summary:
    "L'italienne est l'une des plus anciennes ouvertures : le fou en c4 vise la case f7.",
  recommendation: "Nous sommes dans l'ouverture italienne.",
  sources_used: ['theory', 'rag', 'llm'],
  error: null,
};

describe('CoachPanelComponent', () => {
  let fixture: ComponentFixture<CoachPanelComponent>;

  const text = (): string => fixture.nativeElement.textContent as string;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CoachPanelComponent, NoopAnimationsModule],
    }).compileComponents();
    fixture = TestBed.createComponent(CoachPanelComponent);
  });

  it('invites a move while nothing has been analysed', () => {
    fixture.detectChanges();

    expect(text()).toContain('Jouez un coup');
  });

  it('shows a spinner while the analysis runs', () => {
    fixture.componentInstance.loading = true;
    fixture.detectChanges();

    expect(text()).toContain("L'agent analyse la position");
    expect(fixture.nativeElement.querySelector('mat-spinner')).toBeTruthy();
  });

  it('shows the message when the backend does not answer', () => {
    fixture.componentInstance.error = 'Impossible de contacter l\'agent.';
    fixture.detectChanges();

    expect(text()).toContain('Impossible de contacter');
  });

  it('renders the opening, the moves and the reference games', () => {
    fixture.componentInstance.result = ANSWER;
    fixture.detectChanges();

    const rendered = text();
    expect(rendered).toContain('Italian Game');
    expect(rendered).toContain('C50');
    expect(rendered).toContain('Bc5');
    expect(rendered).toContain('Caruana');
    expect(rendered).toContain('0-1');
    expect(rendered).toContain('Le fou en c4 vise la case f7.');
  });

  it('flags a line that is named but rarely played', () => {
    fixture.componentInstance.result = {
      ...ANSWER,
      in_theory: false,
      opening_name: "King's Pawn Game: Wayward Queen Attack",
      total_games: 48,
    };
    fixture.detectChanges();

    const rendered = text();
    expect(rendered).toContain('Wayward Queen Attack');
    expect(rendered).toContain('Hors théorie');
    expect(rendered).toContain('48 parties de maîtres');
  });

  it('presents the detected opening', () => {
    fixture.componentInstance.result = ANSWER;
    fixture.detectChanges();

    const rendered = text();
    expect(rendered).toContain('Ouverture détectée');
    expect(rendered).toContain("le fou en c4 vise la case f7");
  });

  it('puts the most played move forward inside theory', () => {
    fixture.componentInstance.result = ANSWER;
    fixture.detectChanges();

    // The French thousands separator is a narrow no-break space: rebuild it rather than
    // freezing it into the test.
    const games = (25481).toLocaleString('fr-FR');
    expect(fixture.componentInstance.nextMove).toEqual({
      san: 'Bc5',
      reason: `le plus joué en parties de maîtres (${games})`,
    });
    expect(text()).toContain('Prochain coup');
  });

  it('puts the engine move forward outside theory', () => {
    fixture.componentInstance.result = {
      ...ANSWER,
      in_theory: false,
      theory_moves: [],
      evaluation: {
        fen: ANSWER.fen,
        evaluation_type: 'cp',
        value: 29,
        perspective: 'white',
        best_move: 'b8c6',
        best_move_san: 'Nc6',
        depth: 15,
      },
    };
    fixture.detectChanges();

    expect(fixture.componentInstance.nextMove).toEqual({
      san: 'Nc6',
      reason: 'recommandé par Stockfish (profondeur 15)',
    });
  });

  it('invents no move when there is none', () => {
    fixture.componentInstance.result = {
      ...ANSWER,
      in_theory: false,
      theory_moves: [],
      evaluation: null,
    };

    expect(fixture.componentInstance.nextMove).toBeNull();
  });

  it('names the tools that were used, in plain words', () => {
    fixture.componentInstance.result = ANSWER;
    fixture.detectChanges();

    const rendered = text();
    expect(rendered).toContain('Théorie Lichess');
    expect(rendered).toContain('Base Wikichess');
    expect(rendered).toContain('Modèle de langage');
  });

  it('formats the engine evaluations', () => {
    const composant = fixture.componentInstance;

    composant.result = {
      ...ANSWER,
      evaluation: {
        fen: ANSWER.fen,
        evaluation_type: 'cp',
        value: 29,
        perspective: 'white',
        best_move: 'b8c6',
        best_move_san: 'Nc6',
        depth: 15,
      },
    };
    expect(composant.evaluationLabel()).toBe('+0.29');

    composant.result = {
      ...composant.result,
      evaluation: { ...composant.result.evaluation!, evaluation_type: 'mate', value: -3 },
    };
    expect(composant.evaluationLabel()).toBe('Mat en 3');
  });
});
