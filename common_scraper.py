"""
Common Baseball Scraper Module
Shared functions for scraping baseball statistics
"""

import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd

# =========================
# CONSTANTS
# =========================
PAGE_DELAY = 0.5

# =========================
# LOGGING FUNCTIONS
# =========================
def log_message(message, log_file, level="INFO"):
    """Write log message to file and console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

# =========================
# FILE MANAGEMENT
# =========================
def ensure_directory(directory):
    """Create directory if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)

# =========================
# DRIVER SETUP
# =========================
def setup_driver():
    """Setup Chrome driver with headless configuration."""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920x1080')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--log-level=3')
    options.add_argument('--disable-logging')
    options.add_argument('--disable-web-security')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

# =========================
# EXTRACTION OF LEAGUES AND YEARS
# =========================
def extract_league_years(driver, url, log_file):
    """Extract all leagues and their years from the main page."""
    driver.get(url)
    wait = WebDriverWait(driver, 15)
    banner_cells = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//td[@class='banner']")))
    
    leagues_data = {}
    for banner in banner_cells:
        table_name = banner.text.strip()
        if table_name == "Year-by-Year Baseball History" or table_name in leagues_data:
            continue
        
        try:
            parent_tr = banner.find_element(By.XPATH, "..")
            data_tr = parent_tr.find_element(By.XPATH, "following-sibling::tr[td[@class='datacolBox']]")
            sub_table = data_tr.find_element(By.XPATH, ".//table[@class='ba-sub']")
            rows = sub_table.find_elements(By.TAG_NAME, "tr")
            
            years_info = []
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                for cell in cells:
                    cell_text = cell.text.strip()
                    if cell_text and cell_text != "0000" and "grey" not in cell.get_attribute("class").split():
                        try:
                            link = cell.find_element(By.TAG_NAME, "a").get_attribute("href")
                        except:
                            link = None
                        years_info.append({"year": cell_text, "url": link})
            
            leagues_data[table_name] = years_info
            log_message(f"{table_name}: {len(years_info)} years found", log_file)
        except Exception as e:
            log_message(f"Error processing '{table_name}': {str(e)}", log_file, "ERROR")
            leagues_data[table_name] = []
    
    return leagues_data

# =========================
# EXTRACT PLAYER/PITCHER LEADERS
# =========================
def extract_player_leaders(ba_table, year, league, log_file):
    """Extract player or pitcher leader statistics from a table."""
    data = []
    
    try:
        rows = ba_table.find_elements(By.XPATH, ".//tr")
        current_statistic = None
        current_value = None
        current_player = None
        
        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if not cells:
                    continue
                
                first_cell_class = cells[0].get_attribute("class")
                if "grey" in first_cell_class or "grey" in row.get_attribute("class"):
                    continue
                
                if "banner" in first_cell_class or "header" in first_cell_class:
                    continue
                
                num_cells = len(cells)
                
                if num_cells >= 5 and "datacolBlue" in first_cell_class:
                    current_statistic = cells[0].text.strip()
                    player_name = cells[1].text.strip()
                    team = cells[2].text.strip()
                    current_value = cells[3].text.strip()
                    
                    player_name = player_name.replace('*', '').strip()
                    
                    player_rowspan = cells[1].get_attribute("rowspan")
                    if player_rowspan and int(player_rowspan) > 1:
                        current_player = player_name
                    else:
                        current_player = None
                    
                    data.append({
                        "Year": year,
                        "League": league,
                        "Statistic": current_statistic,
                        "Player_Name": player_name,
                        "Team": team,
                        "Value": current_value
                    })
                
                elif num_cells == 2 and current_statistic and current_value:
                    player_name = cells[0].text.strip()
                    team = cells[1].text.strip()
                    player_name = player_name.replace('*', '').strip()
                    
                    data.append({
                        "Year": year,
                        "League": league,
                        "Statistic": current_statistic,
                        "Player_Name": player_name,
                        "Team": team,
                        "Value": current_value
                    })
                
                elif num_cells == 1 and current_player and current_statistic:
                    team = cells[0].text.strip()
                    
                    data.append({
                        "Year": year,
                        "League": league,
                        "Statistic": current_statistic,
                        "Player_Name": current_player,
                        "Team": team,
                        "Value": current_value
                    })
                
                elif num_cells == 3 and current_statistic:
                    player_name = cells[0].text.strip()
                    team = cells[1].text.strip()
                    value = cells[2].text.strip()
                    player_name = player_name.replace('*', '').strip()
                    
                    data.append({
                        "Year": year,
                        "League": league,
                        "Statistic": current_statistic,
                        "Player_Name": player_name,
                        "Team": team,
                        "Value": value
                    })
                
            except Exception as e:
                continue
    
    except Exception as e:
        log_message(f"Error extracting player leaders: {str(e)}", log_file, "ERROR")
    
    return data

