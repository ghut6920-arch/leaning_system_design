"""Executable fictional teaching example, not a real sensor or learner submission.

Specified input: raw[n][t][c], exactly two channels, numeric range 0..10.
Returns v[N,C,T], g[N,C,T] and f[N,T]. Only the standard library is needed.
"""


def pipeline(raw):
    n, t = len(raw), len(raw[0])
    gain = [1, 2]
    v = [[[raw[i][j][c] / 10 for j in range(t)] for c in range(2)] for i in range(n)]
    g = [[[v[i][c][j] * gain[c] for j in range(t)] for c in range(2)] for i in range(n)]
    f = [[sum(g[i][c][j] for c in range(2)) for j in range(t)] for i in range(n)]
    return v, g, f
