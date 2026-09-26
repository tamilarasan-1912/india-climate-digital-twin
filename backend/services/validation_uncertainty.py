"""Validation and Uncertainty Quantification for Bharat Climate Twin.

Provides:
- Hydrological model validation metrics (NSE, KGE, RMSE, PBIAS)
- Parameter uncertainty via ensemble methods
- Forecast verification (reliability, sharpness)
- Cross-validation utilities
- Model performance tracking
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

import numpy as np


def nash_sutcliffe_efficiency(observed: np.ndarray, simulated: np.ndarray) -> float:
    """Nash-Sutcliffe Efficiency (NSE).
    
    NSE = 1 - sum((obs - sim)^2) / sum((obs - mean(obs))^2)
    Range: -inf to 1.0 (1.0 = perfect match)
    """
    obs = np.asarray(observed, dtype=float)
    sim = np.asarray(simulated, dtype=float)
    
    mask = np.isfinite(obs) & np.isfinite(sim)
    if not np.any(mask):
        return np.nan
    
    obs = obs[mask]
    sim = sim[mask]
    
    if len(obs) < 2:
        return np.nan
    
    mean_obs = np.mean(obs)
    numerator = np.sum((obs - sim) ** 2)
    denominator = np.sum((obs - mean_obs) ** 2)
    
    if denominator == 0:
        return 1.0 if numerator == 0 else -np.inf
    
    return 1.0 - numerator / denominator


def kge(observed: np.ndarray, simulated: np.ndarray) -> float:
    """Kling-Gupta Efficiency (KGE).
    
    KGE = 1 - sqrt((r-1)^2 + (beta-1)^2 + (gamma-1)^2)
    where:
    r = correlation coefficient
    beta = mean(sim) / mean(obs) (bias ratio)
    gamma = (std(sim)/mean(sim)) / (std(obs)/mean(obs)) (variability ratio)
    Range: -inf to 1.0 (1.0 = perfect match)
    """
    obs = np.asarray(observed, dtype=float)
    sim = np.asarray(simulated, dtype=float)
    
    mask = np.isfinite(obs) & np.isfinite(sim)
    if not np.any(mask):
        return np.nan
    
    obs = obs[mask]
    sim = sim[mask]
    
    if len(obs) < 2:
        return np.nan
    
    r = np.corrcoef(obs, sim)[0, 1]
    if np.isnan(r):
        return np.nan
    
    mean_obs = np.mean(obs)
    mean_sim = np.mean(sim)
    beta = mean_sim / mean_obs if mean_obs != 0 else np.nan
    
    std_obs = np.std(obs, ddof=1)
    std_sim = np.std(sim, ddof=1)
    cv_obs = std_obs / mean_obs if mean_obs != 0 else np.nan
    cv_sim = std_sim / mean_sim if mean_sim != 0 else np.nan
    gamma = cv_sim / cv_obs if cv_obs != 0 and not np.isnan(cv_obs) else np.nan
    
    if np.isnan(beta) or np.isnan(gamma):
        return np.nan
    
    return 1.0 - math.sqrt((r - 1)**2 + (beta - 1)**2 + (gamma - 1)**2)


def rmse(observed: np.ndarray, simulated: np.ndarray) -> float:
    """Root Mean Square Error."""
    obs = np.asarray(observed, dtype=float)
    sim = np.asarray(simulated, dtype=float)
    
    mask = np.isfinite(obs) & np.isfinite(sim)
    if not np.any(mask):
        return np.nan
    
    obs = obs[mask]
    sim = sim[mask]
    
    return float(np.sqrt(np.mean((obs - sim) ** 2)))


def mae(observed: np.ndarray, simulated: np.ndarray) -> float:
    """Mean Absolute Error."""
    obs = np.asarray(observed, dtype=float)
    sim = np.asarray(simulated, dtype=float)
    
    mask = np.isfinite(obs) & np.isfinite(sim)
    if not np.any(mask):
        return np.nan
    
    obs = obs[mask]
    sim = sim[mask]
    
    return float(np.mean(np.abs(obs - sim)))


def pbias(observed: np.ndarray, simulated: np.ndarray) -> float:
    """Percent Bias (PBIAS).
    
    PBIAS = 100 * sum(sim - obs) / sum(obs)
    Positive = overestimation, Negative = underestimation
    """
    obs = np.asarray(observed, dtype=float)
    sim = np.asarray(simulated, dtype=float)
    
    mask = np.isfinite(obs) & np.isfinite(sim)
    if not np.any(mask):
        return np.nan
    
    obs = obs[mask]
    sim = sim[mask]
    
    sum_obs = np.sum(obs)
    if sum_obs == 0:
        return np.nan
    
    return 100.0 * np.sum(sim - obs) / sum_obs


def rsr(observed: np.ndarray, simulated: np.ndarray) -> float:
    """RMSE-observations Standard Deviation Ratio (RSR).
    
    RSR = RMSE / std(obs)
    Range: 0 to +inf (0 = perfect)
    """
    obs = np.asarray(observed, dtype=float)
    sim = np.asarray(simulated, dtype=float)
    
    mask = np.isfinite(obs) & np.isfinite(sim)
    if not np.any(mask):
        return np.nan
    
    obs = obs[mask]
    sim = sim[mask]
    
    std_obs = np.std(obs, ddof=1)
    if std_obs == 0:
        return np.nan
    
    return rmse(obs, sim) / std_obs


def log_nse(observed: np.ndarray, simulated: np.ndarray) -> float:
    """Log-transformed NSE (better for low flows)."""
    obs = np.asarray(observed, dtype=float)
    sim = np.asarray(simulated, dtype=float)
    
    mask = (obs > 0) & (sim > 0) & np.isfinite(obs) & np.isfinite(sim)
    if not np.any(mask):
        return np.nan
    
    return nash_sutcliffe_efficiency(np.log(obs[mask]), np.log(sim[mask]))


def correlation_coefficient(observed: np.ndarray, simulated: np.ndarray) -> float:
    """Pearson correlation coefficient."""
    obs = np.asarray(observed, dtype=float)
    sim = np.asarray(simulated, dtype=float)
    
    mask = np.isfinite(obs) & np.isfinite(sim)
    if not np.any(mask) or np.sum(mask) < 2:
        return np.nan
    
    return float(np.corrcoef(obs[mask], sim[mask])[0, 1])


def volume_error(observed: np.ndarray, simulated: np.ndarray) -> float:
    """Total volume error as percentage."""
    obs = np.asarray(observed, dtype=float)
    sim = np.asarray(simulated, dtype=float)
    
    mask = np.isfinite(obs) & np.isfinite(sim)
    if not np.any(mask):
        return np.nan
    
    obs = obs[mask]
    sim = sim[mask]
    
    return 100.0 * (np.sum(sim) - np.sum(obs)) / np.sum(obs) if np.sum(obs) != 0 else np.nan


def peak_flow_error(observed: np.ndarray, simulated: np.ndarray) -> dict[str, float]:
    """Peak flow timing and magnitude errors."""
    obs = np.asarray(observed, dtype=float)
    sim = np.asarray(simulated, dtype=float)
    
    mask = np.isfinite(obs) & np.isfinite(sim)
    if not np.any(mask):
        return {"magnitude_error_pct": np.nan, "timing_error_days": np.nan}
    
    obs = obs[mask]
    sim = sim[mask]
    
    peak_obs_idx = np.argmax(obs)
    peak_sim_idx = np.argmax(sim)
    peak_obs_val = obs[peak_obs_idx]
    peak_sim_val = sim[peak_sim_idx]
    
    mag_error = 100.0 * (peak_sim_val - peak_obs_val) / peak_obs_val if peak_obs_val != 0 else np.nan
    timing_error = float(peak_sim_idx - peak_obs_idx)
    
    return {
        "magnitude_error_pct": mag_error,
        "timing_error_days": timing_error,
        "peak_observed": peak_obs_val,
        "peak_simulated": peak_sim_val,
    }


def low_flow_error(observed: np.ndarray, simulated: np.ndarray, percentile: float = 10.0) -> float:
    """Low flow error (percentile-based)."""
    obs = np.asarray(observed, dtype=float)
    sim = np.asarray(simulated, dtype=float)
    
    mask = np.isfinite(obs) & np.isfinite(sim)
    if not np.any(mask):
        return np.nan
    
    obs = obs[mask]
    sim = sim[mask]
    
    q_obs = np.percentile(obs, percentile)
    q_sim = np.percentile(sim, percentile)
    
    return 100.0 * (q_sim - q_obs) / q_obs if q_obs != 0 else np.nan


def high_flow_error(observed: np.ndarray, simulated: np.ndarray, percentile: float = 90.0) -> float:
    """High flow error (percentile-based)."""
    obs = np.asarray(observed, dtype=float)
    sim = np.asarray(simulated, dtype=float)
    
    mask = np.isfinite(obs) & np.isfinite(sim)
    if not np.any(mask):
        return np.nan
    
    obs = obs[mask]
    sim = sim[mask]
    
    q_obs = np.percentile(obs, percentile)
    q_sim = np.percentile(sim, percentile)
    
    return 100.0 * (q_sim - q_obs) / q_obs if q_obs != 0 else np.nan


def compute_all_metrics(observed: np.ndarray, simulated: np.ndarray) -> dict[str, Any]:
    """Compute all standard hydrological validation metrics."""
    return {
        "nse": nash_sutcliffe_efficiency(observed, simulated),
        "kge": kge(observed, simulated),
        "rmse": rmse(observed, simulated),
        "mae": mae(observed, simulated),
        "pbias": pbias(observed, simulated),
        "rsr": rsr(observed, simulated),
        "log_nse": log_nse(observed, simulated),
        "correlation": correlation_coefficient(observed, simulated),
        "volume_error_pct": volume_error(observed, simulated),
        "peak_flow": peak_flow_error(observed, simulated),
        "low_flow_error_pct": low_flow_error(observed, simulated),
        "high_flow_error_pct": high_flow_error(observed, simulated),
        "n_observations": int(np.sum(np.isfinite(observed) & np.isfinite(simulated))),
    }


def parameter_ensemble(
    param_ranges: dict[str, tuple[float, float]],
    n_samples: int = 100,
    method: str = "lhs",
) -> list[dict[str, float]]:
    """Generate parameter ensemble using Latin Hypercube Sampling or random.
    
    Args:
        param_ranges: Dict of {param_name: (min, max)}
        n_samples: Number of parameter sets
        method: "lhs" for Latin Hypercube, "random" for uniform random
    
    Returns:
        List of parameter dictionaries
    """
    from scipy.stats import qmc
    
    param_names = list(param_ranges.keys())
    bounds = np.array([param_ranges[name] for name in param_names])
    
    if method == "lhs":
        sampler = qmc.LatinHypercube(d=len(param_names), seed=42)
        samples = sampler.random(n=n_samples)
        samples = qmc.scale(samples, bounds[:, 0], bounds[:, 1])
    else:
        samples = np.random.uniform(bounds[:, 0], bounds[:, 1], size=(n_samples, len(param_names)))
    
    return [
        {name: float(samples[i, j]) for j, name in enumerate(param_names)}
        for i in range(n_samples)
    ]


def run_parameter_uncertainty(
    model_func,
    param_ranges: dict[str, tuple[float, float]],
    observed: np.ndarray,
    n_samples: int = 100,
    **model_kwargs,
) -> dict[str, Any]:
    """Run model with parameter ensemble and compute uncertainty bounds.
    
    Args:
        model_func: Function that takes (params, **kwargs) and returns simulated
        param_ranges: Parameter ranges for sampling
        observed: Observed time series
        n_samples: Number of ensemble members
        **model_kwargs: Additional arguments passed to model_func
    
    Returns:
        Dictionary with ensemble statistics and uncertainty bounds
    """
    ensemble_params = parameter_ensemble(param_ranges, n_samples)
    
    simulations = []
    metrics_list = []
    
    for params in ensemble_params:
        try:
            sim = model_func(params, **model_kwargs)
            sim = np.asarray(sim, dtype=float)
            if sim.shape == observed.shape:
                simulations.append(sim)
                metrics = compute_all_metrics(observed, sim)
                metrics_list.append(metrics)
        except Exception:
            continue
    
    if not simulations:
        return {"error": "No successful simulations"}
    
    simulations = np.array(simulations)  # (n_sims, n_timesteps)
    
    # Ensemble statistics
    ensemble_mean = np.nanmean(simulations, axis=0)
    ensemble_std = np.nanstd(simulations, axis=0)
    ensemble_5 = np.nanpercentile(simulations, 5, axis=0)
    ensemble_95 = np.nanpercentile(simulations, 95, axis=0)
    ensemble_25 = np.nanpercentile(simulations, 25, axis=0)
    ensemble_75 = np.nanpercentile(simulations, 75, axis=0)
    
    # Metric statistics
    metric_names = [
        "nse", "kge", "rmse", "mae", "pbias", "rsr", "log_nse",
        "correlation", "volume_error_pct", "low_flow_error_pct", "high_flow_error_pct"
    ]
    metric_stats = {}
    for metric_name in metric_names:
        vals = [metric_dict[metric_name] for metric_dict in metrics_list 
                if metric_name in metric_dict and not np.isnan(metric_dict[metric_name])]
        if vals:
            metric_stats[metric_name] = {
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals)),
                "min": float(np.min(vals)),
                "max": float(np.max(vals)),
                "median": float(np.median(vals)),
            }
    
    return {
        "n_successful": len(simulations),
        "n_failed": n_samples - len(simulations),
        "ensemble_mean": ensemble_mean.tolist(),
        "ensemble_std": ensemble_std.tolist(),
        "ensemble_5th": ensemble_5.tolist(),
        "ensemble_95th": ensemble_95.tolist(),
        "ensemble_25th": ensemble_25.tolist(),
        "ensemble_75th": ensemble_75.tolist(),
        "metric_statistics": metric_stats,
        "coverage_90": {
            "lower": ensemble_5.tolist(),
            "upper": ensemble_95.tolist(),
        },
        "coverage_50": {
            "lower": ensemble_25.tolist(),
            "upper": ensemble_75.tolist(),
        },
        "scientific_status": "parameter_uncertainty_quantified",
    }


def cross_validate(
    model_func,
    param_ranges: dict[str, tuple[float, float]],
    observed: np.ndarray,
    n_folds: int = 5,
    n_samples_per_fold: int = 50,
    **model_kwargs,
) -> dict[str, Any]:
    """Cross-validation for hydrological model.
    
    Args:
        model_func: Function that takes (params, **kwargs) and returns simulated
        param_ranges: Parameter ranges for sampling
        observed: Observed time series
        n_folds: Number of CV folds (time series split)
        n_samples_per_fold: Parameter samples per fold
        **model_kwargs: Additional arguments to model_func
    
    Returns:
        Cross-validation results
    """
    n = len(observed)
    fold_size = n // n_folds
    
    fold_results = []
    
    for fold in range(n_folds):
        # Time series split: train on first part, test on next
        train_end = fold * fold_size + fold_size
        test_start = train_end
        test_end = min(test_start + fold_size, n)
        
        if test_start >= n or test_end > n:
            break
        
        train_obs = observed[:train_end]
        test_obs = observed[test_start:test_end]
        
        # Calibrate on training period (simplified: just use best params from ensemble)
        # In practice, would run optimization here
        ensemble_params = parameter_ensemble(param_ranges, n_samples_per_fold)
        
        best_nse = -np.inf
        best_params = None
        
        for params in ensemble_params:
            try:
                sim = model_func(params, **model_kwargs)
                sim = np.asarray(sim, dtype=float)
                if len(sim) >= train_end:
                    train_sim = sim[:train_end]
                    nse = nash_sutcliffe_efficiency(train_obs, train_sim)
                    if nse > best_nse:
                        best_nse = nse
                        best_params = params
            except Exception:
                continue
        
        if best_params is not None:
            # Test on validation period
            try:
                test_sim = model_func(best_params, **model_kwargs)
                test_sim = np.asarray(test_sim, dtype=float)
                if len(test_sim) >= test_end:
                    test_sim_period = test_sim[test_start:test_end]
                    metrics = compute_all_metrics(test_obs, test_sim_period)
                    fold_results.append({
                        "fold": fold,
                        "train_period": f"0-{train_end}",
                        "test_period": f"{test_start}-{test_end}",
                        "best_train_nse": best_nse,
                        "test_metrics": metrics,
                        "best_params": best_params,
                    })
            except Exception:
                pass
    
    # Aggregate results
    if fold_results:
        test_nse_vals = [f["test_metrics"]["nse"] for f in fold_results if not np.isnan(f["test_metrics"]["nse"])]
        test_kge_vals = [f["test_metrics"]["kge"] for f in fold_results if not np.isnan(f["test_metrics"]["kge"])]
        
        return {
            "n_folds": len(fold_results),
            "fold_results": fold_results,
            "aggregate": {
                "mean_test_nse": float(np.mean(test_nse_vals)) if test_nse_vals else np.nan,
                "std_test_nse": float(np.std(test_nse_vals)) if test_nse_vals else np.nan,
                "mean_test_kge": float(np.mean(test_kge_vals)) if test_kge_vals else np.nan,
                "std_test_kge": float(np.std(test_kge_vals)) if test_kge_vals else np.nan,
            },
            "scientific_status": "cross_validated",
        }
    else:
        return {"error": "No successful folds", "scientific_status": "failed"}


def forecast_verification(
    forecasts: np.ndarray,
    observations: np.ndarray,
    bins: int = 10,
) -> dict[str, Any]:
    """Forecast verification metrics for probabilistic forecasts.
    
    Args:
        forecasts: Forecast values (can be ensemble mean or deterministic)
        observations: Observed values
        bins: Number of bins for reliability diagram
    
    Returns:
        Verification metrics
    """
    f = np.asarray(forecasts, dtype=float)
    o = np.asarray(observations, dtype=float)
    
    mask = np.isfinite(f) & np.isfinite(o)
    if not np.any(mask):
        return {"error": "No valid data"}
    
    f = f[mask]
    o = o[mask]
    
    # Deterministic metrics
    det_metrics = compute_all_metrics(o, f)
    
    # For ensemble forecasts, add reliability
    # (simplified - assumes f is ensemble mean)
    
    return {
        "deterministic": det_metrics,
        "reliability": "not_computed_requires_ensemble",
        "sharpness": "not_computed_requires_ensemble",
        "roc_auc": "not_computed_requires_binary_events",
        "scientific_status": "forecast_verification_basic",
    }


if __name__ == "__main__":
    # Quick test
    obs = np.array([10, 15, 20, 25, 30, 20, 15, 10, 5, 3])
    sim = np.array([11, 14, 22, 24, 28, 19, 16, 9, 6, 2])
    
    metrics = compute_all_metrics(obs, sim)
    print("Validation Metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")