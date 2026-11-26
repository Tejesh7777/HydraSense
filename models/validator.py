"""
Laboratory Validation Engine for Greywater Contamination Analysis (SIH26023 - Objective 3).
Validates clustering outputs against laboratory-confirmed treatment-suitability ground truth categories
using optimal Hungarian bipartite matching, confusion matrices, accuracy, precision, recall, and F1-score.
"""

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import (
    confusion_matrix,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score
)

# Standard laboratory ground truth order
ORDERED_CATEGORIES = [
    'Low Contamination',
    'Medium Contamination',
    'High Contamination',
    'Severe Contamination'
]

class LaboratoryValidator:
    def __init__(self, ground_truth_series):
        """
        ground_truth_series: pandas Series or list containing laboratory ground truth labels.
        """
        self.y_true = np.asarray(ground_truth_series, dtype=str)
        # Determine available unique categories
        self.classes = [c for c in ORDERED_CATEGORIES if c in np.unique(self.y_true)]
        if not self.classes:
            self.classes = sorted(list(np.unique(self.y_true)))

    def align_clusters_to_ground_truth(self, cluster_labels):
        """
        Uses Hungarian Algorithm (Kuhn-Munkres) via scipy.optimize.linear_sum_assignment
        to find the optimal bijective mapping from cluster IDs to laboratory ground truth categories.
        """
        cluster_labels = np.asarray(cluster_labels)
        unique_clusters = np.unique(cluster_labels)
        n_clusters = len(unique_clusters)
        n_classes = len(self.classes)

        # Build cost / contingency matrix (rows: clusters, cols: ground truth classes)
        # Shape: (n_clusters, n_classes)
        cost_matrix = np.zeros((n_clusters, n_classes), dtype=int)
        for i, cid in enumerate(unique_clusters):
            mask = (cluster_labels == cid)
            for j, cls in enumerate(self.classes):
                cost_matrix[i, j] = np.sum(self.y_true[mask] == cls)

        # Maximize overlap <=> minimize -cost_matrix
        row_ind, col_ind = linear_sum_assignment(-cost_matrix)

        mapping = {}
        for r, c in zip(row_ind, col_ind):
            cluster_id = unique_clusters[r]
            assigned_class = self.classes[c]
            mapping[int(cluster_id)] = assigned_class

        # Map predictions
        mapped_predictions = np.array([mapping.get(int(cid), 'Unknown') for cid in cluster_labels])
        return mapped_predictions, mapping, cost_matrix

    def validate(self, cluster_labels, algorithm_name='Clustering Algorithm'):
        """
        Computes real, scientifically rigorous validation metrics against laboratory ground truth.
        """
        mapped_preds, mapping, contingency = self.align_clusters_to_ground_truth(cluster_labels)

        # Filter out any unmapped or missing entries
        valid_mask = np.isin(mapped_preds, self.classes) & np.isin(self.y_true, self.classes)
        y_t = self.y_true[valid_mask]
        y_p = mapped_preds[valid_mask]

        acc = accuracy_score(y_t, y_p)
        prec_macro = precision_score(y_t, y_p, labels=self.classes, average='macro', zero_division=0)
        rec_macro = recall_score(y_t, y_p, labels=self.classes, average='macro', zero_division=0)
        f1_macro = f1_score(y_t, y_p, labels=self.classes, average='macro', zero_division=0)

        prec_weighted = precision_score(y_t, y_p, labels=self.classes, average='weighted', zero_division=0)
        rec_weighted = recall_score(y_t, y_p, labels=self.classes, average='weighted', zero_division=0)
        f1_weighted = f1_score(y_t, y_p, labels=self.classes, average='weighted', zero_division=0)

        # Confusion Matrix
        cm = confusion_matrix(y_t, y_p, labels=self.classes)

        # Per-class breakdown
        class_metrics = []
        for i, cls in enumerate(self.classes):
            tp = int(cm[i, i])
            fn = int(np.sum(cm[i, :]) - tp)
            fp = int(np.sum(cm[:, i]) - tp)
            tn = int(len(y_t) - (tp + fn + fp))
            
            p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f = 2 * (p * r) / (p + r) if (p + r) > 0 else 0.0
            support = int(np.sum(cm[i, :]))

            class_metrics.append({
                'category': cls,
                'true_positives': tp,
                'false_positives': fp,
                'false_negatives': fn,
                'true_negatives': tn,
                'precision': round(float(p), 4),
                'recall': round(float(r), 4),
                'f1_score': round(float(f), 4),
                'support': support
            })

        return {
            'algorithm_name': algorithm_name,
            'mapping': mapping,
            'classes': self.classes,
            'overall': {
                'accuracy': round(float(acc), 4),
                'precision_macro': round(float(prec_macro), 4),
                'recall_macro': round(float(rec_macro), 4),
                'f1_macro': round(float(f1_macro), 4),
                'precision_weighted': round(float(prec_weighted), 4),
                'recall_weighted': round(float(rec_weighted), 4),
                'f1_weighted': round(float(f1_weighted), 4),
                'total_samples': int(len(y_t))
            },
            'confusion_matrix': {
                'labels': self.classes,
                'matrix': cm.tolist()
            },
            'class_breakdown': class_metrics,
            'mapped_predictions': mapped_preds.tolist()
        }

    def compare_multiple_clusterings(self, clustering_results):
        """
        Validates and compares multiple clustering runs side-by-side.
        """
        evaluations = []
        for res in clustering_results:
            labels = res['labels']
            algo_name = res.get('algorithm', 'Unknown')
            val = self.validate(labels, algorithm_name=algo_name)
            evaluations.append({
                'algorithm': algo_name,
                'distance_metric': res.get('distance_metric', 'N/A'),
                'accuracy': val['overall']['accuracy'],
                'precision_macro': val['overall']['precision_macro'],
                'recall_macro': val['overall']['recall_macro'],
                'f1_macro': val['overall']['f1_macro'],
                'execution_time_ms': res.get('execution_time_ms', 0),
                'silhouette_euclidean': res.get('silhouette_euclidean', 0),
                'silhouette_manhattan': res.get('silhouette_manhattan', 0),
                'davies_bouldin_index': res.get('davies_bouldin_index', 0),
                'validation_details': val
            })
        return evaluations