# =========================
# EXTRACT TEAM STANDINGS
# =========================
def extract_team_standings(ba_table, year, league, log_file):
    """Extract team standings from a table."""
    data = []
    
    try:
        rows = ba_table.find_elements(By.XPATH, ".//tr")
        current_division = "Standard"
        
        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                
                if not cells:
                    continue
                
                first_cell_class = cells[0].get_attribute("class")
                first_cell_text = cells[0].text.strip()
                first_cell_rowspan = cells[0].get_attribute("rowspan")
                
                # Check if this is a division header (East/Central/West)
                if first_cell_rowspan and first_cell_text in ["East", "Central", "West"]:
                    current_division = first_cell_text
                    continue
                
                # Skip banner/header rows
                if "banner" in first_cell_class or "header" in first_cell_class:
                    continue
                
                # Try to get team name from link
                team_name = None
                try:
                    link = cells[0].find_element(By.TAG_NAME, "a")
                    team_name = link.text.strip()
                    
                    # Skip All-Star and World Series links
                    if "All-Star" in team_name or "World Series" in team_name:
                        continue
                except:
                    continue
                
                if not team_name:
                    continue
                
                # =========================
                # DETECT SPLIT COLUMNS 
                # =========================
                # Years with split columns: AL 1981, NL 1892, NL 1981
                # These have an extra column after Team with values like:
                # - "Final", "1st Half", "2nd Half" (1981)
                # - "(a)", "(b)", "Final" (1892)
                
                offset = 0
                skip_row = False
                
                if len(cells) > 1:
                    second_cell_text = cells[1].text.strip()
                    
                    # Check if this is a split column
                    split_indicators = ["Final", "1st Half", "2nd Half", "(a)", "(b)"]
                    
                    if second_cell_text in split_indicators:
                        offset = 1  # Skip the split column
                        
                        # Only process "Final" rows - skip partial season rows
                        if second_cell_text != "Final":
                            skip_row = True
                
                if skip_row:
                    continue
                
                # =========================
                # EXTRACT DATA WITH OFFSET
                # =========================
                wins = None
                losses = None
                ties = None
                wp = None
                gb = None
                payroll = None
                
                num_cells = len(cells)
                
                # Adjust all indices by offset
                if num_cells >= 5 + offset:
                    wins = cells[1 + offset].text.strip()
                    losses = cells[2 + offset].text.strip()
                    
                    # Check if there's a Ties column (older years)
                    # If cells[3+offset] contains a number between 0-20 and next cell is a decimal (WP), it's likely Ties
                    if num_cells >= 7 + offset:
                        third_cell = cells[3 + offset].text.strip()
                        fourth_cell = cells[4 + offset].text.strip()
                        
                        # Try to determine if third_cell is Ties or WP
                        try:
                            third_val = float(third_cell) if third_cell else 0
                            fourth_val = float(fourth_cell) if fourth_cell else 0
                            
                            # If fourth cell looks like WP (0.xxx), then third is Ties
                            if 0 <= fourth_val <= 1 and '.' in fourth_cell:
                                ties = third_cell if third_cell and third_cell != '0' else None
                                wp = fourth_cell
                                gb = cells[5 + offset].text.strip()
                                
                                # Check for payroll in next column
                                if num_cells >= 7 + offset:
                                    payroll_text = cells[6 + offset].text.strip()
                                    if payroll_text.startswith('$'):
                                        payroll = payroll_text.replace('$', '').replace(',', '').strip()
                            else:
                                # No Ties column
                                ties = None
                                wp = third_cell
                                gb = fourth_cell
                                
                                if num_cells >= 6 + offset:
                                    payroll_text = cells[5 + offset].text.strip()
                                    if payroll_text.startswith('$'):
                                        payroll = payroll_text.replace('$', '').replace(',', '').strip()
                        except:
                            # Fallback to simple mapping without Ties
                            wp = third_cell
                            gb = fourth_cell
                    else:
                        # Simple case: only W, L, WP, GB
                        wp = cells[3 + offset].text.strip()
                        gb = cells[4 + offset].text.strip()
                
                # Clean GB value (handle special characters for .5)
                if gb == '--':
                    gb = '0'
                elif gb and 'Ãƒâ€šÃ‚Â½' in gb:
                    gb = gb.replace('Ãƒâ€šÃ‚Â½', '.5')
                elif gb and 'Â½' in gb:
                    gb = gb.replace('Â½', '.5')
                elif gb and ',' in gb:
                    gb = gb.replace(',', '.')
                
                # Convert empty strings to None
                if not wins:
                    wins = None
                if not losses:
                    losses = None
                if not ties or ties == '0':
                    ties = None
                if not wp:
                    wp = None
                if not gb:
                    gb = None
                if not payroll:
                    payroll = None
                
                data.append({
                    "Year": year,
                    "League": league,
                    "Division": current_division,
                    "Team": team_name,
                    "Wins": wins,
                    "Losses": losses,
                    "Ties": ties,
                    "WP": wp,
                    "GB": gb,
                    "Payroll": payroll
                })
                
            except Exception as e:
                log_message(f"Error processing row in team standings: {str(e)}", log_file, "DEBUG")
                continue
    
    except Exception as e:
        log_message(f"Error extracting team standings: {str(e)}", log_file, "ERROR")
    
    return data


