import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AgentResponse, HistoryResponse } from '../models/agent.models';

/**
 * Talks to the Chess Coach backend. The base path is relative ("/api/v1") so the
 * same build works behind the nginx reverse proxy (Docker) and the Angular dev
 * proxy (ng serve).
 */
@Injectable({ providedIn: 'root' })
export class AgentService {
  private readonly base = '/api/v1';

  constructor(private readonly http: HttpClient) {}

  /** Run the full coaching agent on a position. */
  analyze(fen: string): Observable<AgentResponse> {
    return this.http.post<AgentResponse>(`${this.base}/agent`, { fen });
  }

  /** Read back the positions the agent analysed recently (MongoDB). */
  history(limit = 5): Observable<HistoryResponse> {
    return this.http.get<HistoryResponse>(`${this.base}/history`, {
      params: { limit },
    });
  }
}
