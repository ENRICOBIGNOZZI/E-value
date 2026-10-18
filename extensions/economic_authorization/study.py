"""Controlled financial simulation of provisional economic authorization.

Kept outside src/ and research/ to preserve the running original study's
scientific fingerprint. All learners see observed returns and public design;
truth is read only after the current actions and evidence stakes are fixed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'research')]
import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from threadpoolctl import threadpool_limits
from park_revive.config import Config
from park_revive_extensions.certificates import PublicRisk, forward_score_caps
from park_revive_extensions.tail_betting import TailMixture
from park_revive_full.engine import source_fingerprint
from park_revive_full.market import CausalMarket

ARMS = ('Wait', 'EconomicQuarter', 'Hybrid', 'EconomicFull')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def training_fit(history, cfg, settings):
    x = np.asarray(history, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    n = len(x)
    if n < 2 or not np.isfinite(x).all():
        raise ValueError('Finite past training returns required')
    mean = x.mean(axis=0)
    second = np.mean(x * x, axis=0) + cfg.ridge
    centered = x - mean
    bandwidth = min(settings['hac_bandwidth'], n - 1)
    long_variance = np.mean(centered * centered, axis=0)
    for lag in range(1, bandwidth + 1):
        long_variance += 2 * (1 - lag / (bandwidth + 1)) * np.sum(
            centered[lag:] * centered[:-lag], axis=0) / n
    se = np.sqrt(np.maximum(long_variance, 0) / n)
    adjusted = np.maximum(np.abs(mean) - settings['uncertainty_z'] * se, 0)
    h = settings['forecast_holding_days']
    w = np.sign(mean) * np.maximum(adjusted - cfg.proportional / h, 0) / (
        cfg.gamma * second + cfg.impact / h)
    return mean, second, se, np.clip(w, -cfg.leverage, cfg.leverage)


def cost(w, previous, cfg):
    d = np.asarray(w) - np.asarray(previous)
    return cfg.proportional * np.abs(d) + cfg.impact * d * d / 2


def forecast(w, previous, mean, second, se, cfg, settings):
    return settings['forecast_holding_days'] * (
        w * mean - settings['uncertainty_z'] * np.abs(w) * se
        - cfg.gamma * w * w * second / 2) - cost(w, previous, cfg)


def review(mean, second, se, w, previous_hybrid, log_e, mean_score,
           already_full, cfg, settings):
    floor = settings['forecast_holding_days'] * settings['effect_floor_daily']
    q = settings['provisional_fraction']
    provisional = q if forecast(q*w, 0., mean, second, se, cfg, settings) > floor else 0.
    full_forecast = forecast(w, 0., mean, second, se, cfg, settings)
    increase_forecast = (
        forecast(w, previous_hybrid, mean, second, se, cfg, settings)
        - forecast(provisional*w, previous_hybrid, mean, second, se, cfg, settings))
    evidence = log_e >= np.log(1 / settings['individual_alpha'])
    full = already_full or bool(evidence and mean_score > settings['effect_floor_daily']
                               and full_forecast > floor and increase_forecast > floor)
    fractions = np.array([float(full), provisional,
                          1. if full else provisional, float(full_forecast > floor)])
    return fractions, full, dict(provisional_fraction=provisional,
                                increase_forecast=float(increase_forecast),
                                full_forecast=float(full_forecast), evidence=bool(evidence))


def realize(weights, previous, returns, alive, wealth, cfg):
    weights = np.where(alive, weights, 0.)
    costs = np.where(alive, cost(weights, previous, cfg), 0.)
    gross = weights * returns
    utility = np.where(alive, gross - cfg.gamma * gross * gross / 2 - costs, 0.)
    net = gross - costs
    new_wealth = np.where(alive, wealth * np.maximum(1 + net, 0), 0.)
    new_alive = alive & (net > -1)
    previous = np.where(new_alive, weights, 0.)
    return weights, previous, new_alive, new_wealth, costs, gross, utility


def freeze(settings_path, output):
    settings = json.loads(settings_path.read_text())
    cfg = Config.read(ROOT / settings['base_config'])
    if not 0 < settings['provisional_fraction'] < 1:
        raise ValueError('Provisional fraction must be strictly between zero and one')
    if settings['seeds'] != dict(first=70001, count=100):
        raise ValueError('The declared study retains exactly seeds 70001--70100')
    if settings['individual_alpha'] != cfg.alpha:
        raise ValueError('Use the shared declared individual testing level')
    original_hash, files = source_fingerprint()
    value = dict(settings=settings, base_config=cfg.to_dict(),
                 original_scientific_source_hash=original_hash,
                 original_scientific_manifest=files,
                 extension_source_sha256=sha(__file__),
                 settings_sha256=sha(settings_path),
                 disclosure='Designed after the earlier pilot and user discussion; no prior new-study outcomes examined.',
                 methods=list(ARMS), seed_pool=list(range(70001, 70101)))
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'protocol_frozen.json'
    if path.exists():
        if json.loads(path.read_text()) != json.loads(json.dumps(value)):
            raise ValueError('Frozen protocol differs; use a new version')
    else:
        write_json(path, value)
    return cfg, settings, value, sha(path)


def run_seed(cfg, settings, protocol, protocol_hash, seed, directory,
             market_factory=CausalMarket):
    directory.mkdir(parents=True, exist_ok=True)
    status_path = directory / 'status.json'
    if status_path.exists():
        status = json.loads(status_path.read_text())
        if (status.get('seed') != seed or status.get('complete') is not True or status.get('protocol_sha256') != protocol_hash
                or any(sha(directory / name) != digest for name, digest in status['files'].items())):
            raise ValueError(f'Incomplete, altered or stale seed: {seed}')
        return
    if any(directory.iterdir()):
        raise ValueError(f'Unsealed output exists for seed {seed}; inspect before retrying')
    started = time.perf_counter()
    market = market_factory(cfg, seed)
    initial = np.array([market.step()[0].returns for _ in range(cfg.block)])
    mean, second, se, candidates = training_fit(initial, cfg, settings)
    values = forecast(candidates, 0., mean, second, se, cfg, settings)
    selected = int(np.argmax(values))  # stable library order resolves exact ties
    history = list(initial[:, selected])
    risk = PublicRisk.from_market_contract(cfg)
    evidence = TailMixture(1)
    previous = np.zeros(len(ARMS))
    alive = np.ones(len(ARMS), dtype=bool)
    wealth = np.ones(len(ARMS))
    previous_shadow = 0.
    full = False
    deployment_day = -1
    first_cross_review = -1
    score_sum = 0.
    score_count = 0
    rows = {key: [] for key in ['returns','shadow_weight','shadow_cost','cap2','cap4',
                               'log_e','true_mean','true_second','arm_weight','arm_cost',
                               'arm_utility','arm_wealth']}
    annual = []
    for year in range(cfg.years - 1):
        mu, m2, uncertainty, target = training_fit(history, cfg, settings)
        mu, m2, uncertainty, target = map(float, (mu[0], m2[0], uncertainty[0], target[0]))
        fractions, full, decision = review(
            mu, m2, uncertainty, target, previous[2], float(evidence.log_e[0]),
            score_sum / score_count if score_count else 0., full, cfg, settings)
        if full and deployment_day < 0:
            deployment_day = year * cfg.block
        annual.append(dict(year=year, training_n=len(history), mean=mu, second=m2,
                           standard_error=uncertainty, target=target,
                           evidence_log_e=float(evidence.log_e[0]),
                           mean_score=score_sum/score_count if score_count else 0.,
                           previous_hybrid=float(previous[2]), full_authorized=full, **decision))
        for offset in range(cfg.block):
            design, _ = market.prepare()
            shadow_cost = float(cost(target, previous_shadow, cfg))
            cap2, cap4 = forward_score_caps(
                np.array([target]), np.array([previous_shadow]), design.values,
                design.sleeves[:, [selected]], cfg, risk)
            prepared = evidence.prepare(cap2, cap4)
            actions = fractions * target
            obs, truth = market.step()
            r = float(obs.returns[selected])
            actual, previous, alive, wealth, costs, gross, utilities = realize(
                actions, previous, r, alive, wealth, cfg)
            y = target*r - cfg.gamma*(target*r)**2/2 - shadow_cost
            evidence.update([y], prepared)
            score_sum += y
            score_count += 1
            previous_shadow = target
            history.append(r)
            for key, value in dict(
                returns=r, shadow_weight=target, shadow_cost=shadow_cost,
                cap2=float(cap2[0]), cap4=float(cap4[0]), log_e=float(evidence.log_e[0]),
                true_mean=float(truth.mean[selected]), true_second=float(truth.second[selected, selected]),
                arm_weight=actual.copy(), arm_cost=costs.copy(),
                arm_utility=utilities.copy(), arm_wealth=wealth.copy()).items():
                rows[key].append(value)
        if first_cross_review < 0 and evidence.log_e[0] >= np.log(1/settings['individual_alpha']):
            first_cross_review = (year + 1) * cfg.block
        if sha(__file__) != protocol['extension_source_sha256']:
            raise RuntimeError('Extension source changed while running')
        print(f'economic seed={seed} block={year+1}/{cfg.years-1}', flush=True)
    arrays = {key: np.asarray(value) for key, value in rows.items()}
    if (sha(__file__) != protocol['extension_source_sha256']
            or source_fingerprint()[0] != protocol['original_scientific_source_hash']):
        raise RuntimeError('Scientific implementation changed before seed completion')
    arrays['initial_training'] = initial
    arrays['selected'] = np.array(selected)
    temporary = directory / 'ledger.partial.npz'
    np.savez_compressed(temporary, **arrays)
    temporary.replace(directory / 'ledger.npz')
    write_json(directory / 'annual_decisions.json', annual)
    h = len(arrays['returns'])
    before = deployment_day if deployment_day >= 0 else h
    summary = []
    for a, name in enumerate(ARMS):
        utility = arrays['arm_utility'][:, a]
        w = arrays['arm_weight'][:, a]
        costs = arrays['arm_cost'][:, a]
        expected = w*arrays['true_mean'] - cfg.gamma*w*w*arrays['true_second']/2 - costs
        wealth_path = np.r_[1., arrays['arm_wealth'][:, a]]
        summary.append(dict(
            seed=seed, method=name, signal=market.ids[selected], selected_index=selected,
            annual_scaled_utility=float(cfg.block*utility.mean()),
            terminal_wealth=float(wealth_path[-1]),
            maximum_drawdown=float(np.max(1-wealth_path/np.maximum.accumulate(wealth_path))),
            annual_scaled_cost=float(cfg.block*costs.mean()),
            cash_fraction=float(np.mean(w == 0)), insolvent=bool(wealth_path[-1] == 0),
            deployment_day=deployment_day, first_cross_review=first_cross_review,
            pre_deployment_utility=float(utility[:before].sum()),
            pre_deployment_expected_utility=float(expected[:before].sum()),
            pre_deployment_negative_days=int(np.sum(utility[:before] < 0)),
            pre_deployment_negative_conditional_days=int(np.sum(expected[:before] < 0)),
            elapsed_seconds=time.perf_counter()-started))
    pd.DataFrame(summary).to_csv(directory / 'summary.csv', index=False)
    files = {name: sha(directory / name) for name in ['ledger.npz','annual_decisions.json','summary.csv']}
    write_json(status_path, dict(seed=seed, complete=True, protocol_sha256=protocol_hash, files=files))
    print(f'economic seed={seed} COMPLETE seconds={time.perf_counter()-started:.2f}', flush=True)


def report(output, destination, cfg, settings, protocol_hash):
    seeds = list(range(70001,70101))
    for seed in seeds:
        directory = output / f'seed_{seed}'
        status = json.loads((directory/'status.json').read_text())
        if (not status['complete'] or status['protocol_sha256'] != protocol_hash
                or any(sha(directory/name) != digest for name,digest in status['files'].items())):
            raise ValueError(f'Unverified membership or artifact: {seed}')
    data = pd.concat([pd.read_csv(output/f'seed_{s}'/'summary.csv') for s in seeds], ignore_index=True)
    if len(data)!=400 or set(data.method)!=set(ARMS):
        raise ValueError('Exactly 100 markets and four methods required')
    destination.mkdir(parents=True, exist_ok=True)
    data.to_csv(destination/'per_market.csv',index=False)
    means = data.groupby('method').agg(
        mean_utility=('annual_scaled_utility','mean'), se_utility=('annual_scaled_utility','sem'),
        mean_wealth=('terminal_wealth','mean'), mean_drawdown=('maximum_drawdown','mean'),
        mean_cost=('annual_scaled_cost','mean'), mean_cash_fraction=('cash_fraction','mean'),
        insolvencies=('insolvent','sum'))
    means.to_csv(destination/'methods.csv')
    contrasts=[]
    wide=data.pivot(index='seed',columns='method',values='annual_scaled_utility').loc[seeds]
    for other in ['Wait','EconomicQuarter','EconomicFull']:
        d=wide.Hybrid-wide[other]; se=float(d.std(ddof=1)/np.sqrt(len(d)))
        radius=float(student_t.ppf(.975,len(d)-1)*se)
        contrasts.append(dict(contrast=f'Hybrid minus {other}',primary=other=='Wait',
                              n=len(d),mean=float(d.mean()),standard_error=se,
                              lower=float(d.mean()-radius),upper=float(d.mean()+radius)))
    pd.DataFrame(contrasts).to_csv(destination/'paired_contrasts.csv',index=False)
    write_json(destination/'status.json',dict(
        complete=True, seed_pool=seeds, protocol_sha256=protocol_hash,
        scope=settings['scope'], analysis=settings['analysis'],
        independent_replay_pending=True, no_empirical_data=True))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--settings',type=Path,default=ROOT/'configs/economic_authorization.json')
    p.add_argument('--output',type=Path,default=ROOT/'outputs/economic_authorization_v1')
    p.add_argument('--destination',type=Path,default=ROOT/'reports/economic_authorization_v1')
    args=p.parse_args()
    cfg,settings,protocol,protocol_hash=freeze(args.settings,args.output)
    with threadpool_limits(limits=1):
        for seed in protocol['seed_pool']:
            if source_fingerprint()[0] != protocol['original_scientific_source_hash']:
                raise RuntimeError('Original scientific source changed after extension freeze')
            run_seed(cfg,settings,protocol,protocol_hash,seed,args.output/f'seed_{seed}')
    report(args.output,args.destination,cfg,settings,protocol_hash)


if __name__ == '__main__':
    main()
