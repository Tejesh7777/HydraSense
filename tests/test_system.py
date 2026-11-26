"""
Comprehensive unit and integration test suite for HydraSense Greywater System (SIH26023).
Tests all 3 objectives, data structures, math functions, machine learning pipelines, and Flask APIs.
"""

import os
import sys
# Ensure project root directory is always on sys.path regardless of where test is invoked from
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import unittest
import json
import numpy as np

from database import init_db, get_all_samples_df
from models.data_processor import FEATURE_COLUMNS, GreywaterDataProcessor
from models.distance_engine import (
    euclidean_distance,
    manhattan_distance
)
from models.clusterer import GreywaterClusterer
from models.validator import LaboratoryValidator
from models.recommender import TreatmentRecommender
from models.report_generator import ReportGenerator
from app import app

class TestGreywaterSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.df = get_all_samples_df()
        cls.client = app.test_client()

    def test_database_populated(self):
        """Test that the database contains the required greywater dataset."""
        self.assertGreaterEqual(len(self.df), 200)
        for col in FEATURE_COLUMNS:
            self.assertIn(col, self.df.columns)
        self.assertIn('Lab_Suitability_Category', self.df.columns)

    def test_distance_calculations(self):
        """Test pure mathematical formulations of Euclidean and Manhattan distances."""
        u = [7.0, 300.0, 30.0, 70.0, 10.0, 450.0, 25.0, 4.0, 25.0]
        v = [8.0, 500.0, 80.0, 160.0, 40.0, 750.0, 75.0, 15.0, 30.0]

        # Euclidean: sqrt(sum((u-v)^2))
        expected_euc = np.sqrt(np.sum((np.array(u) - np.array(v)) ** 2))
        calc_euc = euclidean_distance(u, v)
        self.assertAlmostEqual(calc_euc, expected_euc, places=5)

        # Manhattan: sum(|u-v|)
        expected_man = np.sum(np.abs(np.array(u) - np.array(v)))
        calc_man = manhattan_distance(u, v)
        self.assertAlmostEqual(calc_man, expected_man, places=5)

        # Manhattan is always >= Euclidean in real feature space
        self.assertGreaterEqual(calc_man, calc_euc)

    def test_clustering_and_3d_payload(self):
        """Test K-Means and Hierarchical clustering with Euclidean and Manhattan."""
        processor = GreywaterDataProcessor()
        scaled_X, pca_coords = processor.fit_transform(self.df)

        clusterer = GreywaterClusterer(n_clusters=4)

        # K-Means
        km_res = clusterer.run_kmeans(scaled_X, pca_coords)
        self.assertEqual(len(km_res['labels']), len(self.df))
        self.assertIn('silhouette_euclidean', km_res)
        self.assertIn('inertia', km_res)

        # Hierarchical Manhattan
        h_man_res = clusterer.run_hierarchical(scaled_X, distance_metric='manhattan', linkage='average', pca_coords=pca_coords)
        self.assertEqual(len(h_man_res['labels']), len(self.df))
        self.assertIn('silhouette_manhattan', h_man_res)

        # 3D Payload structure
        payload = clusterer.build_3d_cluster_payload(
            self.df,
            km_res['labels'],
            pca_coords,
            km_res['pca_centroids'],
            FEATURE_COLUMNS
        )
        self.assertIn('points', payload)
        self.assertIn('centroids', payload)
        self.assertEqual(len(payload['points']), len(self.df))

    def test_laboratory_validation(self):
        """Test Hungarian cluster matching and laboratory validation metrics."""
        processor = GreywaterDataProcessor()
        scaled_X, pca_coords = processor.fit_transform(self.df)

        clusterer = GreywaterClusterer(n_clusters=4)
        km_res = clusterer.run_kmeans(scaled_X, pca_coords)

        validator = LaboratoryValidator(self.df['Lab_Suitability_Category'])
        report = validator.validate(km_res['labels'])

        self.assertIn('overall', report)
        self.assertIn('accuracy', report['overall'])
        self.assertGreaterEqual(report['overall']['accuracy'], 0.0)
        self.assertLessEqual(report['overall']['accuracy'], 1.0)
        self.assertIn('confusion_matrix', report)
        self.assertEqual(len(report['confusion_matrix']['matrix']), 4)
        self.assertIn('class_breakdown', report)

    def test_treatment_recommendation_and_wqi(self):
        """Test WQI and multi-stage treatment recommendation."""
        recommender = TreatmentRecommender()
        sample = {
            'pH': 7.4, 'TDS': 320.0, 'BOD': 45.0, 'COD': 110.0,
            'Turbidity': 18.0, 'EC': 480.0, 'TSS': 35.0, 'Oil_and_Grease': 6.0, 'Temperature': 28.0
        }
        wqi = recommender.calculate_wqi(sample)
        self.assertIn('wqi', wqi)
        self.assertIn('status', wqi)

        rec = recommender.generate_treatment_recommendation(sample)
        self.assertIn('stages', rec)
        self.assertIn('chemical_dosing', rec)
        self.assertIn('suitability_matrix', rec)
        self.assertGreater(rec['chemical_dosing']['pac_dose_mg_l'], 0)

    def test_pdf_generation(self):
        """Test ReportLab PDF generation generates valid bytes."""
        sample = self.df.iloc[0].to_dict()
        recommender = TreatmentRecommender()
        wqi_info = recommender.calculate_wqi(sample)
        treatment = recommender.generate_treatment_recommendation(sample)

        pdf_bytes = ReportGenerator.generate_sample_pdf(sample, treatment, wqi_info)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))

    def test_flask_endpoints(self):
        """Test core API routes return status 200 and valid JSON."""
        # 0. Root page & static
        r0 = self.client.get('/')
        self.assertEqual(r0.status_code, 200)
        self.assertIn(b'HydraSense', r0.data)

        # 1. Overview
        r1 = self.client.get('/api/overview')
        self.assertEqual(r1.status_code, 200)
        d1 = json.loads(r1.data)
        self.assertIn('total_samples', d1)

        # 2. EDA
        r2 = self.client.get('/api/eda')
        self.assertEqual(r2.status_code, 200)
        d2 = json.loads(r2.data)
        self.assertIn('summary_statistics', d2)

        # 3. Distance analysis
        r3 = self.client.post('/api/distance_analysis', json={'k_neighbors': 3})
        self.assertEqual(r3.status_code, 200)
        d3 = json.loads(r3.data)
        self.assertIn('stats', d3)

        # 4. Clustering
        r4 = self.client.post('/api/clustering', json={'n_clusters': 4, 'algorithm': 'kmeans'})
        self.assertEqual(r4.status_code, 200)
        d4 = json.loads(r4.data)
        self.assertIn('threejs_payload', d4)

        # 5. Algorithm Comparison
        r5 = self.client.get('/api/algorithm_comparison')
        self.assertEqual(r5.status_code, 200)
        d5 = json.loads(r5.data)
        self.assertIn('benchmarks', d5)

        # 6. Validation
        r6 = self.client.post('/api/validation', json={'algorithm': 'kmeans'})
        self.assertEqual(r6.status_code, 200)
        d6 = json.loads(r6.data)
        self.assertIn('confusion_matrix', d6)

        # 7. Recommendation
        r7 = self.client.post('/api/recommendation', json={'sample_id': 'GW-0001'})
        self.assertEqual(r7.status_code, 200)
        d7 = json.loads(r7.data)
        self.assertIn('treatment', d7)

        # 8. CSV Export
        r8 = self.client.get('/api/export/csv')
        self.assertEqual(r8.status_code, 200)
        self.assertIn(b'GW-0001', r8.data)

if __name__ == '__main__':
    unittest.main()
