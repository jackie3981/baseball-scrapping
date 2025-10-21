"""
Baseball Statistics Dashboard
Interactive Streamlit dashboard for exploring historical baseball data
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from pathlib import Path

# =========================
# CONFIGURATION
# =========================
# Get absolute path to database
CURRENT_DIR = Path(__file__).parent
DB_PATH = CURRENT_DIR.parent / "baseball_stats.db"

# Verify database exists
if not DB_PATH.exists():
    st.error(f"Database not found at: {DB_PATH}")
    st.info("Please run migrate_to_db.py first to create the database.")
    st.stop()

# Page config
st.set_page_config(
    page_title="Baseball Stats Dashboard",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# DATABASE FUNCTIONS
# =========================
@st.cache_resource
def get_db_connection():
    """Create database connection"""
    try:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        return conn
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        st.stop()

@st.cache_data
def get_table_list():
    """Get all tables in database"""
    conn = get_db_connection()
    query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    tables = pd.read_sql_query(query, conn)
    return tables['name'].tolist()

@st.cache_data
def get_years_range():
    """Get min and max years from database"""
    conn = get_db_connection()
    query = """
    SELECT MIN(Year) as min_year, MAX(Year) as max_year 
    FROM AL_Team_Standings
    """
    result = pd.read_sql_query(query, conn)
    return int(result['min_year'][0]), int(result['max_year'][0])

@st.cache_data
def get_total_teams():
    """Get total unique teams"""
    conn = get_db_connection()
    query = """
    SELECT COUNT(DISTINCT Team) as total
    FROM (
        SELECT Team FROM AL_Team_Standings
        UNION
        SELECT Team FROM NL_Team_Standings
    )
    """
    result = pd.read_sql_query(query, conn)
    return int(result['total'][0])

@st.cache_data
def get_stat_evolution(statistic, league='Both'):
    """Get evolution of a statistic over time"""
    conn = get_db_connection()
    
    # Map statistic name to table and column
    stat_mapping = {
        'Home Runs': ('Player_Hitting_Leaders', 'Home Runs'),
        'Batting Average': ('Player_Hitting_Leaders', 'Batting Average'),
        'RBI': ('Player_Hitting_Leaders', 'RBI'),
        'Strikeouts (Pitcher)': ('Pitcher_Leaders', 'Strikeouts'),
        'ERA': ('Pitcher_Leaders', 'ERA'),
        'Wins': ('Pitcher_Leaders', 'Wins')
    }
    
    table_type, stat_name = stat_mapping[statistic]
    
    if league == 'Both':
        query = f"""
        SELECT Year, League, AVG(CAST(Value AS REAL)) as avg_value
        FROM (
            SELECT Year, League, Value FROM AL_{table_type} WHERE Statistic = '{stat_name}'
            UNION ALL
            SELECT Year, League, Value FROM NL_{table_type} WHERE Statistic = '{stat_name}'
        )
        WHERE Value IS NOT NULL AND Value != ''
        GROUP BY Year, League
        ORDER BY Year
        """
    else:
        query = f"""
        SELECT Year, League, AVG(CAST(Value AS REAL)) as avg_value
        FROM {league}_{table_type}
        WHERE Statistic = '{stat_name}' AND Value IS NOT NULL AND Value != ''
        GROUP BY Year, League
        ORDER BY Year
        """
    
    df = pd.read_sql_query(query, conn)
    return df

# =========================
# SIDEBAR
# =========================
st.sidebar.title("Baseball Stats")
st.sidebar.markdown("---")
st.sidebar.markdown("""
### About
Explore historical baseball statistics from 1876 to 2025.

**Data includes:**
- American League (AL)
- National League (NL)
- Minor Leagues

