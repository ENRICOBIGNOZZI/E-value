# Lambda selection: certificate, log growth and actual horizon power

For the Catoni increment q_lambda(Y)=phi(lambda Y)-lambda² v²/2, T2 maximizes
the lower power certificate lambda*delta-lambda² v². Its optimizer
delta/(2 v²) is **not** a general optimizer of actual rejection probability.

## Exact working-model log growth

For a conditional working score distribution with mean delta and raw second
moment at most v², define g(lambda)=E phi(lambda Y)-lambda² v²/2. Direct
differentiation gives

    phi'(x) = (1+abs(x))/(1+abs(x)+x²/2),
    phi''(x) = -sign(x)*(abs(x)+x²/2)/(1+abs(x)+x²/2)².

The absolute second derivative is at most 1/4: after setting u=1+abs(x),
maximize 2(u²-1)/(u²+1)², whose maximum is 1/4 at u²=3. Dominated
differentiation is justified by finite E Y². Hence

    -5 v²/4 <= g''(lambda) <= -3 v²/4 < 0.

The unconstrained optimizer is zero when delta<=0. If delta>0 it is the unique
root of E[Y phi'(lambda Y)] = lambda v², between 4delta/(5v²) and
4delta/(3v²); a finite cap clips this optimizer. For small scores it is near
delta/v², approximately twice the power-certificate bet. This can improve
actual growth while making the old inverse-capital lower bound vacuous; the
two criteria must not be equated. With a fitted working law the optimization
concerns predicted growth, not guaranteed optimal growth under the true law.

## Finite-horizon review power

Fix a working law for future score blocks and a finite action set A of
nonnegative, allowable pre-block bets. Let Q_lambda be the working distribution
of Z_lambda=sum_{i=1}^h phi(lambda Y_i)-h*lambda²*v²/2. With b=log(1/alpha),

    V_0(ell)=1{ell>=b},
    V_k(ell)=1                         if ell>=b,
              max_{lambda in A} E[V_{k-1}(ell+Z_lambda)] otherwise.

Backward induction proves that V_k is the maximum probability of hitting the
review threshold within k remaining blocks under this working model and
action class. A maximizing action selected from current ell and k is
predictable. Therefore the real process remains T1-valid under its real
conditional null and public moment bound, even if the working power model is
wrong. Model misspecification changes power and optimality, not that validity
argument. Re-fitting on an unobserved future block is not allowed.

This standard Bellman principle is a specialization of finite-horizon target
reachability, not a new control theorem. See the primary treatment by
[Chatterjee, Cinquemani and Lygeros](https://arxiv.org/html/0904.4143) for the
broader hitting-probability control problem. Betting log optimality is already
developed in the sources cited in the manuscript, particularly
[Waudby-Smith, Sandoval and Jordan](https://arxiv.org/html/2504.02818v2).
The computed experiment discretizes both action and capital spaces and audits
refinement; it does not assert a continuous-control global optimum.

## Exact one-date target illustrates why the horizon matters

If only one observation remains, with current gap c=b-log E>0, any lambda>0
crosses precisely when

    Y >= b_c(lambda)
       = [sqrt(2 exp(c+lambda² v²/2)-1)-1]/lambda.

Thus minimizing b_c over allowable lambda maximizes one-date power for every
score law simultaneously, since the rejection events are nested in that
threshold. Without a cap the minimizer can be written using the unique q>1
solving

    c = log[(q²+1)/2] - q(q-1)/(q²+1),
    lambda² v² = 2 q(q-1)/(q²+1).

The first right-hand side is strictly increasing from zero to infinity:
its derivative is (2q³-q²+1)/(q²+1)²>0. The optimum lambda*v tends to zero
as c decreases to zero and to sqrt(2) as c increases. With a cap, clip this
one-dimensional minimum. A greedy final-step rule need not maximize the
probability of crossing over many blocks; its aggressive bets can sacrifice
future evidence. The actual study evaluates the same 100-date bet/review
calendar for every rule and optimizes its full block distribution, rather
than substituting this one-date formula for a full-block optimum.

These results concern statistical lambda, not an investible portfolio weight.
They do not remove a conservative risk envelope, a small economic gain, a
positive minimum-effect filter, costs or regime changes. The new stationary
controlled experiment is not evidence of improved full-fund performance.
