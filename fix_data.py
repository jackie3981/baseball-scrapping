"""
Fix 2008 AL Data Contamination
Moves pitching statistics from AL_Player_Hitting_Leaders to AL_Pitcher_Leaders
Fix batting average 1968 NL
"""

import pandas as pd
import os
from datetime import datetime

# =========================
# CONFIGURATION
# =========================
AL_CSV_DIR = os.path.join("CLEANED_CSV", "AL")
HITTING_FILE = os.path.join(AL_CSV_DIR, "AL_Player_Hitting_Leaders.csv")
PITCHER_FILE = os.path.join(AL_CSV_DIR, "AL_Pitcher_Leaders.csv")
BACKUP_DIR = os.path.join("CLEANED_CSV", "AL_BACKUP")
REPORT_FILE = "fix_2008_report.txt"

# Pitching statistics that shouldn't be in hitting file
PITCHING_STATS = [
    'Complete Games',
    'ERA',
    'Games',
    'Saves',
    'Shutouts',
    'Strikeouts',
    'Winning Percentage',
    'Wins'
]

# =========================
# BACKUP FUNCTION
# =========================
def backup_files():
    """Create backup of original files"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Backup hitting file
    df_hitting = pd.read_csv(HITTING_FILE)
    backup_hitting = os.path.join(BACKUP_DIR, f"AL_Player_Hitting_Leaders_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    df_hitting.to_csv(backup_hitting, index=False)
    
    # Backup pitcher file
    df_pitcher = pd.read_csv(PITCHER_FILE)
    backup_pitcher = os.path.join(BACKUP_DIR, f"AL_Pitcher_Leaders_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    df_pitcher.to_csv(backup_pitcher, index=False)
    
    return backup_hitting, backup_pitcher

#==========================
# FIX BATTING AVERAGE
#==========================
def fix_batting_average_decimals():
    """Fix batting averages that are missing the decimal point (e.g., 335 should be 0.335)"""
    print("\nFixing batting average decimal format...")
    
    nl_hitting_file = os.path.join("CLEANED_CSV", "NL", "NL_Player_Hitting_Leaders.csv")
    df = pd.read_csv(nl_hitting_file)
    
    # Find batting averages > 1 (should be 0.xxx)
    mask = (df['Statistic'] == 'Batting Average') & (pd.to_numeric(df['Value'], errors='coerce') > 1)
    
    if mask.any():
        affected = df[mask].copy()
        print(f"   Found {len(affected)} batting averages with missing decimal:")
        
        for idx, row in affected.iterrows():
            old_value = df.at[idx, 'Value']
            # Convert 335 to 0.335
            new_value = float(old_value) / 1000
            df.at[idx, 'Value'] = new_value
            print(f"      {row['Year']} {row['Player_Name']}: {old_value} - {new_value}")
        
        # Save
        df.to_csv(nl_hitting_file, index=False)
        print(f"Fixed and saved to {nl_hitting_file}")
        return len(affected)
    else:
        print("No batting average issues found")
        return 0


# =========================
# MAIN FIX
# =========================
def main():
    print("="*80)
    print("FIX 2008 AL DATA CONTAMINATION")
    print("="*80)
    
    report = []
    report.append("="*80)
    report.append("FIX 2008 AL DATA CONTAMINATION REPORT")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("="*80)
    
    # Check if files exist
    if not os.path.exists(HITTING_FILE):
        print(f"ERROR: {HITTING_FILE} not found")
        return
    
    if not os.path.exists(PITCHER_FILE):
        print(f"ERROR: {PITCHER_FILE} not found")
        return
    
    # Create backup
    print("\nCreating backup...")
    backup_hitting, backup_pitcher = backup_files()
    print(f"Backup created in {BACKUP_DIR}/")
    report.append(f"\nBackup created:")
    report.append(f"   - {backup_hitting}")
    report.append(f"   - {backup_pitcher}")
    
    # Load data
    print("\nLoading data...")
    df_hitting = pd.read_csv(HITTING_FILE)
    df_pitcher = pd.read_csv(PITCHER_FILE)
    
    original_hitting_rows = len(df_hitting)
    original_pitcher_rows = len(df_pitcher)
    
    print(f"   AL_Player_Hitting_Leaders: {original_hitting_rows} rows")
    print(f"   AL_Pitcher_Leaders: {original_pitcher_rows} rows")
    
    report.append(f"\nOriginal row counts:")
    report.append(f"   - AL_Player_Hitting_Leaders: {original_hitting_rows} rows")
    report.append(f"   - AL_Pitcher_Leaders: {original_pitcher_rows} rows")
    
    # Identify contaminated rows
    print("\nIdentifying contaminated rows (Year 2008, pitching stats)...")
    contaminated = df_hitting[
        (df_hitting['Year'] == 2008) & 
        (df_hitting['Statistic'].isin(PITCHING_STATS))
    ]
    
    num_contaminated = len(contaminated)
    print(f"   Found {num_contaminated} contaminated rows")
    
    report.append(f"\nContaminated rows found: {num_contaminated}")
    report.append(f"\n   Statistics found in wrong table:")
    for stat in contaminated['Statistic'].unique():
        count = len(contaminated[contaminated['Statistic'] == stat])
        report.append(f"      - {stat}: {count} rows")
        print(f"      - {stat}: {count} rows")
    
    if num_contaminated == 0:
        print("\nNo contaminated rows found. Data is already clean!")
        report.append("\nNo contaminated rows found. Data is already clean!")
    else:
        # Remove contaminated rows from hitting
        print("\nRemoving contaminated rows from AL_Player_Hitting_Leaders...")
        df_hitting_clean = df_hitting[
            ~((df_hitting['Year'] == 2008) & 
              (df_hitting['Statistic'].isin(PITCHING_STATS)))
        ]
        
        # Add contaminated rows to pitcher file
        print("Adding rows to AL_Pitcher_Leaders...")
        df_pitcher_fixed = pd.concat([df_pitcher, contaminated], ignore_index=True)
        
        # Sort pitcher file by Year, Statistic, Player_Name
        df_pitcher_fixed = df_pitcher_fixed.sort_values(['Year', 'Statistic', 'Player_Name'])
        
        # Save corrected files
        print("\nSaving corrected files...")
        df_hitting_clean.to_csv(HITTING_FILE, index=False)
        df_pitcher_fixed.to_csv(PITCHER_FILE, index=False)
        
        new_hitting_rows = len(df_hitting_clean)
        new_pitcher_rows = len(df_pitcher_fixed)
        
        print(f"AL_Player_Hitting_Leaders: {original_hitting_rows} → {new_hitting_rows} rows (-{original_hitting_rows - new_hitting_rows})")
        print(f"AL_Pitcher_Leaders: {original_pitcher_rows} → {new_pitcher_rows} rows (+{new_pitcher_rows - original_pitcher_rows})")
        
        report.append(f"\nFiles corrected:")
        report.append(f"   - AL_Player_Hitting_Leaders: {original_hitting_rows} → {new_hitting_rows} rows (-{original_hitting_rows - new_hitting_rows})")
        report.append(f"   - AL_Pitcher_Leaders: {original_pitcher_rows} → {new_pitcher_rows} rows (+{new_pitcher_rows - original_pitcher_rows})")
    
    # Verification
    print("\nVerifying fix...")
    df_hitting_verify = pd.read_csv(HITTING_FILE)
    remaining_contaminated = df_hitting_verify[
        (df_hitting_verify['Year'] == 2008) & 
        (df_hitting_verify['Statistic'].isin(PITCHING_STATS))
    ]
    
    if len(remaining_contaminated) == 0:
        print("Verification passed: No pitching stats remain in hitting file")
        report.append("\nVerification: PASSED")
        report.append("   No pitching statistics remain in AL_Player_Hitting_Leaders")
    else:
        print(f"WARNING: {len(remaining_contaminated)} contaminated rows still found!")
        report.append(f"\nVerification: FAILED")
        report.append(f"   {len(remaining_contaminated)} contaminated rows still present")
    
    fix_batting_average_decimals()

    # Summary
    report.append("\n" + "="*80)
    report.append("SUMMARY")
    report.append("="*80)
    report.append(f"Rows moved: {num_contaminated}")
    report.append(f"Status: {'SUCCESS' if len(remaining_contaminated) == 0 else 'NEEDS REVIEW'}")
    report.append("\n" + "="*80)
    report.append("NEXT STEPS:")
    report.append("="*80)
    
    # Save report
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    print(f"\nReport saved to: {REPORT_FILE}")
    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)

if __name__ == "__main__":
    main()