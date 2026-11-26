"""
Database management module for Greywater Contamination Analysis System (SIH26023).
Manages SQLite connection, schema creation, data seeding, and CRUD operations.
"""

import sqlite3
import os
import pandas as pd
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'greywater.db')
SEED_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'greywater_seed.csv')

def get_db_connection():
    """Returns a connection to the SQLite database with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(seed_if_empty=True):
    """Initializes database tables and seeds initial data if table is empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS samples (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sample_id TEXT UNIQUE NOT NULL,
        source TEXT NOT NULL,
        pH REAL NOT NULL,
        TDS REAL NOT NULL,
        BOD REAL NOT NULL,
        COD REAL NOT NULL,
        Turbidity REAL NOT NULL,
        EC REAL NOT NULL,
        TSS REAL NOT NULL,
        Oil_and_Grease REAL NOT NULL,
        Temperature REAL NOT NULL,
        Lab_Suitability_Category TEXT NOT NULL,
        Location TEXT DEFAULT 'Main Campus',
        Collection_Date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS analysis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_id TEXT UNIQUE NOT NULL,
        sample_id TEXT,
        source TEXT,
        pH REAL,
        TDS REAL,
        BOD REAL,
        COD REAL,
        Turbidity REAL,
        EC REAL,
        TSS REAL,
        Oil_and_Grease REAL,
        Temperature REAL,
        wqi REAL,
        contamination_level TEXT,
        predicted_cluster INTEGER,
        mapped_category TEXT,
        euclidean_dist_to_centroid REAL,
        manhattan_dist_to_centroid REAL,
        recommended_stages TEXT,
        suitability_reuse TEXT,
        chemical_dosing TEXT,
        notes TEXT,
        analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')

    conn.commit()

    cursor.execute('SELECT COUNT(*) as count FROM samples')
    count = cursor.fetchone()['count']

    if count == 0 and seed_if_empty and os.path.exists(SEED_CSV_PATH):
        seed_from_csv(SEED_CSV_PATH, conn)

    conn.close()

def seed_from_csv(csv_path, conn=None):
    """Seeds database from a CSV file."""
    close_at_end = False
    if conn is None:
        conn = get_db_connection()
        close_at_end = True

    try:
        df = pd.read_csv(csv_path)

        if 'Location' not in df.columns:
            df['Location'] = 'Decentralized Station'
        if 'Collection_Date' not in df.columns:
            df['Collection_Date'] = datetime.now().strftime('%Y-%m-%d')

        cursor = conn.cursor()
        for _, row in df.iterrows():
            cursor.execute('''
            INSERT OR IGNORE INTO samples (
                sample_id, source, pH, TDS, BOD, COD,
                Turbidity, EC, TSS, Oil_and_Grease, Temperature,
                Lab_Suitability_Category, Location, Collection_Date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(row['sample_id']),
                str(row['source']),
                float(row['pH']),
                float(row['TDS']),
                float(row['BOD']),
                float(row['COD']),
                float(row['Turbidity']),
                float(row['EC']),
                float(row['TSS']),
                float(row['Oil_and_Grease']),
                float(row['Temperature']),
                str(row['Lab_Suitability_Category']),
                str(row['Location']),
                str(row['Collection_Date'])
            ))
        conn.commit()
    finally:
        if close_at_end:
            conn.close()

def get_all_samples_df():
    """Loads all samples into a Pandas DataFrame."""
    conn = get_db_connection()
    try:
        df = pd.read_sql_query('SELECT * FROM samples ORDER BY id ASC', conn)
        return df
    finally:
        conn.close()

def insert_sample(sample_dict):
    """Inserts a single new sample into the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Generate sample_id if not present
        if 'sample_id' not in sample_dict or not sample_dict['sample_id']:
            cursor.execute('SELECT MAX(id) as max_id FROM samples')
            res = cursor.fetchone()
            next_id = (res['max_id'] or 0) + 1
            sample_dict['sample_id'] = f'GW-{next_id:04d}'

        cursor.execute('''
        INSERT INTO samples (
            sample_id, source, pH, TDS, BOD, COD,
            Turbidity, EC, TSS, Oil_and_Grease, Temperature,
            Lab_Suitability_Category, Location, Collection_Date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sample_dict['sample_id'],
            sample_dict.get('source', 'Manual Entry'),
            float(sample_dict['pH']),
            float(sample_dict['TDS']),
            float(sample_dict['BOD']),
            float(sample_dict['COD']),
            float(sample_dict['Turbidity']),
            float(sample_dict['EC']),
            float(sample_dict['TSS']),
            float(sample_dict['Oil_and_Grease']),
            float(sample_dict['Temperature']),
            sample_dict.get('Lab_Suitability_Category', 'Pending Lab Confirmation'),
            sample_dict.get('Location', 'Onsite Manual Sample'),
            sample_dict.get('Collection_Date', datetime.now().strftime('%Y-%m-%d'))
        ))
        conn.commit()
        return sample_dict['sample_id']
    finally:
        conn.close()

def delete_sample_by_id(sample_id):
    """Deletes a sample by sample_id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM samples WHERE sample_id = ?', (sample_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def log_analysis_result(entry_dict):
    """Logs an analysis result to history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO analysis_history (
            analysis_id, sample_id, source, pH, TDS, BOD, COD,
            Turbidity, EC, TSS, Oil_and_Grease, Temperature,
            wqi, contamination_level, predicted_cluster, mapped_category,
            euclidean_dist_to_centroid, manhattan_dist_to_centroid,
            recommended_stages, suitability_reuse, chemical_dosing, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry_dict.get('analysis_id', f"AN-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            entry_dict.get('sample_id'),
            entry_dict.get('source'),
            float(entry_dict.get('pH', 0)),
            float(entry_dict.get('TDS', 0)),
            float(entry_dict.get('BOD', 0)),
            float(entry_dict.get('COD', 0)),
            float(entry_dict.get('Turbidity', 0)),
            float(entry_dict.get('EC', 0)),
            float(entry_dict.get('TSS', 0)),
            float(entry_dict.get('Oil_and_Grease', 0)),
            float(entry_dict.get('Temperature', 0)),
            float(entry_dict.get('wqi', 0)),
            entry_dict.get('contamination_level'),
            int(entry_dict.get('predicted_cluster', 0)),
            entry_dict.get('mapped_category'),
            float(entry_dict.get('euclidean_dist_to_centroid', 0)),
            float(entry_dict.get('manhattan_dist_to_centroid', 0)),
            str(entry_dict.get('recommended_stages')),
            str(entry_dict.get('suitability_reuse')),
            str(entry_dict.get('chemical_dosing')),
            entry_dict.get('notes', '')
        ))
        conn.commit()
    finally:
        conn.close()

def get_analysis_history(limit=50):
    """Retrieves recent analysis history."""
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(
            'SELECT * FROM analysis_history ORDER BY id DESC LIMIT ?', 
            conn, 
            params=(limit,)
        )
        return df.to_dict(orient='records')
    finally:
        conn.close()

def clear_all_samples(clear_history=False):
    """Deletes all samples from the database so the user can import a fresh dataset."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM samples')
        if clear_history:
            cursor.execute('DELETE FROM analysis_history')
        conn.commit()
        return True
    finally:
        conn.close()

def auto_classify_pending_samples(classifier_fn):
    """Updates any samples marked 'Pending Lab Confirmation' or missing with an inferred category."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM samples WHERE Lab_Suitability_Category = 'Pending Lab Confirmation' OR Lab_Suitability_Category IS NULL OR Lab_Suitability_Category = ''")
        rows = cursor.fetchall()
        updated_count = 0
        for r in rows:
            sample_dict = dict(r)
            category = classifier_fn(sample_dict)
            cursor.execute("UPDATE samples SET Lab_Suitability_Category = ? WHERE id = ?", (category, r['id']))
            updated_count += 1
        conn.commit()
        return updated_count
    finally:
        conn.close()

def reset_database_to_seed():
    """Resets database to initial seed dataset."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM samples')
        cursor.execute('DELETE FROM analysis_history')
        conn.commit()
        if os.path.exists(SEED_CSV_PATH):
            seed_from_csv(SEED_CSV_PATH, conn)
        return True
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