# =========================
# EXTRACT TEAM LEADERS (VERTICAL FORMAT)
# =========================
def extract_team_leaders(ba_table, year, league, stats_type, log_file):
    """Extract team leader statistics in vertical format (older years)."""
    data = []
    
    try:
        rows = ba_table.find_elements(By.XPATH, ".//tr")
        
        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                
                if not cells or len(cells) < 3:
                    continue
                
                first_cell_class = cells[0].get_attribute("class")
                
                if "banner" in first_cell_class or "header" in first_cell_class:
                    continue
                
                if "datacolBlue" in first_cell_class:
                    statistic = cells[0].text.strip()
                    team = cells[1].text.strip()
                    value = cells[2].text.strip()
                    
                    if value:
                        value = value.replace(',', '')
                    
                    if statistic and team and value:
                        data.append({
                            "Year": year,
                            "League": league,
                            "Statistic": statistic,
                            "Team": team,
                            "Value": value
                        })
                
            except Exception as e:
                continue
    
    except Exception as e:
        log_message(f"Error extracting team {stats_type} leaders: {str(e)}", log_file, "ERROR")
    
    return data

# =========================
# EXTRACT TEAM STATS COMPLETE (HORIZONTAL FORMAT)
# =========================
def extract_team_stats_complete(ba_table, year, league, stats_type, log_file):
    """Extract complete team statistics (horizontal format - modern years)."""
    data = []
    
    try:
        # Try to find header row
        try:
            header_row = ba_table.find_element(By.XPATH, ".//tr[td[@class='banner']]")
            header_cells = header_row.find_elements(By.TAG_NAME, "td")
        except Exception as e:
            return data
        
        # Extract column names from HTML
        html_columns = []
        for cell in header_cells:
            col_name = cell.text.strip()
            if col_name:
                html_columns.append(col_name)
        
        if not html_columns:
            return data
        
        # =========================
        # SPECIAL HANDLING FOR PITCHING STATS 2002-2004
        # =========================
        if stats_type == "Pitching" and year in ["2002", "2003", "2004"]:
            # Define ALL expected columns IN THE CORRECT ORDER
            EXPECTED_COLUMNS = ['TEAM', 'W', 'L', 'ERA', 'G', 'CG', 'SHO', 'SV', 'SVO', 
                               'IP', 'HA', 'R', 'ER', 'HR', 'HBP', 'BB', 'SO']
            
            # Column name normalization mapping
            COLUMN_MAPPING = {
                'H': 'HA',       # 2002 AL/NL uses 'H' instead of 'HA'
                'SH': 'SHO',     # 2002/2004 AL uses 'SH' instead of 'SHO'
                'Team': 'TEAM',  # Normalize to uppercase
                'TEAM': 'TEAM'
            }
            
            # Normalize HTML column names
            normalized_html_columns = []
            for col in html_columns:
                normalized_col = COLUMN_MAPPING.get(col, col)
                normalized_html_columns.append(normalized_col)
            
            log_message(f"Year {year} {league} - HTML columns: {normalized_html_columns}", log_file, "DEBUG")
            log_message(f"Year {year} {league} - Expected columns: {EXPECTED_COLUMNS}", log_file, "DEBUG")
            
            # Create a mapping from HTML column name to cell index
            html_col_to_index = {}
            for idx, col_name in enumerate(normalized_html_columns):
                html_col_to_index[col_name] = idx
            
            log_message(f"Year {year} {league} - Column mapping: {html_col_to_index}", log_file, "DEBUG")
        else:
            # For other years, use normal processing
            EXPECTED_COLUMNS = None
            COLUMN_MAPPING = {}
            normalized_html_columns = html_columns
            html_col_to_index = {}
        
        # =========================
        # EXTRACT DATA ROWS
        # =========================
        rows = ba_table.find_elements(By.XPATH, ".//tr")
        
        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                
                if not cells or len(cells) < 3:
                    continue
                
                first_cell_class = cells[0].get_attribute("class")
                
                if "banner" in first_cell_class or "header" in first_cell_class:
                    continue
                
                # Try to find link first, fallback to text
                team_name = None
                try:
                    link = cells[0].find_element(By.TAG_NAME, "a")
                    team_name = link.text.strip()
                except:
                    team_name = cells[0].text.strip()

                if not team_name or team_name == "":
                    continue

                if "All-Star" in team_name or "World Series" in team_name or "Seasonal Events" in team_name:
                    continue
                
                row_data = {
                    "Year": year,
                    "League": league,
                    "Team": team_name
                }
                
                # =========================
                # MAP CELLS TO COLUMNS
                # =========================
                if EXPECTED_COLUMNS:
                    # Special handling for 2002-2004 Pitching
                    # Use intelligent mapping based on column names, not positions
                    
                    for expected_col in EXPECTED_COLUMNS:
                        if expected_col == 'TEAM':
                            continue  # Already set
                        
                        # Check if this column exists in the HTML
                        if expected_col in html_col_to_index:
                            cell_idx = html_col_to_index[expected_col]
                            
                            if cell_idx < len(cells):
                                value = cells[cell_idx].text.strip()
                                
                                if value:
                                    value = value.replace(',', '')
                                
                                row_data[expected_col] = value
                            else:
                                row_data[expected_col] = None
                        else:
                            # Column doesn't exist in HTML - set to None
                            row_data[expected_col] = None
                    
                    log_message(f"Year {year} {league} {team_name} - Mapped data: {row_data}", log_file, "DEBUG")
                            
                else:
                    # Normal processing for other years
                    max_idx = min(len(cells), len(html_columns))
                    
                    for idx in range(max_idx):
                        if idx < len(html_columns):
                            col_name = html_columns[idx]
                            
                            if idx >= len(cells):
                                continue
                                
                            value = cells[idx].text.strip()
                            
                            if value:
                                value = value.replace(',', '')
                            
                            if col_name.upper() != "TEAM":
                                row_data[col_name] = value
                
                data.append(row_data)
                
            except Exception as e:
                log_message(f"Error processing row: {str(e)}", log_file, "DEBUG")
                continue
    
    except Exception as e:
        log_message(f"Error extracting team {stats_type} complete stats: {str(e)}", log_file, "ERROR")
    
    return data

