"""
Flask Application for Greywater Contamination Analysis and Treatment Recommendation System (SIH26023).
Provides RESTful APIs and UI rendering for all three project objectives:
1. Physicochemical parameter collection & analysis
2. Euclidean and Manhattan distance algorithm implementation and comparison
3. Laboratory validation against ground truth categories with confusion matrix, accuracy, precision, recall, F1
"""

import os
import io
import json
import zipfile
from datetime import datetime
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, jsonify, send_file, Response

from database import (
    init_db,
    get_all_samples_df,
    insert_sample,
    delete_sample_by_id,
    log_analysis_result,
    get_analysis_history,
    reset_database_to_seed,
    clear_all_samples,
    auto_classify_pending_samples
)
from models.data_processor import (
    FEATURE_COLUMNS,
    PARAMETER_METADATA,
    GreywaterDataProcessor
)
from models.distance_engine import (
    calculate_pairwise_matrices,
    find_nearest_neighbors,
    compute_dimension_contributions
)
from models.clusterer import GreywaterClusterer
from models.validator import LaboratoryValidator
from models.recommender import TreatmentRecommender
from models.report_generator import ReportGenerator

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sih26023-greywater-secure-key-2026')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

recommender = TreatmentRecommender()
data_processor = GreywaterDataProcessor()

with app.app_context():
    init_db(seed_if_empty=True)

@app.route('/')
def index():
    """Renders the main futuristic 3D dashboard."""
    return render_template('index.html')

@app.route('/api/overview', methods=['GET'])
def get_overview():
    """Returns dashboard overview statistics, WQI distribution, and recent samples."""
    df = get_all_samples_df()
    if df.empty:
        empty_averages = {
            col: {'mean': 0.0, 'min': 0.0, 'max': 0.0, 'unit': PARAMETER_METADATA[col]['unit']}
            for col in FEATURE_COLUMNS
        }
        return jsonify({
            'total_samples': 0,
            'average_wqi': 0.0,
            'water_health_index': 0,
            'category_distribution': {},
            'source_distribution': {},
            'parameter_averages': empty_averages,
            'recent_samples': []
        })

    # Calculate WQI for all samples to compute average health index
    wqis = []
    category_counts = df['Lab_Suitability_Category'].value_counts().to_dict()
    source_counts = df['source'].value_counts().head(6).to_dict()

    for _, row in df.iterrows():
        w_res = recommender.calculate_wqi(row.to_dict())
        wqis.append(w_res['wqi'])

    avg_wqi = round(float(np.mean(wqis)), 1)
    
    # Invert WQI to 0-100 water health rating (lower WQI is cleaner)
    # Excellent <50 -> 90-100%, Good 50-100 -> 70-89%, Poor >100 -> <70%
    health_index = max(10, min(98, round(100 - (avg_wqi / 2.5), 1)))

    # Parameter means for summary cards
    param_averages = {}
    for col in FEATURE_COLUMNS:
        param_averages[col] = {
            'mean': round(float(df[col].mean()), 1),
            'min': round(float(df[col].min()), 1),
            'max': round(float(df[col].max()), 1),
            'unit': PARAMETER_METADATA[col]['unit']
        }

    # Recent 6 samples
    recent = df.tail(6).to_dict(orient='records')

    return jsonify({
        'total_samples': len(df),
        'average_wqi': avg_wqi,
        'water_health_index': health_index,
        'category_distribution': category_counts,
        'source_distribution': source_counts,
        'parameter_averages': param_averages,
        'recent_samples': recent
    })

@app.route('/api/samples', methods=['GET'])
def get_samples():
    """Returns all samples or paginated/filtered samples."""
    df = get_all_samples_df()
    search = request.args.get('search', '').strip().lower()
    category = request.args.get('category', '').strip()

    if search:
        mask = (
            df['sample_id'].str.lower().str.contains(search) |
            df['source'].str.lower().str.contains(search) |
            df['Location'].str.lower().str.contains(search)
        )
        df = df[mask]

    if category and category != 'All':
        df = df[df['Lab_Suitability_Category'] == category]

    samples = df.to_dict(orient='records')
    return jsonify({
        'count': len(samples),
        'samples': samples
    })

