"""Measuring the two decisions the agent takes.

The agent chooses an information source — theory or engine, on a threshold — and it
chooses a query to send to the knowledge base. Neither choice was measured; both are
now, with hard labels and no judge.

- ``cases`` loads the evaluation set and its relevance labels;
- ``metrics`` holds recall@k and MRR, written out rather than imported;
- ``variants`` holds the query formulations the ablation compares;
- ``threshold`` sweeps the routing threshold over a frozen reading.
"""
