"""
Minor Leagues Scraper
Scrapes baseball statistics for Federal League, Players League, Union Association, and American Association
"""

import os
import json
import time
from selenium.webdriver.common.by import By
from common_scraper import *

# =========================
# CONFIGURATION
# =========================
OUTPUT_DIR = "MINOR_CSV"
LOG_FILE = "scraping_log_minor_leagues.txt"
CHECKPOINT_FILE = "checkpoint_minor_leagues.json"
BASE_URL = "https://www.baseball-almanac.com/yearmenu.shtml"

# Minor leagues to process
MINOR_LEAGUES = {
    "The History of the Federal League From 1914 to 1915": "FL",
    "The History of the Players League From 1890 - 1890": "PL",
    "The History of the Union Association From 1884 - 1884": "UA",
    "The History of the American Association From 1882 - 1891": "AA"
}

# =========================
# CHECKPOINT FUNCTIONS FOR MULTIPLE LEAGUES
# =========================
def save_checkpoint_multi(processed_data):
    """Save checkpoint for multiple leagues."""
    checkpoint = {
        "processed_data": processed_data,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f, indent=2)
    
    total_years = sum(len(years) for years in processed_data.values())
    log_message(f"Checkpoint saved: {total_years} total years processed across all leagues", LOG_FILE)

def load_checkpoint_multi():
    """Load checkpoint for multiple leagues."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                checkpoint = json.load(f)
                processed_data = checkpoint.get("processed_data", {})
                total_years = sum(len(years) for years in processed_data.values())
                log_message(f"Resuming from checkpoint: {total_years} years already processed across all leagues", LOG_FILE)
                return {k: set(v) for k, v in processed_data.items()}
        except:
            pass
    return {}

# =========================
# CLEAN CSV FILES
# =========================
def clean_csv_files_for_league(league_code):
    """Remove existing CSV files for a specific league."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        return
    
    for file in os.listdir(OUTPUT_DIR):
        if file.startswith(f"{league_code}_") and file.endswith('.csv'):
            file_path = os.path.join(OUTPUT_DIR, file)
            os.remove(file_path)
            log_message(f"Removed {file}", LOG_FILE, "DEBUG")

# =========================
# PROCESS YEAR
# =========================
def process_year(driver, year_url, year, league_code):
    """Process a single year and extract all tables."""
    log_message(f"Processing Year: {year} - {league_code}", LOG_FILE)
    
    driver.get(year_url)
    time.sleep(PAGE_DELAY)
    ba_tables = driver.find_elements(By.CLASS_NAME, "ba-table")
    log_message(f"Found {len(ba_tables)} tables", LOG_FILE, "DEBUG")
    
    for idx, ba_table in enumerate(ba_tables, 1):
        try:
            title = ba_table.find_element(By.TAG_NAME, "h2").text.strip()
            
            try:
                subtitle = ba_table.find_element(By.XPATH, ".//td[@class='header']//p").text.strip()
            except:
                subtitle = ""
            
            # Player Review / Pitcher Review - Check BOTH title and subtitle
            if "Player Review" in title or "Pitcher Review" in title:
                # Determine if it's pitching or hitting by checking subtitle first, then title
                is_pitching = "Pitching" in subtitle or "Pitcher" in subtitle or "Pitcher Review" in title
                
                data = extract_player_leaders(ba_table, year, league_code, LOG_FILE)
                
                if is_pitching:
                    save_to_csv(data, f"{league_code}_Pitcher_Leaders.csv", OUTPUT_DIR, LOG_FILE)
                else:
                    save_to_csv(data, f"{league_code}_Player_Hitting_Leaders.csv", OUTPUT_DIR, LOG_FILE)
            
            # Team Standings
            elif "Team Standings" in title or "Team Standings" in subtitle:
                data = extract_team_standings(ba_table, year, league_code, LOG_FILE)
                save_to_csv(data, f"{league_code}_Team_Standings.csv", OUTPUT_DIR, LOG_FILE)
            
            # Team Review (only vertical format exists for these leagues)
            elif "Team Review" in title:
                if "Hitting" in subtitle:
                    data = extract_team_leaders(ba_table, year, league_code, "Hitting", LOG_FILE)
                    save_to_csv(data, f"{league_code}_Team_Hitting_Leaders.csv", OUTPUT_DIR, LOG_FILE)
                elif "Pitching" in subtitle:
                    data = extract_team_leaders(ba_table, year, league_code, "Pitching", LOG_FILE)
                    save_to_csv(data, f"{league_code}_Team_Pitching_Leaders.csv", OUTPUT_DIR, LOG_FILE)
            
        except Exception as e:
            log_message(f"Error processing table {idx}: {str(e)}", LOG_FILE, "WARNING")