@app.route('/api/samples', methods=['POST'])
def add_sample():
    """Manual sample entry with real-time classification, distance calculation, and recommendation."""
    data = request.get_json() or {}
    
    # Verify required parameters
    missing = [p for p in FEATURE_COLUMNS if p not in data or data[p] is None or data[p] == '']
    if missing:
        return jsonify({'error': f"Missing required parameters: {', '.join(missing)}"}), 400

    try:
        sample_data = {
            'source': data.get('source', 'Manual Entry'),
            'Location': data.get('Location', 'Decentralized Station'),
            'pH': float(data['pH']),
            'TDS': float(data['TDS']),
            'BOD': float(data['BOD']),
            'COD': float(data['COD']),
            'Turbidity': float(data['Turbidity']),
            'EC': float(data['EC']),
            'TSS': float(data['TSS']),
            'Oil_and_Grease': float(data['Oil_and_Grease']),
            'Temperature': float(data['Temperature']),
            'Lab_Suitability_Category': data.get('Lab_Suitability_Category', 'Pending Lab Confirmation'),
            'Collection_Date': data.get('Collection_Date', datetime.now().strftime('%Y-%m-%d'))
        }
        if 'sample_id' in data and data['sample_id']:
            sample_data['sample_id'] = data['sample_id']

        # Save to database
        new_id = insert_sample(sample_data)
        sample_data['sample_id'] = new_id

        # Compute instant recommendation
        treatment_rec = recommender.generate_treatment_recommendation(sample_data)
        wqi_info = recommender.calculate_wqi(sample_data)

        # Log into analysis history
        log_analysis_result({
            'sample_id': new_id,
            'source': sample_data['source'],
            'pH': sample_data['pH'],
            'TDS': sample_data['TDS'],
            'BOD': sample_data['BOD'],
            'COD': sample_data['COD'],
            'Turbidity': sample_data['Turbidity'],
            'EC': sample_data['EC'],
            'TSS': sample_data['TSS'],
            'Oil_and_Grease': sample_data['Oil_and_Grease'],
            'Temperature': sample_data['Temperature'],
            'wqi': wqi_info['wqi'],
            'contamination_level': wqi_info['category_hint'],
            'mapped_category': treatment_rec['category'],
            'recommended_stages': json.dumps([s['title'] for s in treatment_rec['stages'].values()]),
            'suitability_reuse': json.dumps({k: v['status'] for k, v in treatment_rec['suitability_matrix'].items()}),
            'chemical_dosing': json.dumps(treatment_rec['chemical_dosing']),
            'notes': data.get('notes', 'Manual web dashboard entry')
        })

        return jsonify({
            'success': True,
            'sample_id': new_id,
            'sample': sample_data,
            'wqi': wqi_info,
            'treatment': treatment_rec
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/samples/<sample_id>', methods=['DELETE'])
def delete_sample(sample_id):
    """Deletes a sample by sample_id."""
    success = delete_sample_by_id(sample_id)
    if success:
        return jsonify({'success': True, 'message': f'Sample {sample_id} deleted.'})
    return jsonify({'error': 'Sample not found'}), 404

@app.route('/api/reset_database', methods=['POST'])
def reset_db():
    """Resets database back to default seed dataset."""
    reset_database_to_seed()
    return jsonify({'success': True, 'message': 'Database reset to default reference dataset (270 samples).'})

@app.route('/api/clear_data', methods=['POST'])
def clear_data():
    """Wipes all samples from database so user can work exclusively with their own custom dataset."""
    clear_history = request.args.get('clear_history', 'false').lower() in ('true', '1', 'yes')
    clear_all_samples(clear_history=clear_history)
    return jsonify({
        'success': True,
        'message': 'All existing samples have been cleared. You can now import your custom dataset on a clean slate.'
    })

@app.route('/api/auto_classify', methods=['POST'])
def auto_classify():
    """Automatically assigns treatment suitability categories to samples that are pending confirmation."""
    def classify_sample(s):
        w = recommender.calculate_wqi(s)
        return w['category_hint']
    count = auto_classify_pending_samples(classify_sample)
    return jsonify({
        'success': True,
        'updated_count': count,
        'message': f'Successfully classified {count} samples based on physicochemical standard thresholds.'
    })

@app.route('/api/upload_csv', methods=['POST'])
def upload_csv():
    """Uploads and imports greywater CSV dataset with optional replacement and schema validation."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Check if user selected Replace Mode (Clear existing before importing)
    replace_existing = request.form.get('replace_existing', 'false').lower() in ('true', '1', 'yes', 'on')

    try:
        content = file.stream.read().decode('utf-8', errors='ignore')
        df_upload = pd.read_csv(io.StringIO(content))

        # Check required columns
        missing = [col for col in FEATURE_COLUMNS if col not in df_upload.columns]
        if missing:
            return jsonify({'error': f"CSV is missing required parameters: {', '.join(missing)}"}), 400

        # If replace mode is enabled, wipe existing records first
        if replace_existing:
            clear_all_samples(clear_history=False)

        # Import valid rows
        imported_count = 0
        for _, row in df_upload.iterrows():
            rec = {
                'source': str(row.get('source', 'Custom CSV Import')),
                'Location': str(row.get('Location', 'Batch Upload')),
                'pH': float(row['pH']),
                'TDS': float(row['TDS']),
                'BOD': float(row['BOD']),
                'COD': float(row['COD']),
                'Turbidity': float(row['Turbidity']),
                'EC': float(row['EC']),
                'TSS': float(row['TSS']),
                'Oil_and_Grease': float(row['Oil_and_Grease']),
                'Temperature': float(row['Temperature']),
                'Collection_Date': str(row.get('Collection_Date', datetime.now().strftime('%Y-%m-%d')))
            }
            if 'sample_id' in row and pd.notna(row['sample_id']):
                rec['sample_id'] = str(row['sample_id'])

            # Determine category: keep confirmed lab category if provided, otherwise auto-infer from WQI
            raw_cat = row.get('Lab_Suitability_Category')
            if pd.isna(raw_cat) or not str(raw_cat).strip() or str(raw_cat).strip().lower() in ('nan', 'none', 'pending lab confirmation', ''):
                inferred = recommender.calculate_wqi(rec)['category_hint']
                rec['Lab_Suitability_Category'] = inferred
            else:
                rec['Lab_Suitability_Category'] = str(raw_cat).strip()
            
            insert_sample(rec)
            imported_count += 1

        msg = f"Replaced existing dataset with {imported_count} new samples." if replace_existing else f"Successfully imported {imported_count} samples from CSV."
        return jsonify({
            'success': True,
            'message': msg,
            'imported_count': imported_count,
            'replaced': replace_existing
        })

    except Exception as e:
        return jsonify({'error': f'Failed to process CSV file: {str(e)}'}), 500

@app.route('/api/eda', methods=['GET'])
def get_eda():
    """Returns exploratory data analysis: statistics, correlations, distributions, category profiles, PCA."""
    df = get_all_samples_df()
    if df.empty:
        return jsonify({'error': 'No samples available for analysis'}), 404

    processor = GreywaterDataProcessor()
    processor.fit(df)

    summary_stats = processor.compute_summary_statistics(df)
    corr_matrix = processor.compute_correlation_matrix(df)
    distributions = processor.compute_distributions(df)
    cat_profiles = processor.compute_category_profiles(df)
    pca_summary = processor.get_pca_summary()

    return jsonify({
        'summary_statistics': summary_stats,
        'correlation_matrix': corr_matrix,
        'distributions': distributions,
        'category_profiles': cat_profiles,
        'pca_summary': pca_summary,
        'total_samples': len(df)
    })

@app.route('/api/distance_analysis', methods=['POST'])
def distance_analysis():
    """
    Objective 2: Computes and compares Euclidean and Manhattan distance metrics.
    Supports pairwise matrix analysis, distance distributions, and k-nearest neighbors search.
    """
    df = get_all_samples_df()
    if df.empty:
        return jsonify({'error': 'No samples available'}), 404

    data = request.get_json() or {}
    k_neighbors = int(data.get('k_neighbors', 5))
    query_sample_id = data.get('query_sample_id')
    custom_vector = data.get('custom_vector') # optional list of 9 parameters

    # Fit and standardize features
    processor = GreywaterDataProcessor(scaler_type='standard')
    scaled_X, _ = processor.fit_transform(df)
    sample_ids = df['sample_id'].tolist()
    sample_records = df.to_dict(orient='records')

    # Pairwise matrix calculation & metric comparison
    matrix_res = calculate_pairwise_matrices(scaled_X, sample_ids)

    # Nearest neighbor query if requested
    nn_results = None
    query_info = None

    if query_sample_id and query_sample_id in sample_ids:
        idx = sample_ids.index(query_sample_id)
        query_vec = scaled_X[idx]
        query_info = sample_records[idx]
        nn_results = find_nearest_neighbors(query_vec, scaled_X, sample_records, k=k_neighbors)
    elif custom_vector and len(custom_vector) == len(FEATURE_COLUMNS):
        custom_df = pd.DataFrame([custom_vector], columns=FEATURE_COLUMNS)
        custom_scaled, _ = processor.transform(custom_df)
        query_vec = custom_scaled[0]
        query_info = dict(zip(FEATURE_COLUMNS, custom_vector))
        query_info['sample_id'] = 'Custom Query Input'
        query_info['source'] = 'User Query Vector'
        nn_results = find_nearest_neighbors(query_vec, scaled_X, sample_records, k=k_neighbors)
    elif len(sample_ids) > 0:
        # Default to first sample
        query_vec = scaled_X[0]
        query_info = sample_records[0]
        nn_results = find_nearest_neighbors(query_vec, scaled_X, sample_records, k=k_neighbors)

    # Dimension contribution between query and its top Euclidean neighbor
    dimension_breakdown = None
    if nn_results and 'euclidean' in nn_results and len(nn_results['euclidean']) > 1:
        # Pick 2nd neighbor (1st is itself if query is from dataset)
        target_rec = nn_results['euclidean'][1] if nn_results['euclidean'][0]['sample_id'] == query_info.get('sample_id') else nn_results['euclidean'][0]
        target_vec = np.array([target_rec[col] for col in FEATURE_COLUMNS])
        q_raw_vec = np.array([query_info[col] for col in FEATURE_COLUMNS])
        dimension_breakdown = compute_dimension_contributions(q_raw_vec, target_vec, FEATURE_COLUMNS)
        dimension_breakdown['target_sample_id'] = target_rec.get('sample_id')

    return jsonify({
        'stats': matrix_res['stats'],
        'preview_sample_ids': matrix_res['preview_sample_ids'],
        'euclidean_matrix_preview': matrix_res['euclidean_matrix_preview'],
        'manhattan_matrix_preview': matrix_res['manhattan_matrix_preview'],
        'query_info': query_info,
        'nearest_neighbors': nn_results,
        'dimension_breakdown': dimension_breakdown
    })

@app.route('/api/clustering', methods=['POST'])
def run_clustering():
    """
    Executes K-Means or Hierarchical Clustering with Euclidean or Manhattan metrics.
    Returns 3D PCA coordinates and cluster payloads for Three.js.
    """
    df = get_all_samples_df()
    if df.empty:
        return jsonify({'error': 'No samples available'}), 404

    data = request.get_json() or {}
    n_clusters = int(data.get('n_clusters', 4))
    algorithm = data.get('algorithm', 'kmeans') # 'kmeans', 'hierarchical_euclidean', 'hierarchical_manhattan'
    linkage = data.get('linkage', 'average') # 'ward', 'complete', 'average'

    processor = GreywaterDataProcessor()
    scaled_X, pca_coords = processor.fit_transform(df)

    clusterer = GreywaterClusterer(n_clusters=n_clusters)

    if algorithm == 'kmeans':
        result = clusterer.run_kmeans(scaled_X, pca_coords)
    elif algorithm == 'hierarchical_manhattan':
        # Ward linkage is not valid with Manhattan
        link = 'average' if linkage == 'ward' else linkage
        result = clusterer.run_hierarchical(scaled_X, distance_metric='manhattan', linkage=link, pca_coords=pca_coords)
    else: # hierarchical_euclidean
        result = clusterer.run_hierarchical(scaled_X, distance_metric='euclidean', linkage=linkage, pca_coords=pca_coords)

    # Build 3D visualizer payload
    payload_3d = clusterer.build_3d_cluster_payload(
        df=df,
        labels=result['labels'],
        pca_coords=pca_coords,
        pca_centroids=result['pca_centroids'],
        feature_columns=FEATURE_COLUMNS
    )

    result['threejs_payload'] = payload_3d
    return jsonify(result)

@app.route('/api/algorithm_comparison', methods=['GET'])
def get_algorithm_comparison():
    """
    Objective 2: Benchmarks and compares Euclidean vs Manhattan clustering across execution time,
    silhouette scores, Davies-Bouldin index, and Calinski-Harabasz index.
    """
    df = get_all_samples_df()
    if df.empty:
        return jsonify({'error': 'No samples available'}), 404

    processor = GreywaterDataProcessor()
    scaled_X, pca_coords = processor.fit_transform(df)

    clusterer = GreywaterClusterer(n_clusters=4)
    comparison_results = clusterer.compare_algorithms(scaled_X, pca_coords)

    # Also compute validation against ground truth for all algorithms (Objective 3)
    validator = LaboratoryValidator(df['Lab_Suitability_Category'])
    detailed_benchmarks = validator.compare_multiple_clusterings(comparison_results)

    return jsonify({
        'benchmarks': detailed_benchmarks,
        'summary': {
            'total_samples': len(df),
            'features_analyzed': len(FEATURE_COLUMNS),
            'algorithms_evaluated': len(detailed_benchmarks)
        }
    })

@app.route('/api/validation', methods=['POST'])
def validate_clustering():
    """
    Objective 3: Validates clustering results against laboratory-confirmed categories.
    Computes real confusion matrix, accuracy, precision, recall, and F1-score.
    """
    df = get_all_samples_df()
    if df.empty:
        return jsonify({'error': 'No samples available'}), 404

    data = request.get_json() or {}
    algorithm = data.get('algorithm', 'kmeans')
    linkage = data.get('linkage', 'average')
    n_clusters = int(data.get('n_clusters', 4))

    processor = GreywaterDataProcessor()
    scaled_X, pca_coords = processor.fit_transform(df)

    clusterer = GreywaterClusterer(n_clusters=n_clusters)
    if algorithm == 'kmeans':
        res = clusterer.run_kmeans(scaled_X, pca_coords)
    elif algorithm == 'hierarchical_manhattan':
        link = 'average' if linkage == 'ward' else linkage
        res = clusterer.run_hierarchical(scaled_X, distance_metric='manhattan', linkage=link, pca_coords=pca_coords)
    else:
        res = clusterer.run_hierarchical(scaled_X, distance_metric='euclidean', linkage=linkage, pca_coords=pca_coords)

    validator = LaboratoryValidator(df['Lab_Suitability_Category'])
    val_report = validator.validate(res['labels'], algorithm_name=res['algorithm'])
    val_report['clustering_metrics'] = {
        'silhouette_euclidean': res.get('silhouette_euclidean'),
        'silhouette_manhattan': res.get('silhouette_manhattan'),
        'davies_bouldin_index': res.get('davies_bouldin_index'),
        'calinski_harabasz_index': res.get('calinski_harabasz_index'),
        'execution_time_ms': res.get('execution_time_ms')
    }

    return jsonify(val_report)

@app.route('/api/recommendation', methods=['POST'])
def get_recommendation():
    """Generates contamination profile, treatment train, dosing, and reuse suitability for any sample."""
    data = request.get_json() or {}
    sample_id = data.get('sample_id')
    
    if sample_id:
        df = get_all_samples_df()
        row = df[df['sample_id'] == sample_id]
        if row.empty:
            return jsonify({'error': 'Sample ID not found'}), 404
        sample_dict = row.iloc[0].to_dict()
    else:
        sample_dict = data

    profile = recommender.generate_parameter_profile(sample_dict)
    treatment = recommender.generate_treatment_recommendation(sample_dict, category=sample_dict.get('Lab_Suitability_Category'))
    wqi = recommender.calculate_wqi(sample_dict)

    return jsonify({
        'sample': sample_dict,
        'wqi': wqi,
        'profile': profile,
        'treatment': treatment
    })

@app.route('/api/history', methods=['GET'])
def get_history():
    """Returns recent logged analyses."""
    limit = int(request.args.get('limit', 50))
    history = get_analysis_history(limit)
    return jsonify({
        'count': len(history),
        'history': history
    })

@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    """Downloads all samples as a formatted CSV file."""
    df = get_all_samples_df()
    csv_str = ReportGenerator.generate_csv_export(df.to_dict(orient='records'))
    return Response(
        csv_str,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=HydraSense_Greywater_Samples_{datetime.now().strftime("%Y%m%d")}.csv'}
    )

@app.route('/api/export/pdf', methods=['POST'])
def export_pdf():
    """Generates and downloads a laboratory analysis certificate PDF for a sample."""
    data = request.get_json() or {}
    sample_id = data.get('sample_id')
    df = get_all_samples_df()

    if sample_id:
        row = df[df['sample_id'] == sample_id]
        if not row.empty:
            sample_dict = row.iloc[0].to_dict()
        else:
            sample_dict = data
    else:
        sample_dict = data if any(k in data for k in FEATURE_COLUMNS) else df.iloc[0].to_dict()

    wqi_info = recommender.calculate_wqi(sample_dict)
    treatment_rec = recommender.generate_treatment_recommendation(sample_dict, category=sample_dict.get('Lab_Suitability_Category'))
    pdf_bytes = ReportGenerator.generate_sample_pdf(sample_dict, treatment_rec, wqi_info)

    filename = f"HydraSense_Analysis_{sample_dict.get('sample_id', 'Sample')}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/download_project_zip', methods=['GET'])
def download_project_zip():
    """Provides direct browser download of the complete project .zip archive."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root_dir, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', 'venv', '.venv')]
            for file_name in files:
                if file_name.endswith(('.pyc', '.zip')):
                    continue
                full_path = os.path.join(root_dir, file_name)
                arc_name = os.path.join('HydraSense_SIH26023', os.path.relpath(full_path, base_dir))
                zf.write(full_path, arc_name)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name='HydraSense_SIH26023_Greywater_System.zip'
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