Navigate through tabs to explore different aspects of the data.
""")

st.sidebar.markdown("---")
st.sidebar.info("Use the filters to customize your view")

# Debug info (optional - remove in production)
with st.sidebar.expander("Debug Info"):
    st.text(f"Database: {DB_PATH}")
    st.text(f"Exists: {DB_PATH.exists()}")
    if DB_PATH.exists():
        size_mb = DB_PATH.stat().st_size / (1024*1024)
        st.text(f"Size: {size_mb:.2f} MB")

# =========================
# MAIN CONTENT
# =========================

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "Overview",
    "Team Analysis", 
    "Player Leaders",
    "Compare"
])

# =========================
# TAB 1: OVERVIEW
# =========================
with tab1:
    st.title("Baseball Statistics Overview")
    st.markdown("---")
    
    # Key Metrics
    col1, col2, col3 = st.columns(3)
    
    try:
        min_year, max_year = get_years_range()
        total_years = max_year - min_year + 1
        total_teams = get_total_teams()
        tables = get_table_list()
        
        with col1:
            st.metric(
                label="Years of Data",
                value=f"{total_years}",
                delta=f"{min_year} - {max_year}"
            )
        
        with col2:
            st.metric(
                label="Total Teams",
                value=f"{total_teams}",
                delta="AL + NL + Minor"
            )
        
        with col3:
            st.metric(
                label="Data Tables",
                value=f"{len(tables)}",
                delta="Complete dataset"
            )
    except Exception as e:
        st.error(f"Error loading database metrics: {e}")
        st.info("Please verify that migrate_to_db.py ran successfully.")
        st.stop()
    
    st.markdown("---")
    
    # Interactive Section
    st.subheader("Historical Trends")
    
    # Filters
    col1, col2 = st.columns([2, 1])
    
    with col1:
        statistic = st.selectbox(
            "Select Statistic",
            ['Home Runs', 'Batting Average', 'RBI', 'Strikeouts (Pitcher)', 'ERA', 'Wins'],
            help="Choose a statistic to see its evolution over time"
        )
    
    with col2:
        league_filter = st.selectbox(
            "League",
            ['Both', 'AL', 'NL'],
            help="Filter by league"
        )
    
    # Get data
    try:
        df_stat = get_stat_evolution(statistic, league_filter)
        
        if not df_stat.empty:
            # Create plot
            if league_filter == 'Both':
                fig = px.line(
                    df_stat,
                    x='Year',
                    y='avg_value',
                    color='League',
                    title=f'{statistic} - Average Leader Value Over Time',
                    labels={'avg_value': f'Average {statistic}', 'Year': 'Year'},
                    color_discrete_map={'AL': '#003831', 'NL': '#8B0000'}
                )
            else:
                fig = px.line(
                    df_stat,
                    x='Year',
                    y='avg_value',
                    title=f'{statistic} - Average Leader Value Over Time ({league_filter})',
                    labels={'avg_value': f'Average {statistic}', 'Year': 'Year'}
                )
                fig.update_traces(line_color='#003831')
            
            # Update layout
            fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color='#000000', size=12),
                title_font=dict(color='#000000', size=16),
                legend=dict(
                    font=dict(color='#000000', size=12),
                    bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='#000000',
                    borderwidth=1
                ),
                hovermode='x unified',
                height=500
            )
            
            fig.update_xaxes(
                showgrid=True, 
                gridcolor='#E5E5E5',
                title_font=dict(color='#000000', size=14),
                tickfont=dict(color='#000000', size=12)
            )
            fig.update_yaxes(
                showgrid=True, 
                gridcolor='#E5E5E5',
                title_font=dict(color='#000000', size=14),
                tickfont=dict(color='#000000', size=12)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show summary stats
            st.markdown("### Summary Statistics")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Minimum", f"{df_stat['avg_value'].min():.2f}")
            with col2:
                st.metric("Maximum", f"{df_stat['avg_value'].max():.2f}")
            with col3:
                st.metric("Average", f"{df_stat['avg_value'].mean():.2f}")
        else:
            st.warning("No data available for the selected filters.")
    except Exception as e:
        st.error(f"Error loading statistics: {e}")
        st.info("This might be due to missing data or database structure issues.")

# =========================
# TAB 2: TEAM ANALYSIS
# =========================
with tab2:
    st.title("Team Analysis")
    st.markdown("---")
    
    # Get list of teams
    @st.cache_data
    def get_teams_list(league):
        """Get list of teams for selected league"""
        conn = get_db_connection()
        if league == 'Both':
            query = """
            SELECT DISTINCT Team FROM AL_Team_Standings
            UNION
            SELECT DISTINCT Team FROM NL_Team_Standings
            ORDER BY Team
            """
        else:
            query = f"SELECT DISTINCT Team FROM {league}_Team_Standings ORDER BY Team"
        df = pd.read_sql_query(query, conn)
        return df['Team'].tolist()
    
    @st.cache_data
    def get_team_standings_history(team, league):
        """Get team's standings history"""
        conn = get_db_connection()
        if league == 'Both':
            query = f"""
            SELECT Year, League, Wins, Losses, WP, GB, Division
            FROM (
                SELECT * FROM AL_Team_Standings WHERE Team = '{team}'
                UNION ALL
                SELECT * FROM NL_Team_Standings WHERE Team = '{team}'
            )
            ORDER BY Year
            """
        else:
            query = f"""
            SELECT Year, League, Wins, Losses, WP, GB, Division
            FROM {league}_Team_Standings
            WHERE Team = '{team}'
            ORDER BY Year
            """
        return pd.read_sql_query(query, conn)
    
    
    # Filters
    col1, col2 = st.columns(2)
    
    with col1:
        league_team = st.selectbox(
            "Select League",
            ['AL', 'NL', 'Both'],
            key='team_league'
        )
    
    with col2:
        teams = get_teams_list(league_team)
        selected_team = st.selectbox(
            "Select Team",
            teams,
            key='selected_team'
        )
    
    # Year range slider
    min_year, max_year = get_years_range()
    year_range = st.slider(
        "Select Year Range",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        key='team_year_range'
    )
    
    st.markdown("---")
    
    # Get data
    try:
        df_standings = get_team_standings_history(selected_team, league_team)
        
        if not df_standings.empty:
            # Filter by year range
            df_standings_filtered = df_standings[
                (df_standings['Year'] >= year_range[0]) & 
                (df_standings['Year'] <= year_range[1])
            ]
            
            if not df_standings_filtered.empty:
                # Wins/Losses Chart
                st.subheader(f"{selected_team} - Wins & Losses")
                
                fig_wins = go.Figure()
                fig_wins.add_trace(go.Scatter(
                    x=df_standings_filtered['Year'],
                    y=df_standings_filtered['Wins'],
                    mode='lines+markers',
                    name='Wins',
                    line=dict(color='#28a745', width=2),
                    marker=dict(size=6)
                ))
                fig_wins.add_trace(go.Scatter(
                    x=df_standings_filtered['Year'],
                    y=df_standings_filtered['Losses'],
                    mode='lines+markers',
                    name='Losses',
                    line=dict(color='#dc3545', width=2),
                    marker=dict(size=6)
                ))
                
                fig_wins.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(color='#000000', size=12),
                    title_font=dict(color='#000000', size=16),
                    legend=dict(
                        font=dict(color='#000000', size=12),
                        bgcolor='rgba(255,255,255,0.8)',
                        bordercolor='#000000',
                        borderwidth=1
                    ),
                    hovermode='x unified',
                    height=400,
                    xaxis_title='Year',
                    yaxis_title='Games'
                )
                
                fig_wins.update_xaxes(
                    showgrid=True, 
                    gridcolor='#E5E5E5',
                    title_font=dict(color='#000000', size=14),
                    tickfont=dict(color='#000000', size=12)
                )
                fig_wins.update_yaxes(
                    showgrid=True, 
                    gridcolor='#E5E5E5',
                    title_font=dict(color='#000000', size=14),
                    tickfont=dict(color='#000000', size=12)
                )
                
                st.plotly_chart(fig_wins, use_container_width=True)
                
                # Summary table
                st.markdown("---")
                st.subheader("Summary Statistics")
                
                summary_data = {
                    'Total Seasons': len(df_standings_filtered),
                    'Total Wins': int(df_standings_filtered['Wins'].sum()),
                    'Total Losses': int(df_standings_filtered['Losses'].sum()),
                    'Best Season': f"{int(df_standings_filtered.loc[df_standings_filtered['Wins'].idxmax(), 'Year'])} ({int(df_standings_filtered['Wins'].max())} wins)",
                    'Worst Season': f"{int(df_standings_filtered.loc[df_standings_filtered['Wins'].idxmin(), 'Year'])} ({int(df_standings_filtered['Wins'].min())} wins)",
                    'Avg Win %': f"{df_standings_filtered['WP'].mean():.3f}"
                }
                
                col1, col2, col3 = st.columns(3)
                items = list(summary_data.items())
                
                with col1:
                    st.metric(items[0][0], items[0][1])
                    st.metric(items[3][0], items[3][1])
                
                with col2:
                    st.metric(items[1][0], items[1][1])
                    st.metric(items[4][0], items[4][1])
                
                with col3:
                    st.metric(items[2][0], items[2][1])
                    st.metric(items[5][0], items[5][1])
                
            else:
                st.warning(f"No data for {selected_team} in the selected year range")
        else:
            st.warning(f"No data found for {selected_team}")
            
    except Exception as e:
        st.error(f"Error loading team data: {e}")

