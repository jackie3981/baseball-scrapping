# query_database.py

"""
Baseball Statistics Query Program
Interactive command-line interface for querying the baseball database
"""

import sqlite3
import sys
from tabulate import tabulate  # To format tables

DATABASE_FILE = "baseball_stats.db"

def connect_db():
    """Connect to database"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def show_menu():
    """Display main menu"""
    print("\n" + "="*60)
    print("BASEBALL STATISTICS QUERY PROGRAM")
    print("="*60)
    print("\n1. List all tables")
    print("2. View table structure")
    print("3. Show sample data from table")
    print("4. Search player statistics")
    print("5. Compare AL vs NL stats")
    print("6. Team standings by year")
    print("7. Custom SQL query")
    print("8. Exit")
    print("\n" + "="*60)

def format_results(cursor, max_rows=50):
    """Format query results as a table"""
    results = cursor.fetchall()
    
    if not results:
        return None, 0
    
    # Convert Row objects to list of tuples
    headers = results[0].keys()
    rows = [tuple(row) for row in results]
    
    # Limit rows if too many
    total_rows = len(rows)
    if total_rows > max_rows:
        rows = rows[:max_rows]
    
    return tabulate(rows, headers=headers, tablefmt='grid'), total_rows

def list_tables(conn):
    """List all tables in database"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    print("\n TABLES IN DATABASE:")
    for idx, table in enumerate(tables, 1):
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"{idx:2d}. {table[0]:<40} ({count:,} rows)")

def view_table_structure(conn):
    """View structure of a table"""
    table_name = input("\n Enter table name: ").strip()
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        results = cursor.fetchall()
        
        if results:
            columns = [[row['name'], row['type']] for row in results]
            print(f"\n Structure of '{table_name}':\n")
            print(tabulate(columns, headers=['Column', 'Type'], tablefmt='grid'))
        else:
            print(f"\n Table '{table_name}' not found.")
    
    except sqlite3.Error as e:
        print(f"\n Error: {e}")

def show_sample_data(conn):
    """Show sample rows from a table"""
    table_name = input("\n Enter table name: ").strip()
    limit = input("Number of rows to display (default 10): ").strip() or "10"
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        
        formatted, total = format_results(cursor)
        if formatted:
            print(f"\n Sample data from '{table_name}' (showing {total} rows):\n")
            print(formatted)
        else:
            print(f"\n No data found in '{table_name}'")
    
    except sqlite3.Error as e:
        print(f"\n Error: {e}")


def search_player(conn):
    """Search for player statistics"""
    player_name = input("\nEnter player name (or partial name): ").strip()
    league = input("League (AL/NL/Both): ").strip().upper()
    
    # Build query based on league
    if league == "BOTH":
        query = """
        SELECT Year, League, Statistic, Player_Name, Team, Value
        FROM (
            SELECT * FROM AL_Player_Hitting_Leaders
            UNION ALL
            SELECT * FROM NL_Player_Hitting_Leaders
        )
        WHERE Player_Name LIKE ?
        ORDER BY Year DESC, League
        """
        params = (f"%{player_name}%",)
    else:
        table = f"{league}_Player_Hitting_Leaders"
        query = f"""
        SELECT Year, League, Statistic, Player_Name, Team, Value
        FROM {table}
        WHERE Player_Name LIKE ?
        ORDER BY Year DESC
        """
        params = (f"%{player_name}%",)
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        if results:
            headers = ['Year', 'League', 'Statistic', 'Player', 'Team', 'Value']
            print(f"\nFound {len(results)} results:\n")
            print(tabulate(results, headers=headers, tablefmt='grid'))
        else:
            print(f"\n No results found for '{player_name}'")
    
    except Exception as e:
        print(f"\n Error: {e}")

