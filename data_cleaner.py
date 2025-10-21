"""
Data Cleaning and Normalization Script
Cleans all CSV files and saves them to CLEANED_CSV folder
After cleaning, automatically runs data quality analysis on cleaned files
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
import re

# =========================
# CONFIGURATION
# =========================
CSV_FOLDERS = {
    "AL": "AL_CSV",
    "NL": "NL_CSV",
    "MINOR": "MINOR_CSV"
}
OUTPUT_BASE = "CLEANED_CSV"
CLEANING_REPORT_FILE = "cleaning_report.txt"

# =========================
# CLEANING FUNCTIONS
# =========================
def clean_special_characters(value):
    """Replace special characters like Ã‚Â½, Â½ with .5"""
    if pd.isna(value):
        return value
    
    value_str = str(value)
    # Replace all variations of 1/2
    value_str = re.sub(r'Â½|½|Ã‚Â½|Ãƒâ€šÃ‚Â½', '.5', value_str)
    return value_str

def clean_placeholder_values(value):
    """Replace '--' with None/NaN"""
    if pd.isna(value):
        return None
    
    value_str = str(value).strip()
    if value_str == '--' or value_str == '':
        return None
    return value

def clean_asterisks(value):
    """Remove asterisks from names"""
    if pd.isna(value):
        return value
    
    return str(value).replace('*', '').strip()

def clean_whitespace(value):
    """Remove leading/trailing whitespace"""
    if pd.isna(value):
        return value
    
    return str(value).strip()

def standardize_decimal_format(value):
    """Standardize decimal format (e.g., .426 → 0.426) and fix comma decimals (,528 → .528)"""
    if pd.isna(value):
        return value
    
    value_str = str(value).strip()
    
    # Replace comma with dot for decimal numbers
    # Only replace if it looks like a decimal number (e.g., ,528 not 1,000)
    if value_str.startswith(',') and len(value_str) > 1:
        value_str = '.' + value_str[1:]
    
    # If starts with a dot, add leading zero
    if value_str.startswith('.') and len(value_str) > 1:
        return '0' + value_str
    
    return value_str

def clean_question_marks(value):
    """Remove question marks from numeric values (e.g., 6? → 6)"""
    if pd.isna(value):
        return value
    
    value_str = str(value).strip()
    # Remove trailing question marks
    if value_str.endswith('?'):
        return value_str[:-1].strip()
    
    return value_str

def convert_to_numeric(series, column_name):
    """Convert a series to numeric type, handling errors gracefully"""
    try:
        # First clean the series
        series = series.apply(clean_placeholder_values)
        series = series.apply(clean_special_characters)
        
        # Try to convert to numeric
        numeric_series = pd.to_numeric(series, errors='coerce')
        return numeric_series
    except:
        return series

# =========================
# FILE CLEANING
# =========================
def clean_csv(filepath, filename, output_folder):
    """
    Clean a single CSV file and save to output folder.
    Shows before/after samples and handles duplicates.
    """
    cleaning_log = []
    cleaning_log.append(f"\n{'='*80}")
    cleaning_log.append(f"CLEANING: {filename}")
    cleaning_log.append(f"{'='*80}")
    
    try:
        # Read CSV
        df = pd.read_csv(filepath)
        original_rows = len(df)
        cleaning_log.append(f"Original rows: {original_rows}")
        
        # Show BEFORE sample (first 3 rows, max 5 columns for readability)
        cleaning_log.append(f"\n--- BEFORE CLEANING (sample: first 3 rows) ---")
        sample_cols = df.columns[:5] if len(df.columns) > 5 else df.columns
        cleaning_log.append(df[sample_cols].head(3).to_string(index=False))
        
        changes_made = []
        
        # 1. Remove completely empty rows
        df_before_empty = len(df)
        df = df.dropna(how='all')
        empty_rows_removed = df_before_empty - len(df)
        if empty_rows_removed > 0:
            changes_made.append(f" Removed {empty_rows_removed} completely empty rows")
        
        # 2. Identify and remove duplicate rows
        key_columns = []
        if 'Year' in df.columns:
            key_columns.append('Year')
        if 'League' in df.columns:
            key_columns.append('League')
        if 'Team' in df.columns:
            key_columns.append('Team')
        if 'Player_Name' in df.columns:
            key_columns.append('Player_Name')
        if 'Statistic' in df.columns:
            key_columns.append('Statistic')
        
        if key_columns:
            df_before_dedup = len(df)
            df = df.drop_duplicates(subset=key_columns, keep='first')
            duplicates_removed = df_before_dedup - len(df)
            if duplicates_removed > 0:
                changes_made.append(f" Removed {duplicates_removed} duplicate rows (based on: {', '.join(key_columns)})")
        
        # 3. Clean special characters in all text columns
        for col in df.columns:
            if df[col].dtype == 'object':
                before = df[col].astype(str).str.contains(r'[Ã‚Â½Â½Ãƒâ€š]', na=False, regex=True).sum()
                if before > 0:
                    df[col] = df[col].apply(clean_special_characters)
                    changes_made.append(f" Cleaned {before} special characters in '{col}'")
        
        # 4. Clean question marks from numeric columns (must be before placeholder cleaning)
        numeric_like_columns = ['Year', 'Wins', 'Losses', 'Ties', 'G', 'AB', 'R', 'H', '2B', '3B', 'HR', 
                                'RBI', 'BB', 'SO', 'SB', 'W', 'L', 'CG', 'SHO', 'SV', 'IP', 'GB', 'Value']
        for col in numeric_like_columns:
            if col in df.columns:
                before = df[col].astype(str).str.contains(r'\?', na=False, regex=True).sum()
                if before > 0:
                    df[col] = df[col].apply(clean_question_marks)
                    changes_made.append(f" Removed question marks from {before} values in '{col}'")
        
        # 5. Replace placeholders with None
        placeholder_count = 0
        for col in df.columns:
            before = (df[col].astype(str).str.strip() == '--').sum()
            if before > 0:
                df[col] = df[col].apply(clean_placeholder_values)
                placeholder_count += before
        if placeholder_count > 0:
            changes_made.append(f" Replaced {placeholder_count} placeholder values ('--') with NULL")
        
        # 6. Remove asterisks from player/team names
        name_columns = [col for col in df.columns if 'Player' in col or 'Name' in col or 'Team' in col]
        for col in name_columns:
            if col in df.columns and df[col].dtype == 'object':
                before = df[col].astype(str).str.contains(r'\*', na=False, regex=True).sum()
                if before > 0:
                    df[col] = df[col].apply(clean_asterisks)
                    changes_made.append(f" Removed asterisks from {before} entries in '{col}'")
        
        # 7. Clean whitespace in all text columns
        whitespace_cleaned = 0
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].apply(clean_whitespace)
                whitespace_cleaned += 1
        if whitespace_cleaned > 0:
            changes_made.append(f" Cleaned whitespace in {whitespace_cleaned} text columns")
        
        # 8. Standardize decimal format
        decimal_columns = [col for col in df.columns if any(x in col for x in ['AVG', 'BA', 'ERA', 'WP', 'OBP', 'SLG', 'PCT'])]
        for col in decimal_columns:
            if col in df.columns:
                df[col] = df[col].apply(standardize_decimal_format)
                changes_made.append(f" Standardized decimal format in '{col}'")
        
        # 9. Convert numeric columns to proper types
        numeric_columns = ['Year', 'Wins', 'Losses', 'Ties', 'G', 'AB', 'R', 'H', '2B', '3B', 'HR', 'RBI', 'BB', 'SO', 'SB', 'W', 'L', 'CG', 'SHO', 'SV', 'IP']
        for col in numeric_columns:
            if col in df.columns:
                original_dtype = df[col].dtype
                df[col] = convert_to_numeric(df[col], col)
                if df[col].dtype != original_dtype:
                    changes_made.append(f" Converted '{col}' to numeric type")
        
        # Decimal numeric columns
        decimal_numeric_columns = ['ERA', 'AVG', 'OBP', 'SLG', 'OPS', 'WP', 'BA', 'PCT', 'GB', 'Value']
        for col in decimal_numeric_columns:
            if col in df.columns:
                original_dtype = df[col].dtype
                df[col] = convert_to_numeric(df[col], col)
                if df[col].dtype != original_dtype:
                    changes_made.append(f" Converted '{col}' to numeric type")
        
        # Save cleaned CSV
        output_path = os.path.join(output_folder, filename)
        df.to_csv(output_path, index=False, encoding='utf-8')
        
        # Show AFTER sample
        cleaning_log.append(f"\n--- AFTER CLEANING (sample: first 3 rows) ---")
        cleaning_log.append(df[sample_cols].head(3).to_string(index=False))
        
        # Summary of changes
        cleaning_log.append(f"\n--- SUMMARY OF CHANGES ---")
        cleaning_log.append(f"Rows before cleaning: {original_rows}")
        cleaning_log.append(f"Rows after cleaning: {len(df)}")
        cleaning_log.append(f"Rows removed: {original_rows - len(df)}")
        
        if changes_made:
            cleaning_log.append(f"\nChanges applied:")
            cleaning_log.extend(changes_made)
        else:
            cleaning_log.append("No changes needed - file was already clean")
        
        cleaning_log.append(f"\nSaved to: {output_path}")
        
    except Exception as e:
        cleaning_log.append(f"ERROR: {str(e)}")
        import traceback
        cleaning_log.append(f"Traceback:\n{traceback.format_exc()}")
    
    return cleaning_log


# =========================
# MAIN CLEANING
# =========================
def main():
    print("="*80)
    print("DATA CLEANING AND NORMALIZATION")
    print("="*80)
    
    all_logs = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    all_logs.append("="*80)
    all_logs.append("BASEBALL DATA CLEANING REPORT")
    all_logs.append(f"Generated: {timestamp}")
    all_logs.append("="*80)
    
    # Create output folders
    for league in CSV_FOLDERS.keys():
        output_folder = os.path.join(OUTPUT_BASE, league)
        os.makedirs(output_folder, exist_ok=True)
        print(f" Created output folder: {output_folder}")
    
    total_files = 0
    successful_files = 0
    
    # Process each folder
    for league, folder in CSV_FOLDERS.items():
        if not os.path.exists(folder):
            all_logs.append(f"\n Folder '{folder}' not found. Skipping...")
            continue
        
        all_logs.append(f"\n\n{'#'*80}")
        all_logs.append(f"# {league} LEAGUE")
        all_logs.append(f"{'#'*80}")
        
        output_folder = os.path.join(OUTPUT_BASE, league)
        
        csv_files = [f for f in os.listdir(folder) if f.endswith('.csv')]
        all_logs.append(f"\nProcessing {len(csv_files)} CSV files from {folder}/")
        
        for csv_file in sorted(csv_files):
            filepath = os.path.join(folder, csv_file)
            file_log = clean_csv(filepath, csv_file, output_folder)
            all_logs.extend(file_log)
            
            total_files += 1
            if " Saved to:" in '\n'.join(file_log):
                successful_files += 1
    
    # Summary
    all_logs.append(f"\n\n{'='*80}")
    all_logs.append("SUMMARY")
    all_logs.append(f"{'='*80}")
    all_logs.append(f"Total files processed: {total_files}")
    all_logs.append(f"Successfully cleaned: {successful_files}")
    all_logs.append(f"Failed: {total_files - successful_files}")
    all_logs.append(f"\nCleaned files saved to: {OUTPUT_BASE}/")
    all_logs.append(f"Report saved to: {CLEANING_REPORT_FILE}")
    all_logs.append("="*80)
    
    # Write report to file
    with open(CLEANING_REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_logs))
    
    # Print to console
    print('\n'.join(all_logs))
    
    print(f"\n Cleaning complete! Report saved to {CLEANING_REPORT_FILE}")
    print(f" Cleaned CSV files available in {OUTPUT_BASE}/")
    
    # =========================
    # AUTOMATIC VALIDATION OF CLEANED FILES
    # =========================
    print("\n" + "="*80)
    print("STARTING AUTOMATIC VALIDATION OF CLEANED FILES")
    print("="*80 + "\n")
    
    # Import and run analyze_data with cleaned folders
    try:
        import analyze_data
        
        # Define cleaned folders
        cleaned_folders = {
            "AL": os.path.join(OUTPUT_BASE, "AL"),
            "NL": os.path.join(OUTPUT_BASE, "NL"),
            "MINOR": os.path.join(OUTPUT_BASE, "MINOR")
        }
        
        # Run analysis on cleaned files
        cleaned_report_file = "data_quality_report_cleaned.txt"
        analyze_data.main(csv_folders=cleaned_folders, report_file=cleaned_report_file)
        
        print(f"\n Validation complete! Results saved to {cleaned_report_file}")
        
    except Exception as e:
        print(f"\n Error during validation: {str(e)}")
        print("You can manually run analyze_data.py on the cleaned files.")

if __name__ == "__main__":
    main()
