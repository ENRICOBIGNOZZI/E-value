# Closest prior work and scope of the contribution

Primary sources consulted in this continuation:

- Henzi and Ziegel, *Valid sequential inference on probability forecast performance*,
  https://arxiv.org/abs/2103.08402 and published correction
  https://doi.org/10.1093/biomet/asac043. Sequential comparison of competing
  forecast scores using e-values already exists; this is not a new general idea.
- Choe and Ramdas, *Comparing Sequential Forecasters*,
  https://arxiv.org/abs/2110.00115. This includes time-varying average score
  comparisons and weak-null formulations. The baseline T1 only proves its
  datewise conditional null, so its guarantee must not be advertised as
  weak-null average-performance control.
- Waudby-Smith and Ramdas, *Estimating means of bounded random variables by betting*,
  https://arxiv.org/abs/2010.09686. Predictable linear betting and mixtures are
  established tools. The new section specializes these using a lower-tail bias
  correction, without claiming to invent the general construction.
- Lugosi and Mendelson, *Mean estimation and regression under heavy-tailed
  distributions—a survey*, https://arxiv.org/abs/1906.04280. Moment-based
  inference and rare-event lower-bound techniques have a substantial existing
  literature. The two-point local information bound in this manuscript is
  presented with its proof and scope, not as an unqualified novel minimax result.

All sleeve outcomes are observed on the common market path. The problem is
full-information comparison of adaptive investment policies with stateful
costs; it does not require the importance-weighting machinery used when rewards
for unchosen actions are missing. This distinction matters when selecting
related work and benchmarks.

The defensible contribution currently consists of explicit economic/state
accounting, a public label-free policy-geometry moment envelope, a corrected-tail
specialization with stronger moment assumptions, and transparent feasibility
experiments. A complete independent prior-art review and full-strategy evidence
are still needed before a strong publication or novelty claim.
