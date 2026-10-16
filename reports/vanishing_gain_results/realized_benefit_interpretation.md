# Realized cumulative utility on the original saved scalar paths

This is a post-hoc summary of fields already saved by source freeze **57752eb**.
It uses the original **4,096 paths under each law**, at the fixed unstopped
horizon **65,536** with 32 training observations. Both archive hashes still
match the independent audit. No observation, parameter, horizon, seed, bet or
financial arm is changed. The original independent score replay remains the
declared eight-path prefix under each law; this summary does not extend it.

Under the iid Gaussian alternative, mean conditional cumulative benefit is
**3.854828** (MC SE **0.041735**), while mean realized cumulative cash advantage
is **3.871292** (MC SE **0.015831**). The paired realized-minus-conditional mean
is **0.016464**, with MC SE **0.044965**. Fourteen of 4,096 realized cumulative
advantages are negative: observed fraction 0.003418, Wilson 95% interval
[0.002037,0.005729]. These are toy cumulative quadratic-utility units, not
annual returns, certainty equivalents, or compounded wealth.

Under the Gaussian feedback boundary null, the conditional cumulative mean is
zero up to rounding. The realized mean is **−0.056445** (MC SE **0.093895**).
There are 1,331 negative realized sums, fraction 0.324951, Wilson interval
[0.310778,0.339453]. These descriptive summaries are not new type-I-error or
power estimates. Existing crossing counts remain unchanged.

The new proof makes explicit an implication of the existing martingale
normalization: for the Gaussian alternative, J_n=sum Y_t and
C_n=sum E(Y_t|past) satisfy J_n/C_n -> 1 almost surely. Conditional variance
is bounded by a constant times w_t². Dividing its martingale differences by
the predictable 1+sum_{s<=t}w_s² gives a convergent square-integrable series;
Kronecker's lemma supplies the ratio. Thus the attained coefficient 4/gamma
and the arbitrary-valid-test-family lower bound in probability transfer from
conditional benefits to realized cumulative utility. Finite realized sums
need not be positive or monotone.

The proof concerns the same costless scalar Gaussian estimated policy and
the limit alpha->0. Fixed-horizon averages cannot be substituted for stopped
benefits, and the finite simulation does not prove the asymptotic result.
Neither expected stopping-time nor expected stopped-benefit equivalence has
been established. Costs, multiple comparisons, closures, changing regimes and
the actual financial fund remain outside this example.
