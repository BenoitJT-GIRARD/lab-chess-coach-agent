import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Observable, of } from 'rxjs';

import { ChessboardComponent } from './chessboard.component';
import { AgentService } from '../services/agent.service';
import { AgentResponse, HistoryResponse } from '../models/agent.models';

const HISTORIQUE: HistoryResponse = {
  total: 7,
  interactions: [
    {
      fen: 'rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
      opening_name: 'Sicilian Defense',
      in_theory: true,
      sources_used: ['theory'],
      created_at: '2026-09-02T09:30:00+00:00',
    },
    {
      fen: 'rnbqkbnr/pppp1ppp/8/4p2Q/4P3/8/PPPP1PPP/RNB1KBNR b KQkq - 1 2',
      opening_name: null,
      in_theory: false,
      sources_used: ['engine'],
      created_at: '2026-09-02T09:20:00+00:00',
    },
  ],
};

class FakeAgentService {
  analyseeAvec: string | null = null;

  analyze(fen: string): Observable<AgentResponse> {
    this.analyseeAvec = fen;
    return of({} as AgentResponse);
  }

  history(): Observable<HistoryResponse> {
    return of(HISTORIQUE);
  }
}

describe('ChessboardComponent', () => {
  let fixture: ComponentFixture<ChessboardComponent>;
  let agent: FakeAgentService;

  beforeEach(async () => {
    agent = new FakeAgentService();
    await TestBed.configureTestingModule({
      imports: [ChessboardComponent, NoopAnimationsModule],
      providers: [{ provide: AgentService, useValue: agent }],
    }).compileComponents();
    fixture = TestBed.createComponent(ChessboardComponent);
    fixture.detectChanges();
  });

  it('propose les positions préparées pour la démonstration', () => {
    const texte = fixture.nativeElement.textContent as string;

    expect(texte).toContain('Ouverture italienne');
    expect(texte).toContain('Partie espagnole');
    expect(texte).toContain('Hors théorie (2.Dh5)');
  });

  it('affiche les dernières analyses enregistrées', () => {
    const texte = fixture.nativeElement.textContent as string;

    expect(texte).toContain('Sicilian Defense');
    expect(texte).toContain('Hors théorie');
    expect(texte).toContain('7 au total');
  });

  it("rejoue une position de l'historique", () => {
    fixture.componentInstance.rejouer(HISTORIQUE.interactions[0]);

    expect(agent.analyseeAvec).toBe(HISTORIQUE.interactions[0].fen);
  });

  it("n'affiche que l'heure des analyses", () => {
    expect(fixture.componentInstance.heure('2026-09-02T09:30:00+00:00')).toMatch(/^\d{2}:\d{2}$/);
    expect(fixture.componentInstance.heure('pas une date')).toBe('');
  });
});