# =========================
# TAB 3: PLAYER LEADERS
# =========================
with tab3:
    st.title("Player Leaders")
    st.markdown("---")
    
    @st.cache_data
    def get_top_players(category, statistic, league, year_range, top_n):
        """Get top N players for a specific statistic"""
        conn = get_db_connection()
        min_year, max_year = year_range
        
        # Determine table based on category
        if category == "Hitting":
            table_suffix = "Player_Hitting_Leaders"
        else:
            table_suffix = "Pitcher_Leaders"
        
        # Build query based on league selection
        if league == "Both":
            query = f"""
            SELECT Player_Name, Team, Year, League, Value
            FROM (
                SELECT * FROM AL_{table_suffix} WHERE Statistic = '{statistic}'
                UNION ALL
                SELECT * FROM NL_{table_suffix} WHERE Statistic = '{statistic}'
            )
            WHERE Year >= {min_year} AND Year <= {max_year}
            AND Value IS NOT NULL
            """
        elif league == "Minor Leagues":
            query = f"""
            SELECT Player_Name, Team, Year, League, Value
            FROM (
                SELECT * FROM AA_{table_suffix} WHERE Statistic = '{statistic}'
                UNION ALL
                SELECT * FROM FL_{table_suffix} WHERE Statistic = '{statistic}'
                UNION ALL
                SELECT * FROM PL_{table_suffix} WHERE Statistic = '{statistic}'
                UNION ALL
                SELECT * FROM UA_{table_suffix} WHERE Statistic = '{statistic}'
            )
            WHERE Year >= {min_year} AND Year <= {max_year}
            AND Value IS NOT NULL
            """
        else:
            query = f"""
            SELECT Player_Name, Team, Year, League, Value
            FROM {league}_{table_suffix}
            WHERE Statistic = '{statistic}'
            AND Year >= {min_year} AND Year <= {max_year}
            AND Value IS NOT NULL
            """
        
        query += " ORDER BY CAST(Value AS REAL) DESC"
        query += f" LIMIT {top_n}"
        
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
        return df
    
    # Category selection (Hitting or Pitching)
    category = st.radio(
        "Select Category",
        ["Hitting", "Pitching"],
        horizontal=True,
        key='player_category'
    )
    
    # Filters row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if category == "Hitting":
            statistic = st.selectbox(
                "Select Statistic",
                ['Home Runs', 'Batting Average', 'Hits', 'RBI', 'Stolen Bases'],
                key='hitting_stat'
            )
        else:
            statistic = st.selectbox(
                "Select Statistic",
                ['ERA', 'Strikeouts', 'Wins', 'Saves'],
                key='pitching_stat'
            )
    
    with col2:
        league_player = st.selectbox(
            "League",
            ['Both', 'AL', 'NL', 'Minor Leagues'],
            key='player_league'
        )
    
    with col3:
        top_n = st.number_input(
            "Number of Players",
            min_value=5,
            max_value=50,
            value=10,
            step=5,
            key='top_n_players'
        )
    
    # Year range slider (start from 1882 to include minor leagues)
    min_year, max_year = get_years_range()
    year_range_players = st.slider(
        "Select Year Range",
        min_value=1882,
        max_value=max_year,
        value=(1882, max_year),
        key='player_year_range'
    )
    
    st.markdown("---")
    
    # Get data
    try:
        df_players = get_top_players(
            category,
            statistic,
            league_player,
            year_range_players,
            top_n
        )
        
        if not df_players.empty:
            # Title
            st.subheader(f" Top {len(df_players)} Players - {statistic}")
            
            # Bar chart
            fig_players = px.bar(
                df_players,
                x='Player_Name',
                y='Value',
                color='League',
                hover_data=['Team', 'Year'],
                title=f'{statistic} Leaders',
                color_discrete_map={'AL': '#003831', 'NL': '#8B0000', 'AA': '#4A4A4A', 
                                   'FL': '#6B6B6B', 'PL': '#8C8C8C', 'UA': '#ADADAD'}
            )
            
            fig_players.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color='#000000', size=12),
                title_font=dict(color='#000000', size=16),
                legend=dict(
                    font=dict(color='#000000', size=12),
                    bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='#000000',
                    borderwidth=1
                ),
                height=500,
                xaxis_title='Player',
                yaxis_title=statistic,
                showlegend=True
            )
            
            fig_players.update_xaxes(
                showgrid=False, 
                tickangle=-45,
                title_font=dict(color='#000000', size=14),
                tickfont=dict(color='#000000', size=12)
            )
            fig_players.update_yaxes(
                showgrid=True, 
                gridcolor='#E5E5E5',
                title_font=dict(color='#000000', size=14),
                tickfont=dict(color='#000000', size=12)
            )
            
            st.plotly_chart(fig_players, use_container_width=True)
            
            # Detailed table
            st.markdown("### Detailed Rankings")
            
            # Format the dataframe for display
            df_display = df_players.copy()
            df_display['Rank'] = range(1, len(df_display) + 1)
            df_display = df_display[['Rank', 'Player_Name', 'Team', 'Year', 'League', 'Value']]
            
            # Format Value based on statistic type
            if statistic in ['Batting Average', 'ERA']:
                df_display['Value'] = df_display['Value'].apply(lambda x: f"{x:.3f}")
            else:
                df_display['Value'] = df_display['Value'].apply(lambda x: f"{int(x)}")
            
            # Rename columns for display
            df_display.columns = ['Rank', 'Player', 'Team', 'Year', 'League', statistic]
            
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            )
            
            # Summary stats
            st.markdown("### Summary")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                best_value = df_players['Value'].max()
                if statistic in ['Batting Average', 'ERA']:
                    st.metric("Best Value", f"{best_value:.3f}")
                else:
                    st.metric("Best Value", f"{int(best_value)}")
            
            with col2:
                avg_value = df_players['Value'].mean()
                if statistic in ['Batting Average', 'ERA']:
                    st.metric("Average", f"{avg_value:.3f}")
                else:
                    st.metric("Average", f"{int(avg_value)}")
            
            with col3:
                year_span = f"{df_players['Year'].min()} - {df_players['Year'].max()}"
                st.metric("Year Range", year_span)
        else:
            st.warning(f"No data available for {statistic} in the selected filters.")
            st.info("Try adjusting the year range or league selection.")
    
    except Exception as e:
        st.error(f"Error loading player data: {e}")
        st.info("This might be due to missing data or database structure issues.")

