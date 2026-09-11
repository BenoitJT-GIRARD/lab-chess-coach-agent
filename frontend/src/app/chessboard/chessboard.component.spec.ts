import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Observable, of } from 'rxjs';

import { ChessboardComponent } from './chessboard.component';
import { AgentService } from '../services/agent.service';
import { AgentResponse, HistoryResponse } from '../models/agent.models';

const HISTORY: HistoryResponse = {
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
    return of(HISTORY);
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

  it('offers the prepared demonstration positions', () => {
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Ouverture italienne');
    expect(text).toContain('Partie espagnole');
    expect(text).toContain('Hors théorie (2.Dh5)');
  });

  it('shows the last analyses recorded', () => {
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Sicilian Defense');
    expect(text).toContain('Hors théorie');
    expect(text).toContain('7 au total');
  });

  it('replays a position from the history', () => {
    fixture.componentInstance.replay(HISTORY.interactions[0]);

    expect(agent.analyseeAvec).toBe(HISTORY.interactions[0].fen);
  });

  it('shows only the time of an analysis, not its date', () => {
    expect(fixture.componentInstance.timeOf('2026-09-02T09:30:00+00:00')).toMatch(/^\d{2}:\d{2}$/);
    expect(fixture.componentInstance.timeOf('pas une date')).toBe('');
  });
});
