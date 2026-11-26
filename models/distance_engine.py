"""
Distance and Similarity Engine for Greywater Contamination Analysis (SIH26023 - Objective 2).
Provides mathematical implementations of Euclidean and Manhattan distance algorithms,
pairwise matrix calculations, nearest-neighbor similarity searches, and metric comparisons.
"""

import numpy as np
from scipy.spatial.distance import cdist
from scipy.stats import spearmanr, pearsonr

def euclidean_distance(u, v):
    """
    Computes Euclidean distance (L2 norm) between two vectors:
    d_E(u, v) = sqrt(sum((u_i - v_i)^2))
    """
    u = np.asarray(u, dtype=float)
    v = np.asarray(v, dtype=float)
    return float(np.sqrt(np.sum((u - v) ** 2)))

def manhattan_distance(u, v):
    """
    Computes Manhattan distance (L1 norm / Taxicab distance) between two vectors:
    d_M(u, v) = sum(|u_i - v_i|)
    """
    u = np.asarray(u, dtype=float)
    v = np.asarray(v, dtype=float)
    return float(np.sum(np.abs(u - v)))

def calculate_pairwise_matrices(X, sample_ids=None):
    """
    Calculates pairwise distance matrices using both Euclidean and Manhattan metrics.
    X: 2D array of shape (N, D) - typically standardized/scaled parameters.
    """
    X = np.asarray(X, dtype=float)
    N = X.shape[0]

    # Calculate distance matrices using scipy cdist for high numerical efficiency
    dist_euclidean = cdist(X, X, metric='euclidean')
    dist_manhattan = cdist(X, X, metric='cityblock')

    # Extract upper triangle without diagonal for statistical analysis
    triu_indices = np.triu_indices(N, k=1)
    euc_pairs = dist_euclidean[triu_indices]
    man_pairs = dist_manhattan[triu_indices]

    # Statistical correlation between metrics
    p_corr, _ = pearsonr(euc_pairs, man_pairs)
    s_corr, _ = spearmanr(euc_pairs, man_pairs)

    stats = {
        'total_pairs': int(len(euc_pairs)),
        'pearson_correlation': round(float(p_corr), 4),
        'spearman_rank_correlation': round(float(s_corr), 4),
        'euclidean': {
            'mean': round(float(np.mean(euc_pairs)), 3),
            'std': round(float(np.std(euc_pairs)), 3),
            'min': round(float(np.min(euc_pairs)), 3),
            'q25': round(float(np.percentile(euc_pairs, 25)), 3),
            'median': round(float(np.median(euc_pairs)), 3),
            'q75': round(float(np.percentile(euc_pairs, 75)), 3),
            'max': round(float(np.max(euc_pairs)), 3),
        },
        'manhattan': {
            'mean': round(float(np.mean(man_pairs)), 3),
            'std': round(float(np.std(man_pairs)), 3),
            'min': round(float(np.min(man_pairs)), 3),
            'q25': round(float(np.percentile(man_pairs, 25)), 3),
            'median': round(float(np.median(man_pairs)), 3),
            'q75': round(float(np.percentile(man_pairs, 75)), 3),
            'max': round(float(np.max(man_pairs)), 3),
        }
    }

    # For UI display, limit matrix size if N is very large (e.g. preview first 25 samples)
    preview_limit = min(N, 20)
    matrix_euc_preview = dist_euclidean[:preview_limit, :preview_limit].round(2).tolist()
    matrix_man_preview = dist_manhattan[:preview_limit, :preview_limit].round(2).tolist()
    
    ids_preview = list(sample_ids[:preview_limit]) if sample_ids is not None else [f"S{i+1}" for i in range(preview_limit)]

    return {
        'stats': stats,
        'preview_sample_ids': ids_preview,
        'euclidean_matrix_preview': matrix_euc_preview,
        'manhattan_matrix_preview': matrix_man_preview,
        'full_euclidean': dist_euclidean,
        'full_manhattan': dist_manhattan
    }

def find_nearest_neighbors(query_vec, X, sample_records, k=5, metric='both'):
    """
    Finds top-k nearest greywater samples to a query vector.
    query_vec: 1D array of shape (D,)
    X: 2D array of shape (N, D)
    sample_records: list of dicts with sample metadata (sample_id, source, category, etc.)
    """
    query_vec = np.asarray(query_vec, dtype=float).reshape(1, -1)
    X = np.asarray(X, dtype=float)

    results = {}

    if metric in ('euclidean', 'both'):
        dists_euc = cdist(query_vec, X, metric='euclidean')[0]
        # Top-k indices
        top_k_euc_idx = np.argsort(dists_euc)[:k]
        
        euc_list = []
        for rank, idx in enumerate(top_k_euc_idx):
            d = float(dists_euc[idx])
            sim = float(1.0 / (1.0 + d)) # normalized similarity score
            rec = sample_records[idx].copy()
            rec['distance'] = round(d, 3)
            rec['similarity_pct'] = round(sim * 100, 1)
            rec['rank'] = rank + 1
            euc_list.append(rec)
        results['euclidean'] = euc_list

    if metric in ('manhattan', 'both'):
        dists_man = cdist(query_vec, X, metric='cityblock')[0]
        top_k_man_idx = np.argsort(dists_man)[:k]
        
        man_list = []
        for rank, idx in enumerate(top_k_man_idx):
            d = float(dists_man[idx])
            sim = float(1.0 / (1.0 + d))
            rec = sample_records[idx].copy()
            rec['distance'] = round(d, 3)
            rec['similarity_pct'] = round(sim * 100, 1)
            rec['rank'] = rank + 1
            man_list.append(rec)
        results['manhattan'] = man_list

    return results

def compute_dimension_contributions(u, v, feature_names):
    """
    Breaks down how each parameter dimension contributes to Euclidean vs Manhattan distance.
    Useful for explaining WHY two samples differ.
    """
    u = np.asarray(u, dtype=float)
    v = np.asarray(v, dtype=float)
    diff = u - v

    abs_diff = np.abs(diff)
    sq_diff = diff ** 2

    total_man = np.sum(abs_diff)
    total_sq_euc = np.sum(sq_diff)
    total_euc = np.sqrt(total_sq_euc)

    breakdown = []
    for i, col in enumerate(feature_names):
        man_pct = (abs_diff[i] / total_man * 100) if total_man > 0 else 0
        euc_sq_pct = (sq_diff[i] / total_sq_euc * 100) if total_sq_euc > 0 else 0

        breakdown.append({
            'parameter': col,
            'u_val': round(float(u[i]), 2),
            'v_val': round(float(v[i]), 2),
            'delta': round(float(diff[i]), 2),
            'abs_diff': round(float(abs_diff[i]), 3),
            'manhattan_contrib_pct': round(float(man_pct), 1),
            'sq_diff': round(float(sq_diff[i]), 3),
            'euclidean_sq_contrib_pct': round(float(euc_sq_pct), 1)
        })

    return {
        'total_euclidean': round(float(total_euc), 3),
        'total_manhattan': round(float(total_man), 3),
        'breakdown': breakdown
    }
