"""
American League (AL) Scraper
Scrapes baseball statistics for the American League from 1901 to 2025
"""

import os
import json
import time
from selenium.webdriver.common.by import By
from common_scraper import *

# =========================
# CONFIGURATION
# =========================
OUTPUT_DIR = "AL_CSV"
LOG_FILE = "scraping_log_AL.txt"
CHECKPOINT_FILE = "checkpoint_AL.json"
LEAGUE_KEY = "The History of the American League From 1901 to 2025"
LEAGUE_SHORT = "AL"
BASE_URL = "https://www.baseball-almanac.com/yearmenu.shtml"

# =========================
# CHECKPOINT FUNCTIONS
# =========================
def save_checkpoint(processed_years):
    """Save checkpoint to resume processing later."""
    checkpoint = {
        "league": LEAGUE_SHORT,
        "processed_years": processed_years,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f, indent=2)
    
    log_message(f"Checkpoint saved: {len(processed_years)} years processed", LOG_FILE)

def load_checkpoint():
    """Load checkpoint if exists."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                checkpoint = json.load(f)
                if checkpoint.get("league") == LEAGUE_SHORT:
                    log_message(f"Resuming from checkpoint: {len(checkpoint.get('processed_years', []))} years already processed", LOG_FILE)
                    return set(checkpoint.get("processed_years", []))
        except:
            pass
    return set()

# =========================
# CLEAN CSV FILES
# =========================
def clean_csv_files():
    """Remove existing CSV files to start fresh."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        return
    
    for file in os.listdir(OUTPUT_DIR):
        if file.endswith('.csv'):
            file_path = os.path.join(OUTPUT_DIR, file)
            os.remove(file_path)
            log_message(f"Removed {file}", LOG_FILE, "DEBUG")

# =========================
# PROCESS YEAR
# =========================
def process_year(driver, year_url, year):
    """Process a single year and extract all tables."""
    log_message(f"Processing Year: {year} - {LEAGUE_SHORT}", LOG_FILE)
    
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
            
            if "Player Review" in title:
                data = extract_player_leaders(ba_table, year, LEAGUE_SHORT, LOG_FILE)
                save_to_csv(data, "AL_Player_Hitting_Leaders.csv", OUTPUT_DIR, LOG_FILE)
            
            elif "Pitcher Review" in title:
                data = extract_player_leaders(ba_table, year, LEAGUE_SHORT, LOG_FILE)
                save_to_csv(data, "AL_Pitcher_Leaders.csv", OUTPUT_DIR, LOG_FILE)
            
            elif "Team Standings" in title or ("American League" in title and "Team Standings" in ba_table.text):
                data = extract_team_standings(ba_table, year, LEAGUE_SHORT, LOG_FILE)
                save_to_csv(data, "AL_Team_Standings.csv", OUTPUT_DIR, LOG_FILE)
            
            elif "Team Review" in title:
                try:
                    banner_row = ba_table.find_element(By.XPATH, ".//tr[td[@class='banner']]")
                    headers = banner_row.find_elements(By.TAG_NAME, "td")
                    num_columns = len(headers)
                except:
                    num_columns = 0
                
                if num_columns == 3:
                    if "Hitting" in subtitle:
                        data = extract_team_leaders(ba_table, year, LEAGUE_SHORT, "Hitting", LOG_FILE)
                        save_to_csv(data, "AL_Team_Hitting_Leaders.csv", OUTPUT_DIR, LOG_FILE)
                    elif "Pitching" in subtitle:
                        data = extract_team_leaders(ba_table, year, LEAGUE_SHORT, "Pitching", LOG_FILE)
                        save_to_csv(data, "AL_Team_Pitching_Leaders.csv", OUTPUT_DIR, LOG_FILE)
                elif num_columns > 10:
                    if "Hitting" in subtitle:
                        data = extract_team_stats_complete(ba_table, year, LEAGUE_SHORT, "Hitting", LOG_FILE)
                        save_to_csv(data, "AL_Team_Hitting_Complete.csv", OUTPUT_DIR, LOG_FILE)
                    elif "Pitching" in subtitle:
                        data = extract_team_stats_complete(ba_table, year, LEAGUE_SHORT, "Pitching", LOG_FILE)
                        save_to_csv(data, "AL_Team_Pitching_Complete.csv", OUTPUT_DIR, LOG_FILE)
            
        except Exception as e:
            log_message(f"Error processing table {idx}: {str(e)}", LOG_FILE, "WARNING")

# =========================
# MAIN FLOW
# =========================
def main():
    # Setup
    ensure_directory(OUTPUT_DIR)
    
    log_message("="*80, LOG_FILE)
    log_message("BASEBALL SCRAPING - FULL RUN - AMERICAN LEAGUE", LOG_FILE)
    log_message("="*80, LOG_FILE)
    
    # Clean existing files
    clean_csv_files()
    
    # Clear old checkpoint if starting fresh
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        log_message("Removed old checkpoint", LOG_FILE)
    
    driver = setup_driver()
    
    try:
        # Extract leagues and years
        leagues_data = extract_league_years(driver, BASE_URL, LOG_FILE)
        
        if LEAGUE_KEY not in leagues_data:
            log_message(f"League '{LEAGUE_KEY}' not found", LOG_FILE, "ERROR")
            return
        
        al_years = leagues_data[LEAGUE_KEY]
        total_years = len(al_years)
        
        # Load checkpoint
        processed_years = load_checkpoint()
        
        log_message(f"Total years to process: {total_years}", LOG_FILE)
        log_message(f"Already processed: {len(processed_years)}", LOG_FILE)
        log_message(f"Remaining: {total_years - len(processed_years)}", LOG_FILE)
        
        failed_years = []
        
        for idx, year_info in enumerate(al_years, 1):
            year = year_info["year"]
            year_url = year_info["url"]
            
            if year in processed_years:
                continue
            
            log_message(f"[{idx}/{total_years}] Processing {year}...", LOG_FILE)
            
            try:
                process_year(driver, year_url, year)
                processed_years.add(year)
                
                # Save checkpoint every 10 years
                if len(processed_years) % 10 == 0:
                    save_checkpoint(list(processed_years))
            except Exception as e:
                log_message(f"Error processing year {year}: {str(e)}", LOG_FILE, "ERROR")
                failed_years.append(year)
            
            time.sleep(0.5)
        
        # Final checkpoint
        save_checkpoint(list(processed_years))
        
        # Summary
        log_message("="*80, LOG_FILE)
        log_message("SCRAPING COMPLETE", LOG_FILE)
        log_message(f"Total processed: {len(processed_years)}", LOG_FILE)
        log_message(f"Failed: {len(failed_years)}", LOG_FILE)
        if failed_years:
            log_message(f"Failed years: {failed_years}", LOG_FILE)
        log_message("="*80, LOG_FILE)
        
        # Run validation and save report
        validate_csvs(OUTPUT_DIR, LEAGUE_SHORT, LOG_FILE)
        
    except Exception as e:
        log_message(f"Fatal error: {str(e)}", LOG_FILE, "ERROR")
    
    finally:
        driver.quit()
        log_message("Browser closed", LOG_FILE)

if __name__ == "__main__":
    main()