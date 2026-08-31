import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { AgentService } from './agent.service';
import { AgentResponse } from '../models/agent.models';

const FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

describe('AgentService', () => {
  let service: AgentService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [AgentService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AgentService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it("envoie la position à l'agent sur un chemin relatif", () => {
    service.analyze(FEN).subscribe();

    const requete = http.expectOne('/api/v1/agent');
    expect(requete.request.method).toBe('POST');
    expect(requete.request.body).toEqual({ fen: FEN });
    requete.flush({});
  });

  it("remonte la réponse de l'agent telle quelle", () => {
    let recu: AgentResponse | undefined;
    service.analyze(FEN).subscribe((reponse) => (recu = reponse));

    http.expectOne('/api/v1/agent').flush({ fen: FEN, opening_name: 'Italian Game' });

    expect(recu?.opening_name).toBe('Italian Game');
  });
});
