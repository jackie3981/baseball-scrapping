"""
Data Quality Analysis Script
Analyzes all CSV files and generates a report of anomalies
"""

import os
import pandas as pd
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
REPORT_FILE = "data_quality_report.txt"

# =========================
# ANALYSIS FUNCTIONS
# =========================
def check_special_characters(df, column_name):
    """Detect special characters like Ã‚Â½, Â½ in a column."""
    issues = []
    if column_name in df.columns:
        special_chars = df[column_name].astype(str).str.contains(r'[Ã‚Â½Â½Ãƒâ€š]', na=False, regex=True)
        if special_chars.any():
            examples = df[special_chars][column_name].head(5).tolist()
            issues.append(f"  - Special characters found in '{column_name}': {examples}")
    return issues

def check_placeholder_values(df, column_name):
    """Detect placeholder values like '--' in numeric columns."""
    issues = []
    if column_name in df.columns:
        placeholders = df[column_name].astype(str).str.strip() == '--'
        if placeholders.any():
            count = placeholders.sum()
            issues.append(f"  - Placeholder '--' found in '{column_name}': {count} occurrences")
    return issues

def check_missing_values(df):
    """Check for missing values in all columns and report affected years."""
    issues = []
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        issues.append(f"  - Missing values detected:")
        for col, count in missing.items():
            percentage = (count / len(df)) * 100
            issues.append(f"    • {col}: {count} ({percentage:.1f}%)")
            
            # If 'Year' column exists, show affected years
            if 'Year' in df.columns:
                affected_years = df[df[col].isnull()]['Year'].dropna().unique()
                if len(affected_years) > 0:
                    affected_years_sorted = sorted([str(int(y)) for y in affected_years])
                    
                    if len(affected_years_sorted) <= 10:
                        years_display = ', '.join(affected_years_sorted)
                    else:
                        years_display = ', '.join(affected_years_sorted[:10]) + f'... ({len(affected_years_sorted) - 10} more)'
                    
                    issues.append(f"      Years affected: {years_display}")
    return issues

def check_asterisks_in_names(df, column_name):
    """Check for asterisks in player/team names."""
    issues = []
    if column_name in df.columns:
        asterisks = df[column_name].astype(str).str.contains(r'\*', na=False, regex=True)
        if asterisks.any():
            count = asterisks.sum()
            examples = df[asterisks][column_name].head(3).tolist()
            issues.append(f"  - Asterisks found in '{column_name}': {count} occurrences")
            issues.append(f"    Examples: {examples}")
    return issues

def check_whitespace(df, column_name):
    """Check for leading/trailing whitespace in text columns."""
    issues = []
    if column_name in df.columns and df[column_name].dtype == 'object':
        has_whitespace = df[column_name].astype(str).str.strip() != df[column_name].astype(str)
        if has_whitespace.any():
            count = has_whitespace.sum()
            issues.append(f"  - Leading/trailing whitespace in '{column_name}': {count} occurrences")
    return issues

def check_numeric_as_string(df, column_name):
    """Check if numeric columns are stored as strings."""
    issues = []
    if column_name in df.columns:
        if df[column_name].dtype == 'object':
            # Try to convert to numeric
            try:
                pd.to_numeric(df[column_name], errors='coerce')
                issues.append(f"  - '{column_name}' is stored as text but contains numeric values")
            except:
                pass
    return issues

def check_value_ranges(df, column_name, min_val=None, max_val=None):
    """Check if values are within expected ranges."""
    issues = []
    if column_name in df.columns:
        try:
            numeric_col = pd.to_numeric(df[column_name], errors='coerce')
            if min_val is not None:
                below_min = numeric_col < min_val
                if below_min.any():
                    count = below_min.sum()
                    issues.append(f"  - '{column_name}' has {count} values below minimum ({min_val})")
            if max_val is not None:
                above_max = numeric_col > max_val
                if above_max.any():
                    count = above_max.sum()
                    issues.append(f"  - '{column_name}' has {count} values above maximum ({max_val})")
        except:
            pass
    return issues

def check_decimal_format(df, column_name):
    """Check for inconsistent decimal formats."""
    issues = []
    if column_name in df.columns:
        # Look for values like ".426" vs "0.426"
        values_str = df[column_name].astype(str)
        starts_with_dot = values_str.str.match(r'^\.\d+', na=False)
        if starts_with_dot.any():
            count = starts_with_dot.sum()
            issues.append(f"  - '{column_name}' has {count} values starting with '.' (e.g., '.426' instead of '0.426')")
    return issues