# =========================
# SAVE DATA TO CSV
# =========================
def save_to_csv(data, filename, output_dir, log_file):
    """
    Save data to CSV, avoiding duplicates.
    
    Args:
        data: List of dictionaries with data to save
        filename: Name of CSV file
        output_dir: Output directory
        log_file: Log file path
    """
    if not data:
        return
    
    filepath = os.path.join(output_dir, filename)
    df_new = pd.DataFrame(data)
    
    if not os.path.exists(filepath):
        # File doesn't exist, create new
        df_new.to_csv(filepath, index=False, encoding='utf-8')
        log_message(f"Created {filename} with {len(df_new)} rows", log_file, "DEBUG")
    else:
        # File exists, check for duplicates before appending
        try:
            df_existing = pd.read_csv(filepath, encoding='utf-8')
            
            # Identify key columns to detect duplicates
            key_columns = []
            if 'Year' in df_new.columns:
                key_columns.append('Year')
            if 'League' in df_new.columns:
                key_columns.append('League')
            if 'Team' in df_new.columns:
                key_columns.append('Team')
            if 'Player_Name' in df_new.columns:
                key_columns.append('Player_Name')
            if 'Statistic' in df_new.columns:
                key_columns.append('Statistic')
            
            if key_columns:
                # Concatenate and remove duplicates
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                
                # Remove duplicates keeping first occurrence
                rows_before = len(df_combined)
                df_combined = df_combined.drop_duplicates(subset=key_columns, keep='first')
                rows_after = len(df_combined)
                
                duplicates_removed = rows_before - rows_after
                rows_added = rows_after - len(df_existing)
                
                # Save deduplicated data
                df_combined.to_csv(filepath, index=False, encoding='utf-8')
                
                if rows_added > 0:
                    log_message(f"Added {rows_added} new rows to {filename}", log_file, "DEBUG")
                    if duplicates_removed > 0:
                        log_message(f"Removed {duplicates_removed} duplicate rows from {filename}", log_file, "DEBUG")
                else:
                    log_message(f"No new rows added to {filename} (all {len(df_new)} were duplicates)", log_file, "DEBUG")
            else:
                # No key columns found, do simple append (less safe)
                df_new.to_csv(filepath, mode='a', header=False, index=False, encoding='utf-8')
                log_message(f"Appended {len(df_new)} rows to {filename} (no duplicate check)", log_file, "WARNING")
        
        except Exception as e:
            log_message(f"Error checking duplicates in {filename}: {str(e)}", log_file, "ERROR")
            # Fallback to simple append
            df_new.to_csv(filepath, mode='a', header=False, index=False, encoding='utf-8')
            log_message(f"Appended {len(df_new)} rows to {filename} (fallback mode)", log_file, "WARNING")

