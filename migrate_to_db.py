"""
Database Migration Script
Migrates cleaned CSV files to SQLite database with data type enforcement and validation
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime

# =========================
# CONFIGURATION
# =========================
CLEANED_CSV_BASE = "CLEANED_CSV"
CSV_FOLDERS = {
    "AL": os.path.join(CLEANED_CSV_BASE, "AL"),
    "NL": os.path.join(CLEANED_CSV_BASE, "NL"),
    "MINOR": os.path.join(CLEANED_CSV_BASE, "MINOR")
}
DATABASE_FILE = "baseball_stats.db"
MIGRATION_REPORT_FILE = "migration_report.txt"

# =========================
# DATA TYPE MAPPINGS
# =========================
def get_dtype_mapping(table_name):
    """Get SQLite data type mapping for specific table"""
    
    # Common numeric columns across all tables
    common_dtypes = {
        'Year': 'INTEGER',
        'Wins': 'INTEGER',
        'Losses': 'INTEGER',
        'W': 'INTEGER',
        'L': 'INTEGER',
        'Ties': 'INTEGER',
        'G': 'INTEGER',
        'AB': 'INTEGER',
        'R': 'INTEGER',
        'H': 'INTEGER',
        '2B': 'INTEGER',
        '3B': 'INTEGER',
        'HR': 'INTEGER',
        'RBI': 'INTEGER',
        'TB': 'INTEGER',
        'BB': 'INTEGER',
        'SO': 'INTEGER',
        'SB': 'INTEGER',
        'CS': 'INTEGER',
        'CG': 'INTEGER',
        'SHO': 'INTEGER',
        'SV': 'INTEGER',
        'SVO': 'INTEGER',
        'HA': 'INTEGER',
        'ER': 'INTEGER',
        'HBP': 'INTEGER',
        'ERA': 'REAL',
        'WP': 'REAL',
        'OBP': 'REAL',
        'SLG': 'REAL',
        'AVG': 'REAL',
        'OPS': 'REAL',
        'BA': 'REAL',
        'PCT': 'REAL',
        'GB': 'REAL',
        'IP': 'REAL',
        'Payroll': 'REAL'
    }
    
    # For Leader tables, Value can be either INTEGER or REAL
    if 'Leaders' in table_name or 'Leader' in table_name:
        common_dtypes['Value'] = 'REAL'  
    
    return common_dtypes

# =========================
# INDEX CREATION
# =========================
def create_indexes(conn, table_name, df):
    """Create indexes on key columns for faster queries"""
    cursor = conn.cursor()
    indexes_created = []
    
    # Index on Year (if exists)
    if 'Year' in df.columns:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_year ON {table_name}(Year)")
            indexes_created.append("Year")
        except:
            pass
    
    # Index on League (if exists)
    if 'League' in df.columns:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_league ON {table_name}(League)")
            indexes_created.append("League")
        except:
            pass
    
    # Index on Player_Name (if exists)
    if 'Player_Name' in df.columns:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_player ON {table_name}(Player_Name)")
            indexes_created.append("Player_Name")
        except:
            pass
    
    # Index on Team (if exists)
    if 'Team' in df.columns:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_team ON {table_name}(Team)")
            indexes_created.append("Team")
        except:
            pass
    
    # Index on Statistic (if exists) - for Leader tables
    if 'Statistic' in df.columns:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_statistic ON {table_name}(Statistic)")
            indexes_created.append("Statistic")
        except:
            pass
    
    # Composite index on Year + League (if both exist)
    if 'Year' in df.columns and 'League' in df.columns:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_year_league ON {table_name}(Year, League)")
            indexes_created.append("Year+League")
        except:
            pass
    
    # Composite index on Year + Team (if both exist)
    if 'Year' in df.columns and 'Team' in df.columns:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_year_team ON {table_name}(Year, Team)")
            indexes_created.append("Year+Team")
        except:
            pass
    
    # Composite index on Year + Statistic (for Leader tables)
    if 'Year' in df.columns and 'Statistic' in df.columns:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_year_stat ON {table_name}(Year, Statistic)")
            indexes_created.append("Year+Statistic")
        except:
            pass
    
    conn.commit()
    return indexes_created

# =========================
# NULL VERIFICATION
# =========================
def verify_nulls(conn, table_name, df):
    """Verify NULL values in table and return report"""
    cursor = conn.cursor()
    null_report = []
    
    for col in df.columns:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {col} IS NULL")
            null_count = cursor.fetchone()[0]
            
            if null_count > 0:
                total_rows = len(df)
                percentage = (null_count / total_rows) * 100
                null_report.append(f"    • {col}: {null_count} NULLs ({percentage:.1f}%)")
        except:
            pass
    
    return null_report

# =========================
# DATA VALIDATION
# =========================
def validate_data(conn, table_name):
    """Perform specific data validations after migration"""
    cursor = conn.cursor()
    validations = []
    
    try:
        # Validation 1: Check "Data Not Kept" has NULL values
        if 'Player_Name' in [col[1] for col in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()]:
            cursor.execute(f"""
                SELECT COUNT(*) FROM {table_name} 
                WHERE Player_Name = 'Data Not Kept' AND Value IS NOT NULL
            """)
            data_not_kept_with_value = cursor.fetchone()[0]
            
            if data_not_kept_with_value > 0:
                validations.append(f" WARNING: {data_not_kept_with_value} 'Data Not Kept' rows have non-NULL Value")
            else:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {table_name} 
                    WHERE Player_Name = 'Data Not Kept'
                """)
                data_not_kept_count = cursor.fetchone()[0]
                if data_not_kept_count > 0:
                    validations.append(f" {data_not_kept_count} 'Data Not Kept' rows correctly have NULL Value")
        
        # Validation 2: Check Team_Pitching_Complete for years 2002-2004
        if 'Team_Pitching_Complete' in table_name:
            # Check 2002: G should be NULL
            cursor.execute(f"""
                SELECT COUNT(*) FROM {table_name} 
                WHERE Year = 2002 AND G IS NULL
            """)
            null_g_2002 = cursor.fetchone()[0]
            
            if null_g_2002 > 0:
                validations.append(f" Year 2002: {null_g_2002} teams with G = NULL (expected)")
            
            # Check 2003: SVO should be NULL
            cursor.execute(f"""
                SELECT COUNT(*) FROM {table_name} 
                WHERE Year = 2003 AND SVO IS NULL
            """)
            null_svo_2003 = cursor.fetchone()[0]
            
            if null_svo_2003 > 0:
                validations.append(f" Year 2003: {null_svo_2003} teams with SVO = NULL (expected)")
            
            # Check 2004: Both G and SVO should be NULL (AL only)
            if 'AL' in table_name:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {table_name} 
                    WHERE Year = 2004 AND G IS NULL AND SVO IS NULL
                """)
                null_both_2004 = cursor.fetchone()[0]
                
                if null_both_2004 > 0:
                    validations.append(f" Year 2004: {null_both_2004} teams with G and SVO = NULL (expected)")
        
        # Validation 3: Check Team_Standings for NL 2013 GB issue
        if 'Team_Standings' in table_name:
            cursor.execute(f"""
                SELECT COUNT(*) FROM {table_name} 
                WHERE Year = 2013 AND League = 'NL' AND Team LIKE '%Cubs%' AND GB IS NOT NULL
            """)
            nl_2013_gb = cursor.fetchone()[0]
            
            if nl_2013_gb > 0:
                validations.append(f" NL 2013 Cubs: GB has value (typo fixed)")
    
    except Exception as e:
        validations.append(f" Validation error: {str(e)}")
    
    return validations

# =========================
# MIGRATION FUNCTION
# =========================
def migrate_csv_to_db(conn, filepath, filename):
    """Migrate a single CSV file to database with type enforcement"""
    migration_log = []
    migration_log.append(f"\n{'='*80}")
    migration_log.append(f"MIGRATING: {filename}")
    migration_log.append(f"{'='*80}")
    
    try:
        # Read CSV with proper handling
        df = pd.read_csv(filepath, encoding='utf-8', na_values=['', 'NA', 'N/A'])
        original_rows = len(df)
        
        # Table name = filename without .csv extension
        table_name = filename.replace('.csv', '')
        
        migration_log.append(f"Source: {filepath}")
        migration_log.append(f"Target table: {table_name}")
        migration_log.append(f"Rows to insert: {original_rows}")
        migration_log.append(f"Columns: {list(df.columns)}")
        
        # Get data type mapping for this table
        dtype_mapping = get_dtype_mapping(table_name)
        
        # Filter to only include columns that exist in the dataframe
        filtered_dtypes = {col: dtype for col, dtype in dtype_mapping.items() if col in df.columns}
        
        if filtered_dtypes:
            migration_log.append(f"Enforcing data types for {len(filtered_dtypes)} columns")
        
        # Insert data into database with type enforcement
        df.to_sql(table_name, conn, if_exists='replace', index=False, dtype=filtered_dtypes)
        
        # Verify insertion
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        inserted_rows = cursor.fetchone()[0]
        
        migration_log.append(f"Successfully inserted {inserted_rows} rows")
        
        # Create indexes
        indexes = create_indexes(conn, table_name, df)
        if indexes:
            migration_log.append(f"Created indexes on: {', '.join(indexes)}")
        
        # Get table structure
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        migration_log.append(f"Table structure:")
        for col_info in columns_info:
            col_name = col_info[1]
            col_type = col_info[2]
            migration_log.append(f"  - {col_name}: {col_type}")
        
        # Verify NULLs
        null_report = verify_nulls(conn, table_name, df)
        if null_report:
            migration_log.append(f"NULL values found:")
            migration_log.extend(null_report)
        else:
            migration_log.append(f"No NULL values in table")
        
        # Validate data
        validation_report = validate_data(conn, table_name)
        if validation_report:
            migration_log.append(f"Data validation:")
            migration_log.extend(validation_report)
        
        return migration_log, True, inserted_rows
        
    except Exception as e:
        migration_log.append(f"ERROR: {str(e)}")
        import traceback
        migration_log.append(f"Traceback: {traceback.format_exc()}")
        return migration_log, False, 0

# =========================
# MAIN MIGRATION
# =========================
def main():
    print("="*80)
    print("DATABASE MIGRATION WITH VALIDATION")
    print("="*80)
    
    all_logs = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    all_logs.append("="*80)
    all_logs.append("BASEBALL DATABASE MIGRATION REPORT")
    all_logs.append(f"Generated: {timestamp}")
    all_logs.append(f"Database: {DATABASE_FILE}")
    all_logs.append("="*80)
    
    # Check if cleaned CSV folders exist
    if not os.path.exists(CLEANED_CSV_BASE):
        print(f"Error: {CLEANED_CSV_BASE} folder not found!")
        print("Please run data_cleaner.py first to generate cleaned CSV files.")
        return
    
    # Remove existing database if it exists
    if os.path.exists(DATABASE_FILE):
        os.remove(DATABASE_FILE)
        print(f"Removed existing database: {DATABASE_FILE}")
        all_logs.append(f"\nℹ Removed existing database")
    
    # Create database connection
    conn = sqlite3.connect(DATABASE_FILE)
    print(f"Created database: {DATABASE_FILE}")
    all_logs.append(f"\nCreated new database: {DATABASE_FILE}")
    
    total_files = 0
    successful_files = 0
    total_rows = 0
    
    # Process each folder
    for league, folder in CSV_FOLDERS.items():
        if not os.path.exists(folder):
            all_logs.append(f"\nFolder '{folder}' not found. Skipping...")
            continue
        
        all_logs.append(f"\n\n{'#'*80}")
        all_logs.append(f"# {league} LEAGUE")
        all_logs.append(f"{'#'*80}")
        
        csv_files = [f for f in os.listdir(folder) if f.endswith('.csv')]
        all_logs.append(f"\nProcessing {len(csv_files)} CSV files from {folder}/")
        
        for csv_file in sorted(csv_files):
            filepath = os.path.join(folder, csv_file)
            file_log, success, rows = migrate_csv_to_db(conn, filepath, csv_file)
            all_logs.extend(file_log)
            
            total_files += 1
            if success:
                successful_files += 1
                total_rows += rows
    
    # Close database connection
    conn.close()
    
    # Get database size
    db_size = os.path.getsize(DATABASE_FILE) / (1024 * 1024)  # Size in MB
    
    # Get table count
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    table_count = len(tables)
    
    # Get index count
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = cursor.fetchall()
    index_count = len(indexes)
    
    conn.close()
    
    # Summary
    all_logs.append(f"\n\n{'='*80}")
    all_logs.append("SUMMARY")
    all_logs.append(f"{'='*80}")
    all_logs.append(f"CSV files processed: {total_files}")
    all_logs.append(f"Successfully migrated: {successful_files}")
    all_logs.append(f"Failed: {total_files - successful_files}")
    all_logs.append(f"Total rows inserted: {total_rows:,}")
    all_logs.append(f"Tables created: {table_count}")
    all_logs.append(f"Indexes created: {index_count}")
    all_logs.append(f"Database size: {db_size:.2f} MB")
    all_logs.append(f"\nDatabase file: {DATABASE_FILE}")
    all_logs.append(f"Report saved to: {MIGRATION_REPORT_FILE}")
    all_logs.append("="*80)
    
    # List all tables
    all_logs.append(f"\n\nTABLES IN DATABASE:")
    all_logs.append(f"{'-'*80}")
    for idx, table in enumerate(sorted(tables), 1):
        all_logs.append(f"{idx:2d}. {table[0]}")
    
    # Write report to file
    with open(MIGRATION_REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_logs))
    
    # Print to console
    print('\n'.join(all_logs))
    
    print(f"\n Migration complete!")
    print(f" Database: {DATABASE_FILE}")
    print(f" Tables: {table_count}")
    print(f" Total rows: {total_rows:,}")
    print(f" Report: {MIGRATION_REPORT_FILE}")

if __name__ == "__main__":
    main()