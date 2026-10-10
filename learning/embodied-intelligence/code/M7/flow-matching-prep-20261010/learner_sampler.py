"""M7.2 learner-owned core placeholder, AI scaffold revision 1, 2026-10-10.

Independent specification: SAMPLER_SPEC.md. No learner implementation exists yet.
If the complete teacher implementation has been read, subsequent use is supported
implementation/modification/tracing, not an unseen independent implementation.
"""


def euler_sample(field, z, c, n_steps):
    """field(x[B,2],t_scalar,c[B])->velocity[B,2]; return endpoint[B,2]."""
    raise NotImplementedError("Implement the sampler from SAMPLER_SPEC.md; preserve your own original version.")