# =========================
# VALIDATION FUNCTIONS
# =========================
def validate_csvs(output_dir, league_name, log_file):
    """Validate all CSV files and save report to TXT file."""
    validation_file = os.path.join(output_dir, f"{league_name}_validation_report.txt")
    
    csv_files = [f for f in os.listdir(output_dir) if f.endswith('.csv')]
    
    if not csv_files:
        message = f"No CSV files found in {output_dir}"
        log_message(message, log_file, "WARNING")
        return
    
    # Open validation report file
    with open(validation_file, 'w', encoding='utf-8') as report:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"{'='*80}\nVALIDATION REPORT - {league_name}\n{timestamp}\n{'='*80}\n\n"
        report.write(header)
        print(header)
        
        for filename in sorted(csv_files):
            filepath = os.path.join(output_dir, filename)
            
            try:
                df = pd.read_csv(filepath)
                
                output = f"\n{filename}:\n"
                output += f"  Total rows: {len(df)}\n"
                output += f"  Columns: {list(df.columns)}\n"
                
                # Check for missing values
                missing = df.isnull().sum()
                missing = missing[missing > 0]
                
                if not missing.empty:
                    output += f" Missing values found:\n"
                    for col, count in missing.items():
                        output += f"     {col}: {count}\n"
                else:
                    output += f"  No missing values in key columns\n"
                
                # Show sample
                output += f"  Sample (first 2 rows):\n"
                sample = df.head(2).to_string(index=False)
                for line in sample.split('\n'):
                    output += f"    {line}\n"
                
                # Write to both file and console
                report.write(output)
                print(output)
                
            except FileNotFoundError:
                output = f"\n{filename}: FILE NOT FOUND\n"
                report.write(output)
                print(output)
            except Exception as e:
                output = f"\n{filename}: ERROR - {str(e)}\n"
                report.write(output)
                print(output)
        
        footer = f"\n{'='*80}\n"
        report.write(footer)
        print(footer)
    
    log_message(f"Validation report saved to {validation_file}", log_file)
