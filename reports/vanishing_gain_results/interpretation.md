# Executed vanishing-gain diagnostic

The two declared laws each have **4,096 paths and 65,536 evaluated observations**,
after 32 training observations. Source/configuration match the freeze at
`57752eb`; every replication is retained. The scientific run took 109 seconds.
These are scalar statistical experiments, not additional financial markets.

At the individual 5% threshold, all-date crossings under the Gaussian alternative
are:

| Evidence rule | Crossings | Fraction | Wilson 95% interval | Mean final log capital (MC SE) |
|---|---:|---:|---:|---:|
| Linear cash-PARK | 3/4096 | 0.000732 | [0.000249, 0.002151] | 0.97564 (0.01307) |
| Catoni, geometry, fixed bet | 1/4096 | 0.000244 | [0.000043, 0.001382] | 0.77040 (0.01519) |
| Catoni, uniform bound, fixed bet | 0/4096 | 0 | [0, 0.000937] | -5322.34919 (0.00782) |
| Catoni, uniform bound, past-mean bet | 0/4096 | 0 | [0, 0.000937] | -0.001929 (0.000057) |

The difference between three and one crossing does not establish a finite-sample
power ranking. At the separately declared 1% and 0.1% thresholds, all four rules
have zero observed alternative crossings. Under the Gaussian feedback boundary
null, every rule has zero observed crossings at every declared level. This
does not establish zero type-I probability; validity follows from the stated
conditional-null arguments, not these observed fractions. Annual-review
crossings are retained separately in the numeric tables.

Under the alternative, mean integrated squared targets are 7.70966 and mean
cumulative conditional cash-PARK benefit is 3.85483 in the toy utility units
(gamma=sigma=1). These are not calibrated stock-market units, financial returns,
or expected stopped costs. The mean final evaluator log P/Q ratio is 0.97827;
the linear rule's mean absolute log discrepancy is 0.03746. The latter is a
finite-horizon diagnostic, not evidence by itself of a bounded asymptotic regret.

The [figure](vanishing_gain.png) shows the positive mean log-capital growth of
linear and geometric fixed betting, alongside the nearly flat uniform plug-in
rule. The uniform fixed-bet rule is omitted from the left panel because its
large negative value would obscure the other series; its complete results are
in the table. The 1/8 line is a slope guide, not an exact finite-horizon formula.
Left shading is +/-1.96 Monte Carlo SE for mean log capital. Right shading is
pointwise Wilson uncertainty for the crossing fractions; neither set of bands
is simultaneous across observation times. The rare crossings and overlapping
intervals matter as much as the different mean log capitals.

Independent replay uses direct multiplicative factors over short checkpoint
intervals, rather than the scientific script's log-increment arithmetic, and
separate Gaussian density calculations for P/Q. It checks a fixed eight-path
prefix per law: **39,888 scalar checkpoint values**, exact first-crossing arrays,
and source/configuration identity. Maximum absolute discrepancy is 8.37e-11,
arising on the very negative uniform fixed-bet log capital. This is explicitly
a prefix audit; it is not a replay of every simulated path. All path checkpoint
arrays and input digests are retained under `outputs/vanishing_gain_v1/`.

The proof audit establishes a sharp confidence exponent and conditional-benefit
coefficient for this particular costless estimated-policy example. It establishes
no expected rejection time, useful finite-horizon power, changing-regime result,
or improvement in the frozen full financial strategy. The main financial
minimum-effect floor is absent here. Broader prior-art review, including nested
forecast comparisons and their vanishing estimation-error effects, and manuscript
integration remain outstanding. No scientific horizon, bet, bound or seed was
retuned after observing this low crossing power.