# =========================
# MAIN FLOW
# =========================
def main():
    # Setup
    ensure_directory(OUTPUT_DIR)
    
    log_message("="*80, LOG_FILE)
    log_message("BASEBALL SCRAPING - MINOR LEAGUES", LOG_FILE)
    log_message("="*80, LOG_FILE)
    
    # Clear old checkpoint if starting fresh
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        log_message("Removed old checkpoint", LOG_FILE)
    
    driver = setup_driver()
    
    try:
        # Extract all leagues and years
        leagues_data = extract_league_years(driver, BASE_URL, LOG_FILE)
        
        # Load checkpoint
        processed_data = load_checkpoint_multi()
        
        # Process each minor league
        for league_key, league_short in MINOR_LEAGUES.items():
            log_message("="*80, LOG_FILE)
            log_message(f"Processing {league_key.split('From')[0].strip()} ({league_short})", LOG_FILE)
            log_message("="*80, LOG_FILE)
            
            if league_key not in leagues_data:
                log_message(f"League '{league_key}' not found", LOG_FILE, "WARNING")
                continue
            
            years = leagues_data[league_key]
            total_years = len(years)
            
            # Get processed years for this league
            if league_short not in processed_data:
                processed_data[league_short] = set()
            
            processed_years = processed_data[league_short]
            
            log_message(f"Total years to process: {total_years}", LOG_FILE)
            log_message(f"Already processed: {len(processed_years)}", LOG_FILE)
            log_message(f"Remaining: {total_years - len(processed_years)}", LOG_FILE)
            
            failed_years = []
            
            for idx, year_info in enumerate(years, 1):
                year = year_info["year"]
                year_url = year_info["url"]
                
                if year in processed_years:
                    continue
                
                log_message(f"[{idx}/{total_years}] Processing {year}...", LOG_FILE)
                
                try:
                    process_year(driver, year_url, year, league_short)
                    processed_years.add(year)
                    processed_data[league_short] = processed_years
                    
                    # Save checkpoint after each year for minor leagues
                    save_checkpoint_multi({k: list(v) for k, v in processed_data.items()})
                except Exception as e:
                    log_message(f"Error processing year {year}: {str(e)}", LOG_FILE, "ERROR")
                    failed_years.append(year)
                
                time.sleep(0.5)
            
            # Summary for this league
            log_message(f"{league_key.split('From')[0].strip()} complete: {len(processed_years)} success, {len(failed_years)} failed", LOG_FILE)
            if failed_years:
                log_message(f"Failed years: {failed_years}", LOG_FILE)
        
        # Final summary
        log_message("="*80, LOG_FILE)
        log_message("ALL MINOR LEAGUES SCRAPING COMPLETE", LOG_FILE)
        total_processed = sum(len(years) for years in processed_data.values())
        log_message(f"Total years processed across all leagues: {total_processed}", LOG_FILE)
        log_message("="*80, LOG_FILE)
        
        # Run validation and save report
        validate_csvs(OUTPUT_DIR, "MINOR_LEAGUES", LOG_FILE)
        
    except Exception as e:
        log_message(f"Fatal error: {str(e)}", LOG_FILE, "ERROR")
    
    finally:
        driver.quit()
        log_message("Browser closed", LOG_FILE)

if __name__ == "__main__":
    main()
