"""
Data Processing and Exploratory Analysis Module for Greywater Contamination Analysis System (SIH26023).
Handles parameter definitions, scaling, PCA, correlation analysis, and statistical profiling.
"""

import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA

# The 9 core physicochemical parameters mandated by Objective 1
FEATURE_COLUMNS = [
    'pH',
    'TDS',
    'BOD',
    'COD',
    'Turbidity',
    'EC',
    'TSS',
    'Oil_and_Grease',
    'Temperature'
]

# Units and display metadata for all parameters
PARAMETER_METADATA = {
    'pH': {'unit': 'pH units', 'name': 'pH Level', 'min_safe': 6.5, 'max_safe': 8.5, 'critical_max': 9.0},
    'TDS': {'unit': 'mg/L', 'name': 'Total Dissolved Solids', 'min_safe': 0, 'max_safe': 500, 'critical_max': 1200},
    'BOD': {'unit': 'mg/L', 'name': 'Biochemical Oxygen Demand (5-day)', 'min_safe': 0, 'max_safe': 30, 'critical_max': 150},
    'COD': {'unit': 'mg/L', 'name': 'Chemical Oxygen Demand', 'min_safe': 0, 'max_safe': 100, 'critical_max': 350},
    'Turbidity': {'unit': 'NTU', 'name': 'Turbidity', 'min_safe': 0, 'max_safe': 5, 'critical_max': 50},
    'EC': {'unit': 'µS/cm', 'name': 'Electrical Conductivity', 'min_safe': 0, 'max_safe': 800, 'critical_max': 1800},
    'TSS': {'unit': 'mg/L', 'name': 'Total Suspended Solids', 'min_safe': 0, 'max_safe': 30, 'critical_max': 100},
    'Oil_and_Grease': {'unit': 'mg/L', 'name': 'Oil & Grease', 'min_safe': 0, 'max_safe': 5, 'critical_max': 30},
    'Temperature': {'unit': '°C', 'name': 'Water Temperature', 'min_safe': 15.0, 'max_safe': 35.0, 'critical_max': 40.0}
}

class GreywaterDataProcessor:
    def __init__(self, scaler_type='standard'):
        self.scaler_type = scaler_type
        if scaler_type == 'minmax':
            self.scaler = MinMaxScaler()
        else:
            self.scaler = StandardScaler()
        self.pca = PCA(n_components=3, random_state=42)
        self.is_fitted = False
        self.feature_means = {}
        self.feature_stds = {}

    def fit(self, df):
        """Fits scaler and PCA models on the feature dataframe."""
        X = df[FEATURE_COLUMNS].copy()
        # Handle any nulls by replacing with median
        X = X.fillna(X.median())
        
        scaled_X = self.scaler.fit_transform(X)
        self.pca.fit(scaled_X)
        self.is_fitted = True

        for col in FEATURE_COLUMNS:
            self.feature_means[col] = float(X[col].mean())
            self.feature_stds[col] = float(X[col].std())

        return self

    def transform(self, df):
        """Scales features and projects into 3D PCA space."""
        if not self.is_fitted:
            self.fit(df)
            
        X = df[FEATURE_COLUMNS].copy()
        X = X.fillna(X.median())
        scaled_X = self.scaler.transform(X)
        pca_coords = self.pca.transform(scaled_X)

        return scaled_X, pca_coords

    def fit_transform(self, df):
        """Fits and transforms dataframe."""
        self.fit(df)
        return self.transform(df)

    def get_pca_summary(self):
        """Returns PCA explained variance and loadings."""
        if not self.is_fitted:
            return {}

        explained_var = self.pca.explained_variance_ratio_
        cumulative_var = float(np.sum(explained_var))
        
        loadings = []
        for i, col in enumerate(FEATURE_COLUMNS):
            loadings.append({
                'parameter': col,
                'name': PARAMETER_METADATA[col]['name'],
                'PC1': round(float(self.pca.components_[0][i]), 4),
                'PC2': round(float(self.pca.components_[1][i]), 4),
                'PC3': round(float(self.pca.components_[2][i]), 4)
            })

        return {
            'explained_variance': [round(float(v) * 100, 2) for v in explained_var],
            'cumulative_variance': round(cumulative_var * 100, 2),
            'loadings': loadings
        }

    @staticmethod
    def compute_summary_statistics(df):
        """Computes comprehensive descriptive statistics for each parameter."""
        stats = {}
        for col in FEATURE_COLUMNS:
            series = df[col].dropna()
            q25 = float(series.quantile(0.25))
            q75 = float(series.quantile(0.75))
            iqr = q75 - q25
            
            # Outlier detection using 1.5 * IQR
            lower_bound = q25 - 1.5 * iqr
            upper_bound = q75 + 1.5 * iqr
            outliers_count = int(((series < lower_bound) | (series > upper_bound)).sum())

            stats[col] = {
                'name': PARAMETER_METADATA[col]['name'],
                'unit': PARAMETER_METADATA[col]['unit'],
                'count': int(len(series)),
                'mean': round(float(series.mean()), 2),
                'std': round(float(series.std()), 2),
                'min': round(float(series.min()), 2),
                'q25': round(q25, 2),
                'median': round(float(series.median()), 2),
                'q75': round(q75, 2),
                'max': round(float(series.max()), 2),
                'iqr': round(iqr, 2),
                'outliers_count': outliers_count,
                'min_safe': PARAMETER_METADATA[col]['min_safe'],
                'max_safe': PARAMETER_METADATA[col]['max_safe']
            }
        return stats

    @staticmethod
    def compute_correlation_matrix(df):
        """Computes Pearson and Spearman correlation matrices."""
        sub_df = df[FEATURE_COLUMNS].dropna()
        pearson = sub_df.corr(method='pearson').round(3).to_dict()
        spearman = sub_df.corr(method='spearman').round(3).to_dict()
        return {
            'parameters': FEATURE_COLUMNS,
            'pearson': pearson,
            'spearman': spearman
        }

    @staticmethod
    def compute_distributions(df, bins=12):
        """Generates histogram data for each parameter for frontend visualization."""
        distributions = {}
        for col in FEATURE_COLUMNS:
            series = df[col].dropna()
            counts, bin_edges = np.histogram(series, bins=bins)
            bin_labels = [f"{round(bin_edges[i], 1)}-{round(bin_edges[i+1], 1)}" for i in range(len(counts))]
            distributions[col] = {
                'labels': bin_labels,
                'counts': counts.tolist(),
                'unit': PARAMETER_METADATA[col]['unit']
            }
        return distributions

    @staticmethod
    def compute_category_profiles(df):
        """Aggregates parameter averages and counts by Lab_Suitability_Category."""
        if 'Lab_Suitability_Category' not in df.columns:
            return {}
        
        grouped = df.groupby('Lab_Suitability_Category')[FEATURE_COLUMNS].mean().round(2)
        counts = df['Lab_Suitability_Category'].value_counts().to_dict()
        
        profiles = {}
        for cat, row in grouped.iterrows():
            profiles[cat] = {
                'count': int(counts.get(cat, 0)),
                'parameters': row.to_dict()
            }
        return profiles
