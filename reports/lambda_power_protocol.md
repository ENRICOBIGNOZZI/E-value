# Pre-evaluation freeze: selecting lambda for finite-horizon power

This study responds to the user's request to select lambda to maximize power.
It is a **new controlled score experiment**, separate from the frozen financial
pilots and from the earlier costless vanishing-gain study. No already observed
financial path is used to select a winning bet or change the primary methods.

The target is probability of first rejection **at a review within a declared
horizon**, at individual alpha=.05. All methods use the same Catoni process,
public raw-second-moment certificate nu²=1.09, and cap lambda<=.5/sqrt(nu²).
Bets are held for **100 observations** and decisions occur only at block ends.
Horizons are **400, 800 and 1600 observations**. Thus any improvement is not
obtained by giving one method more frequent betting or rejection opportunities.

For power design, a fixed, declared working score law is N(.1,1). This is a
design alternative, not a simulator truth column or an estimate based on the
evaluation data. Bellman state is remaining blocks and current log capital.
The action maximizes the working-model probability of hitting log(20) before
the horizon. This is a standard finite-horizon reachability problem; no claim
of a new dynamic-programming principle is made.

Evaluate these rules on identical paths within each law:

1. Original past-positive-mean certificate bet, with initial design gain .1.
2. Fixed certificate bet .1/(2*1.09), which maximizes T2's inverse-capital bound.
3. Fixed bet maximizing exact working-model expected Catoni log growth.
4. A greedy one-block power rule, repeatedly using the Bellman final-block rule.
5. Horizon-specific Bellman rules on the primary numerical grid.
6. The same horizon-specific rules on a finer grid and wider lower boundary.

The fixed growth bet maximizes an expectation, not finite-horizon crossing
power. The Bellman rule targets crossing power directly. Its numerical maximum
is over the declared action and capital grids under the working model, not a
guarantee of maximal power for unknown or changing financial score laws.
Every selected lambda depends only on the pre-block capital, past scores and
fixed design information. T1 validity therefore does not require the working
alternative to be correct.

Numerical model construction consumes **no evaluation random numbers**. Exact
Gaussian CDF differences give daily increment-bin probabilities. FFT convolution
forms the distribution of a full 100-observation constant-bet block. FFT mass
error, clipped numerical negative masses and truncation are checked; a 12-sigma
normal tail has probability at most 2*Phi(-12) per date before discretization.
The primary capital step is .01, lower boundary -18 and 129 regular actions;
the refinement uses .005, -24 and 257 regular actions. Both action grids also
include the fixed certificate and log-growth bets. The computational lower
boundary is absorbing; its approximation is assessed by the wider refinement.

Before evaluation, the predicted powers at the initial capital are respectively
0.37273, 0.72996 and 0.96936 on the primary grid, and 0.37233, 0.72988 and
0.96953 on the refinement. Maximum discrepancy .000396 is below the predeclared
.005 numerical tolerance. These are **working-model calculations**, not observed
Monte Carlo power, a global continuous-control optimum or a validity proof.

Fresh scientific seed **440001** is untouched at this freeze. Independent
SeedSequence children generate **20,000 paths per law** at actual means
0, .1, .2 and .3 and standard deviation one. All laws satisfy the common raw
second-moment cap. Mean zero is the conditional boundary null; .1 matches the
working alternative, while .2 and .3 assess misspecification. Three separate
software checks use seed 950001 and tiny grids. Retain every replication.

Record review-time first crossings, all pre-block stakes, block-end capitals
and the first sixteen score paths for independent multiplicative replay.
Use path-level Wilson intervals and paired Monte Carlo differences on shared
paths. Zero crossings do not prove zero error. Individual 5% validity is not
simultaneous control over the collection of compared rules.

Freeze the script, configuration, model digests and this protocol in Git before
the first evaluation draw. Do not revise a grid, threshold, horizon or rule
based on evaluation winners. Any numerical-model deficiency must be reported.
The full financial v3 pilot continues with its own source unchanged. Financial
adoption would require a separately declared policy and fresh financial evidence.