# =========================
# FILE ANALYSIS
# =========================
def analyze_csv(filepath, filename):
    """Analyze a single CSV file for data quality issues."""
    issues = []
    
    try:
        df = pd.read_csv(filepath)
        issues.append(f"\n{'='*80}")
        issues.append(f"FILE: {filename}")
        issues.append(f"{'='*80}")
        issues.append(f"Total rows: {len(df)}")
        issues.append(f"Columns: {list(df.columns)}")
        
        # Check for missing values
        missing_issues = check_missing_values(df)
        if missing_issues:
            issues.extend(missing_issues)
        
        # Check specific columns based on file type
        for col in df.columns:
            # Special characters (mainly in GB column)
            if 'GB' in col or 'Games Behind' in col:
                issues.extend(check_special_characters(df, col))
            
            # Placeholder values
            issues.extend(check_placeholder_values(df, col))
            
            # Asterisks in names
            if 'Player' in col or 'Name' in col:
                issues.extend(check_asterisks_in_names(df, col))
            
            # Whitespace
            if df[col].dtype == 'object':
                issues.extend(check_whitespace(df, col))
            
            # Numeric as string
            if col in ['Year', 'Wins', 'Losses', 'Value', 'HR', 'RBI', 'G', 'AB', 'R', 'H']:
                issues.extend(check_numeric_as_string(df, col))
            
            # Decimal format
            if 'AVG' in col or 'BA' in col or 'ERA' in col or 'WP' in col or 'OBP' in col or 'SLG' in col:
                issues.extend(check_decimal_format(df, col))
        
        # Value range checks
        issues.extend(check_value_ranges(df, 'Year', min_val=1800, max_val=2030))
        
        # Batting average should be between 0 and 1
        for col in df.columns:
            if 'AVG' in col or 'BA' in col:
                issues.extend(check_value_ranges(df, col, min_val=0, max_val=1))
        
        # ERA should be >= 0
        if 'ERA' in df.columns:
            issues.extend(check_value_ranges(df, 'ERA', min_val=0))
        
        if len(issues) == 5:  # Only header info, no issues found
            issues.append("No data quality issues detected")
        
    except Exception as e:
        issues.append(f"\n{'='*80}")
        issues.append(f"FILE: {filename}")
        issues.append(f"{'='*80}")
        issues.append(f"ERROR reading file: {str(e)}")
    
    return issues

# =========================
# MAIN ANALYSIS
# =========================
def main(csv_folders=None, report_file=None):
    """
    Main analysis function.
    
    Args:
        csv_folders: Dictionary with league names as keys and folder paths as values
        report_file: Path to the report file
    """
    # Use provided parameters or defaults
    folders = csv_folders if csv_folders is not None else CSV_FOLDERS
    report = report_file if report_file is not None else REPORT_FILE
    
    print("="*80)
    print("DATA QUALITY ANALYSIS")
    print("="*80)
    
    all_issues = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    all_issues.append("="*80)
    all_issues.append("BASEBALL DATA QUALITY REPORT")
    all_issues.append(f"Generated: {timestamp}")
    all_issues.append("="*80)
    
    total_files = 0
    files_with_issues = 0
    
    # Analyze each folder
    for league, folder in folders.items():
        if not os.path.exists(folder):
            all_issues.append(f"\n Folder '{folder}' not found. Skipping...")
            continue
        
        all_issues.append(f"\n\n{'#'*80}")
        all_issues.append(f"# {league} LEAGUE")
        all_issues.append(f"{'#'*80}")
        
        csv_files = [f for f in os.listdir(folder) if f.endswith('.csv')]
        all_issues.append(f"\nFound {len(csv_files)} CSV files in {folder}/")
        
        for csv_file in sorted(csv_files):
            filepath = os.path.join(folder, csv_file)
            file_issues = analyze_csv(filepath, csv_file)
            all_issues.extend(file_issues)
            
            total_files += 1
            # Check if file has issues (more than just header info)
            if len(file_issues) > 5:
                files_with_issues += 1
    
    # Summary
    all_issues.append(f"\n\n{'='*80}")
    all_issues.append("SUMMARY")
    all_issues.append(f"{'='*80}")
    all_issues.append(f"Total files analyzed: {total_files}")
    all_issues.append(f"Files with issues: {files_with_issues}")
    all_issues.append(f"Files clean: {total_files - files_with_issues}")
    all_issues.append(f"\nReport saved to: {report}")
    all_issues.append("="*80)
    
    # Write report to file
    with open(report, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_issues))
    
    # Print to console
    print('\n'.join(all_issues))
    
    print(f"\nAnalysis complete! Report saved to {report}")

if __name__ == "__main__":
    main()