# =========================
# TAB 4: COMPARE
# =========================
with tab4:
    st.title("⚖️ Compare")
    st.markdown("---")
    
    # Create subtabs
    subtab1, subtab2 = st.tabs(["AL vs NL (Top Teams)", "Team vs Team"])
    
    # =========================
    # SUBTAB 1: AL vs NL
    # =========================
    with subtab1:
        st.subheader("Best Team Comparison by Year")
        st.markdown("Compare the top team from each league for a selected year")
        
        @st.cache_data
        def get_top_teams_by_year(year):
            """Get the team with most wins from each league for a specific year"""
            conn = get_db_connection()
            
            # Get AL top team
            query_al = f"""
            SELECT Team, Wins, Losses, WP, League
            FROM AL_Team_Standings
            WHERE Year = {year}
            ORDER BY Wins DESC
            LIMIT 1
            """
            df_al = pd.read_sql_query(query_al, conn)
            
            # Get NL top team
            query_nl = f"""
            SELECT Team, Wins, Losses, WP, League
            FROM NL_Team_Standings
            WHERE Year = {year}
            ORDER BY Wins DESC
            LIMIT 1
            """
            df_nl = pd.read_sql_query(query_nl, conn)
            
            return df_al, df_nl
        
        # Year selector
        min_year, max_year = get_years_range()
        selected_year = st.slider(
            "Select Year",
            min_value=min_year,
            max_value=max_year,
            value=2024,
            key='compare_year'
        )
        
        st.markdown("---")
        
        try:
            df_al_top, df_nl_top = get_top_teams_by_year(selected_year)
            
            if not df_al_top.empty and not df_nl_top.empty:
                # Combine data
                df_compare = pd.concat([df_al_top, df_nl_top], ignore_index=True)
                
                # Display comparison table
                st.markdown(f"### Top Teams in {selected_year}")
                
                # Format table for display
                df_display = df_compare[['League', 'Team', 'Wins', 'Losses', 'WP']].copy()
                df_display.columns = ['League', 'Team', 'Wins', 'Losses', 'Win %']
                
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Bar chart comparison
                st.markdown("### Wins Comparison")
                
                fig_compare = px.bar(
                    df_compare,
                    x='League',
                    y='Wins',
                    color='League',
                    text='Team',
                    title=f'Best Team Comparison - {selected_year}',
                    color_discrete_map={'AL': '#003831', 'NL': '#8B0000'}
                )
                
                fig_compare.update_traces(textposition='outside')
                
                fig_compare.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(color='#000000', size=12),
                    title_font=dict(color='#000000', size=16),
                    height=400,
                    xaxis_title='League',
                    yaxis_title='Wins',
                    showlegend=False
                )
                
                fig_compare.update_xaxes(
                    showgrid=False,
                    title_font=dict(color='#000000', size=14),
                    tickfont=dict(color='#000000', size=12)
                )
                fig_compare.update_yaxes(
                    showgrid=True,
                    gridcolor='#E5E5E5',
                    title_font=dict(color='#000000', size=14),
                    tickfont=dict(color='#000000', size=12)
                )
                
                st.plotly_chart(fig_compare, use_container_width=True)
                
                # Summary metrics
                st.markdown("### Summary")
                col1, col2, col3 = st.columns(3)
                
                wins_diff = abs(df_al_top['Wins'].values[0] - df_nl_top['Wins'].values[0])
                
                with col1:
                    st.metric("AL Champion", df_al_top['Team'].values[0], f"{int(df_al_top['Wins'].values[0])} wins")
                
                with col2:
                    st.metric("NL Champion", df_nl_top['Team'].values[0], f"{int(df_nl_top['Wins'].values[0])} wins")
                
                with col3:
                    st.metric("Wins Difference", f"{int(wins_diff)}", 
                             "AL" if df_al_top['Wins'].values[0] > df_nl_top['Wins'].values[0] else "NL")
            
            else:
                st.warning(f"No data available for {selected_year}")
        
        except Exception as e:
            st.error(f"Error loading comparison data: {e}")
    
    # =========================
    # SUBTAB 2: TEAM VS TEAM
    # =========================
    with subtab2:
        st.subheader("Head-to-Head Team Comparison")
        st.markdown("Compare wins and losses between two teams over time")
        
        @st.cache_data
        def get_team_comparison_data(team1, league1, team2, league2, year_range):
            """Get comparison data for two teams"""
            conn = get_db_connection()
            min_year, max_year = year_range
            
            # Get team 1 data
            query1 = f"""
            SELECT Year, Team, Wins, Losses, WP
            FROM {league1}_Team_Standings
            WHERE Team = '{team1}'
            AND Year >= {min_year} AND Year <= {max_year}
            ORDER BY Year
            """
            df1 = pd.read_sql_query(query1, conn)
            df1['TeamID'] = 'Team 1'
            
            # Get team 2 data
            query2 = f"""
            SELECT Year, Team, Wins, Losses, WP
            FROM {league2}_Team_Standings
            WHERE Team = '{team2}'
            AND Year >= {min_year} AND Year <= {max_year}
            ORDER BY Year
            """
            df2 = pd.read_sql_query(query2, conn)
            df2['TeamID'] = 'Team 2'
            
            return df1, df2
        
        # Team selection
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Team 1")
            league1 = st.selectbox("League", ['AL', 'NL'], key='team1_league')
            teams1 = get_teams_list(league1)
            team1 = st.selectbox("Select Team", teams1, key='team1_select')
        
        with col2:
            st.markdown("#### Team 2")
            league2 = st.selectbox("League", ['AL', 'NL'], key='team2_league')
            teams2 = get_teams_list(league2)
            team2 = st.selectbox("Select Team", teams2, key='team2_select')
        
        # Year range
        min_year, max_year = get_years_range()
        year_range_compare = st.slider(
            "Select Year Range",
            min_value=min_year,
            max_value=max_year,
            value=(min_year, max_year),
            key='compare_year_range'
        )
        
        st.markdown("---")
        
        try:
            df_team1, df_team2 = get_team_comparison_data(
                team1, league1, team2, league2, year_range_compare
            )
            
            if not df_team1.empty and not df_team2.empty:
                # Line chart comparison
                st.markdown(f"### {team1} vs {team2} - Wins Over Time")
                
                fig_comparison = go.Figure()
                
                fig_comparison.add_trace(go.Scatter(
                    x=df_team1['Year'],
                    y=df_team1['Wins'],
                    mode='lines+markers',
                    name=team1,
                    line=dict(color='#003831', width=2),
                    marker=dict(size=6)
                ))
                
                fig_comparison.add_trace(go.Scatter(
                    x=df_team2['Year'],
                    y=df_team2['Wins'],
                    mode='lines+markers',
                    name=team2,
                    line=dict(color='#8B0000', width=2),
                    marker=dict(size=6)
                ))
                
                fig_comparison.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(color='#000000', size=12),
                    title_font=dict(color='#000000', size=16),
                    legend=dict(
                        font=dict(color='#000000', size=12),
                        bgcolor='rgba(255,255,255,0.8)',
                        bordercolor='#000000',
                        borderwidth=1
                    ),
                    hovermode='x unified',
                    height=400,
                    xaxis_title='Year',
                    yaxis_title='Wins'
                )
                
                fig_comparison.update_xaxes(
                    showgrid=True,
                    gridcolor='#E5E5E5',
                    title_font=dict(color='#000000', size=14),
                    tickfont=dict(color='#000000', size=12)
                )
                fig_comparison.update_yaxes(
                    showgrid=True,
                    gridcolor='#E5E5E5',
                    title_font=dict(color='#000000', size=14),
                    tickfont=dict(color='#000000', size=12)
                )
                
                st.plotly_chart(fig_comparison, use_container_width=True)
                
                # Comparison table
                st.markdown("### Side-by-Side Comparison")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"#### {team1} ({league1})")
                    df_team1_display = df_team1[['Year', 'Wins', 'Losses', 'WP']].copy()
                    df_team1_display.columns = ['Year', 'Wins', 'Losses', 'Win %']
                    st.dataframe(df_team1_display, use_container_width=True, hide_index=True, height=300)
                
                with col2:
                    st.markdown(f"#### {team2} ({league2})")
                    df_team2_display = df_team2[['Year', 'Wins', 'Losses', 'WP']].copy()
                    df_team2_display.columns = ['Year', 'Wins', 'Losses', 'Win %']
                    st.dataframe(df_team2_display, use_container_width=True, hide_index=True, height=300)
                
                # Summary statistics
                st.markdown("### Overall Summary")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"**{team1}**")
                    st.metric("Total Seasons", len(df_team1))
                    st.metric("Avg Wins/Season", f"{df_team1['Wins'].mean():.1f}")
                    st.metric("Best Season", f"{int(df_team1['Wins'].max())} wins")
                
                with col2:
                    st.markdown(f"**{team2}**")
                    st.metric("Total Seasons", len(df_team2))
                    st.metric("Avg Wins/Season", f"{df_team2['Wins'].mean():.1f}")
                    st.metric("Best Season", f"{int(df_team2['Wins'].max())} wins")
                
                with col3:
                    st.markdown("**Comparison**")
                    avg_diff = abs(df_team1['Wins'].mean() - df_team2['Wins'].mean())
                    better_team = team1 if df_team1['Wins'].mean() > df_team2['Wins'].mean() else team2
                    st.metric("Avg Wins Difference", f"{avg_diff:.1f}")
                    st.metric("Better Average", better_team)
                    
                    # Count who had more wins in common years
                    common_years = set(df_team1['Year']).intersection(set(df_team2['Year']))
                    if common_years:
                        team1_better = sum(1 for year in common_years 
                                         if df_team1[df_team1['Year']==year]['Wins'].values[0] > 
                                            df_team2[df_team2['Year']==year]['Wins'].values[0])
                        st.metric("Years Team 1 Better", f"{team1_better}/{len(common_years)}")
            
            elif df_team1.empty:
                st.warning(f"No data found for {team1} in the selected year range")
            elif df_team2.empty:
                st.warning(f"No data found for {team2} in the selected year range")
        
        except Exception as e:
            st.error(f"Error loading comparison data: {e}")

# =========================
# FOOTER
# =========================
st.sidebar.markdown("---")
st.sidebar.markdown("*Data scraped from Baseball Almanac*")
st.sidebar.markdown("*Dashboard created with Streamlit*")