def compare_leagues(conn):
    """Compare AL vs NL team hitting and pitching statistics for years ≤ given year."""
    year = input("\nEnter year: ").strip()

    cursor = conn.cursor()

    # Query with pivot for hitting and pitching
    query = """
    WITH Hitting AS (
        SELECT 
            League,
            Team,
            Year,
            MAX(CASE WHEN Statistic = 'Hits' THEN Value END) AS Hits,
            MAX(CASE WHEN Statistic = 'Home Runs' THEN Value END) AS HomeRuns,
            MAX(CASE WHEN Statistic = 'Batting Average' THEN Value END) AS BattingAvg
        FROM (
            SELECT * FROM AL_Team_Hitting_Leaders WHERE Year <= ?
            UNION ALL
            SELECT * FROM NL_Team_Hitting_Leaders WHERE Year <= ?
        )
        GROUP BY League, Team, Year
    ),
    Pitching AS (
        SELECT 
            League,
            Team,
            Year,
            MAX(CASE WHEN Statistic = 'ERA' THEN Value END) AS ERA,
            MAX(CASE WHEN Statistic = 'Strikeouts' THEN Value END) AS Strikeouts,
            MAX(CASE WHEN Statistic = 'Saves' THEN Value END) AS Saves
        FROM (
            SELECT * FROM AL_Team_Pitching_Leaders WHERE Year <= ?
            UNION ALL
            SELECT * FROM NL_Team_Pitching_Leaders WHERE Year <= ?
        )
        GROUP BY League, Team, Year
    )
    SELECT 
        h.League,
        h.Team,
        h.Year,
        h.Hits,
        h.HomeRuns,
        h.BattingAvg,
        p.ERA,
        p.Strikeouts,
        p.Saves
    FROM Hitting h
    JOIN Pitching p
        ON h.League = p.League
        AND h.Team = p.Team
        AND h.Year = p.Year
    WHERE h.Hits IS NOT NULL
    ORDER BY h.Year DESC, h.League, h.Hits DESC
    LIMIT 10;
    """

    try:
        # Pass the year 4 times for the 4 placeholders '?'
        cursor.execute(query, (year, year, year, year))
        results = cursor.fetchall()

        if not results:
            print(f"\n No data found for years ≤ {year}")
            return

        # Print header
        print(f"\nComparison AL vs NL (Top 10 teams by Hits, years ≤ {year})")
        print("-" * 85)
        print(f"{'League':<6} {'Team':<20} {'Year':<6} {'Hits':<6} {'HR':<6} {'AVG':<6} {'ERA':<6} {'K':<6} {'Saves':<6}")
        print("-" * 85)

        # print results
        for row in results:
            league, team, yr, hits, hr, avg, era, k, saves = row
            print(f"{league:<6} {team:<20} {yr:<6} {hits or '':<6} {hr or '':<6} {avg or '':<6} {era or '':<6} {k or '':<6} {saves or '':<6}")

    except Exception as e:
        print(f"\n Error executing query: {e}")
    finally:
        cursor.close()


def team_standings(conn):
    """Show team standings"""
    year = input("\nEnter year: ").strip()
    league = input("League (AL/NL): ").strip().upper()
    
    query = f"""
    SELECT Team, Wins, Losses, WP, GB
    FROM {league}_Team_Standings
    WHERE Year = ?
    ORDER BY Wins DESC
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, (year,))
        results = cursor.fetchall()
        
        if results:
            headers = ['Team', 'Wins', 'Losses', 'Win %', 'GB']
            print(f"\n {league} Standings - {year}:\n")
            print(tabulate(results, headers=headers, tablefmt='grid'))
        else:
            print(f"\n No data found for {league} in {year}")

    except Exception as e:
        print(f"\n Error: {e}")

def custom_query(conn):
    """Execute custom SQL query"""
    print("\n Enter your SQL query (or 'back' to return):")
    print("Example: SELECT * FROM AL_Team_Standings WHERE Year = 2023 LIMIT 5")
    
    query = input("\nSQL> ").strip()
    
    if query.lower() == 'back':
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        
        if results:
            # Get column names
            headers = [description[0] for description in cursor.description]
            print(f"\n Query returned {len(results)} rows:\n")
            print(tabulate(results, headers=headers, tablefmt='grid'))
        else:
            print("\n Query executed successfully (no results returned)")
    
    except Exception as e:
        print(f"\n SQL Error: {e}")

def main():
    """Main program loop"""
    conn = connect_db()
    print("\n Connected to database:", DATABASE_FILE)
    
    while True:
        show_menu()
        choice = input("\nSelect option (1-8): ").strip()
        
        if choice == '1':
            list_tables(conn)
        elif choice == '2':
            view_table_structure(conn)
        elif choice == '3':
            show_sample_data(conn)    
        elif choice == '4':
            search_player(conn)
        elif choice == '5':
            compare_leagues(conn)
        elif choice == '6':
            team_standings(conn)
        elif choice == '7':
            custom_query(conn)
        elif choice == '8':
            print("\nGoodbye!")
            break
        else:
            print("\nInvalid option. Please choose 1-8.")

        input("\nPress Enter to continue...")
    
    conn.close()

if __name__ == "__main__":
    main()