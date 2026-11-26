"""
Clustering Engine for Greywater Contamination Analysis (SIH26023).
Implements K-Means and Hierarchical Agglomerative clustering with Euclidean and Manhattan metrics,
3D PCA coordinates generation for Three.js, centroid calculations, and benchmark evaluation.
"""

import time
import numpy as np
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import (
    silhouette_score,
    davies_bouldin_score,
    calinski_harabasz_score
)

class GreywaterClusterer:
    def __init__(self, n_clusters=4, random_state=42):
        self.n_clusters = n_clusters
        self.random_state = random_state

    def run_kmeans(self, scaled_X, pca_coords=None):
        """
        Runs K-Means clustering (Euclidean metric).
        Returns cluster assignments, centroids, metrics, and execution time.
        """
        start_time = time.perf_counter()
        kmeans = KMeans(
            n_clusters=self.n_clusters,
            random_state=self.random_state,
            n_init=10,
            max_iter=300
        )
        labels = kmeans.fit_predict(scaled_X)
        exec_time_ms = (time.perf_counter() - start_time) * 1000

        # Quality metrics
        sil_euc = silhouette_score(scaled_X, labels, metric='euclidean')
        sil_man = silhouette_score(scaled_X, labels, metric='cityblock')
        db_score = davies_bouldin_score(scaled_X, labels)
        ch_score = calinski_harabasz_score(scaled_X, labels)

        # Centroids in scaled space
        centroids_scaled = kmeans.cluster_centers_

        # 3D PCA centroids if pca_coords provided
        pca_centroids = []
        if pca_coords is not None:
            for k in range(self.n_clusters):
                cluster_mask = (labels == k)
                if np.sum(cluster_mask) > 0:
                    pca_centroids.append(pca_coords[cluster_mask].mean(axis=0).tolist())
                else:
                    pca_centroids.append([0.0, 0.0, 0.0])

        return {
            'algorithm': 'K-Means (Euclidean)',
            'distance_metric': 'Euclidean',
            'labels': labels.tolist(),
            'inertia': round(float(kmeans.inertia_), 2),
            'execution_time_ms': round(exec_time_ms, 2),
            'silhouette_euclidean': round(float(sil_euc), 4),
            'silhouette_manhattan': round(float(sil_man), 4),
            'davies_bouldin_index': round(float(db_score), 4),
            'calinski_harabasz_index': round(float(ch_score), 2),
            'centroids_scaled': centroids_scaled.tolist(),
            'pca_centroids': pca_centroids
        }

    def run_hierarchical(self, scaled_X, distance_metric='euclidean', linkage='average', pca_coords=None):
        """
        Runs Hierarchical Agglomerative clustering with either Euclidean or Manhattan (cityblock) metric.
        Valid linkages:
        - Euclidean: 'ward', 'complete', 'average', 'single'
        - Manhattan: 'complete', 'average', 'single'
        """
        start_time = time.perf_counter()
        
        # Scikit-learn AgglomerativeClustering parameter mapping
        metric_param = 'cityblock' if distance_metric.lower() in ('manhattan', 'cityblock', 'l1') else 'euclidean'
        
        # Ward linkage is mathematically only valid with Euclidean distance
        if metric_param == 'cityblock' and linkage == 'ward':
            linkage = 'average'

        model = AgglomerativeClustering(
            n_clusters=self.n_clusters,
            metric=metric_param,
            linkage=linkage
        )
        labels = model.fit_predict(scaled_X)
        exec_time_ms = (time.perf_counter() - start_time) * 1000

        # Quality metrics
        sil_euc = silhouette_score(scaled_X, labels, metric='euclidean')
        sil_man = silhouette_score(scaled_X, labels, metric='cityblock')
        db_score = davies_bouldin_score(scaled_X, labels)
        ch_score = calinski_harabasz_score(scaled_X, labels)

        # Centroids / Prototypes:
        # For Manhattan we also calculate the cluster medians (L1 medoids/medians)
        centroids_scaled = []
        pca_centroids = []
        for k in range(self.n_clusters):
            mask = (labels == k)
            if np.sum(mask) > 0:
                if metric_param == 'cityblock':
                    centroid = np.median(scaled_X[mask], axis=0)
                else:
                    centroid = np.mean(scaled_X[mask], axis=0)
                centroids_scaled.append(centroid.tolist())

                if pca_coords is not None:
                    pca_centroids.append(pca_coords[mask].mean(axis=0).tolist())
            else:
                centroids_scaled.append(np.zeros(scaled_X.shape[1]).tolist())
                if pca_coords is not None:
                    pca_centroids.append([0.0, 0.0, 0.0])

        return {
            'algorithm': f'Hierarchical ({distance_metric.capitalize()} - {linkage})',
            'distance_metric': distance_metric.capitalize(),
            'linkage': linkage,
            'labels': labels.tolist(),
            'execution_time_ms': round(exec_time_ms, 2),
            'silhouette_euclidean': round(float(sil_euc), 4),
            'silhouette_manhattan': round(float(sil_man), 4),
            'davies_bouldin_index': round(float(db_score), 4),
            'calinski_harabasz_index': round(float(ch_score), 2),
            'centroids_scaled': centroids_scaled,
            'pca_centroids': pca_centroids
        }

    def compare_algorithms(self, scaled_X, pca_coords=None):
        """
        Runs comprehensive benchmark comparing Euclidean and Manhattan algorithms across metrics.
        """
        results = []
        results.append(self.run_kmeans(scaled_X, pca_coords))
        results.append(self.run_hierarchical(scaled_X, distance_metric='euclidean', linkage='ward', pca_coords=pca_coords))
        results.append(self.run_hierarchical(scaled_X, distance_metric='euclidean', linkage='average', pca_coords=pca_coords))
        results.append(self.run_hierarchical(scaled_X, distance_metric='manhattan', linkage='average', pca_coords=pca_coords))
        results.append(self.run_hierarchical(scaled_X, distance_metric='manhattan', linkage='complete', pca_coords=pca_coords))
        return results

    def build_3d_cluster_payload(self, df, labels, pca_coords, pca_centroids, feature_columns):
        """
        Prepares rich JSON data for the Three.js 3D visualizer.
        Includes coordinates, sample metadata, cluster statistics, and color mapping.
        """
        cluster_colors = [
            '#00f0ff', # Cyan - Low
            '#00ff88', # Spring Green - Medium
            '#ffb703', # Amber Orange - High
            '#ff0055', # Neon Pink/Red - Severe
            '#9d4edd', # Purple
            '#4361ee'  # Electric Blue
        ]

        points = []
        for i, row in df.iterrows():
            cid = int(labels[i])
            points.append({
                'id': str(row['sample_id']),
                'source': str(row['source']),
                'cluster': cid,
                'category': str(row.get('Lab_Suitability_Category', 'Unknown')),
                'x': round(float(pca_coords[i, 0]), 4),
                'y': round(float(pca_coords[i, 1]), 4),
                'z': round(float(pca_coords[i, 2]), 4),
                'pH': float(row['pH']),
                'TDS': float(row['TDS']),
                'BOD': float(row['BOD']),
                'COD': float(row['COD']),
                'Turbidity': float(row['Turbidity']),
                'EC': float(row['EC']),
                'TSS': float(row['TSS']),
                'Oil_and_Grease': float(row['Oil_and_Grease']),
                'Temperature': float(row['Temperature']),
                'color': cluster_colors[cid % len(cluster_colors)]
            })

        centroids_3d = []
        for k in range(self.n_clusters):
            c_pos = pca_centroids[k] if k < len(pca_centroids) else [0, 0, 0]
            centroids_3d.append({
                'cluster': k,
                'x': round(float(c_pos[0]), 4),
                'y': round(float(c_pos[1]), 4),
                'z': round(float(c_pos[2]), 4),
                'color': cluster_colors[k % len(cluster_colors)]
            })

        return {
            'points': points,
            'centroids': centroids_3d,
            'cluster_colors': cluster_colors[:self.n_clusters]
        }
