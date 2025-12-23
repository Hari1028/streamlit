import streamlit as st
import pandas as pd
import sqlite3
import os
import requests
from dotenv import load_dotenv

# Import your graph templates
try:
    from graphs import graph_factory
except ImportError:
    st.error("❌ Error: 'graph.py' not found. Please make sure graph.py is in the same directory.")
    st.stop()

# --- 1. SETUP ---
load_dotenv()
st.set_page_config(page_title="Anomaly Co-Pilot", layout="wide")

# CSS for the "Grafana-Dark" Look
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    
    /* Chat Container */
    .stChatMessage {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
    }
    
    /* Fixed Right Canvas for Graphs */
    div[data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart) {
        border: 1px solid #333;
        border-radius: 10px;
        padding: 20px;
        background-color: #161B22;
        min-height: 500px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'olist.sqlite')

# --- 2. LLM CONNECTION ---
def query_llm(messages):
    token = os.environ.get('LLMFOUNDRY_TOKEN')
    if not token: 
        return "Error: LLMFOUNDRY_TOKEN not found in .env file."

    url = "https:///openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}:my-test-project",
        "Content-Type": "application/json"
    }
    # Temp 0.3 allows for natural conversation but strict command adherence
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.3 
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"LLM Error: {str(e)}"

# --- 3. DATA & SCHEMA HELPERS ---
def get_schema_context():
    """
    Dynamically fetches table names and column info.
    This runs on every interaction to support 'New Tables'.
    """
    if not os.path.exists(DB_PATH):
        return "Error: Database file not found."
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    schema_str = "CURRENT DATABASE SCHEMA:\n"
    for t in tables:
        table_name = t[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        # Format: Name (Type)
        cols = [f"{c[1]} ({c[2]})" for c in cursor.fetchall()]
        schema_str += f"- Table: {table_name}\n  Columns: {', '.join(cols)}\n"
    conn.close()
    return schema_str

def get_data_for_graph(table_name):
    """Fetches data for the visualization"""
    conn = sqlite3.connect(DB_PATH)
    try:
        # Limit to 2000 rows for performance in POC
        return pd.read_sql(f"SELECT * FROM {table_name} LIMIT 2000", conn)
    except Exception as e:
        return None
    finally:
        conn.close()

# --- 4. SESSION STATE INIT ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add an empty starter message so the UI renders correctly
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I am your Data Observability Agent. Which table would you like to investigate?"})

if "active_chart_fig" not in st.session_state:
    st.session_state.active_chart_fig = None

if "last_cmd" not in st.session_state:
    st.session_state.last_cmd = None

# --- 5. SYSTEM PROMPT BUILDER ---
# We rebuild this every time to capture new tables
schema_context = get_schema_context()

system_prompt = f"""
You are an expert Data Observability Agent (like a smart Grafana).
You have access to a SQLite database with the following schema:

{schema_context}

You have access to a Graph Library with these 4 TEMPLATES:
1. 'line' (Requires: Date/Time column + Numeric column) -> Good for Trends/Spikes.
2. 'bar' (Requires: Category column + Numeric column) -> Good for Counts/Comparisons.
3. 'histogram' (Requires: Numeric column) -> Good for Distributions/Outliers.
4. 'scatter' (Requires: 2 Numeric columns) -> Good for Correlations.

YOUR BEHAVIOR PROTOCOL (Follow this strict flow):
PHASE 1: CONSULTATION
- If the user asks for a table (e.g., "Check bronze_customers"), DO NOT PLOT YET.
- First, analyze the columns of that table.
- Then, propose 2-3 suitable graph options to the user.
- Example: "I see 'city' and 'customer_id'. I can show a Bar Chart of users per city, or a Line Chart of signups over time. Which do you prefer?"

PHASE 2: EXECUTION
- Only when the user CONFIRMS their choice (e.g., "Show the Bar chart"), output the command.
- The command must be the LAST line of your response.
- Format: `CMD_PLOT|table_name|graph_type`
- Example: "Understood. Plotting the data now. CMD_PLOT|bronze_customers|bar"

PHASE 3: GENERAL CHAT
- If the user says "Hello" or asks non-data questions, just chat normally.
"""

# --- 6. UI LAYOUT ---
st.title("🤖 Anomaly Co-Pilot (POC)")
col_chat, col_canvas = st.columns([1, 1.5]) # Split 40% Chat / 60% Graph

# === LEFT COLUMN: CHAT INTERFACE ===
with col_chat:
    st.subheader("💬 Agent Chat")
    
    # Render Chat History (Excluding System Prompt)
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                # Clean the message to hide the raw command from the user
                display_text = msg["content"].split("CMD_PLOT")[0].strip()
                st.markdown(display_text)

    # Chat Input
    if prompt := st.chat_input("Type here (e.g., 'Visualize bronze_orders')..."):
        # 1. Append User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Construct Messages for LLM (System Prompt + History)
        llm_messages = [{"role": "system", "content": system_prompt}] + st.session_state.messages[-10:] # Keep last 10 turns context

        with st.spinner("Thinking..."):
            response_text = query_llm(llm_messages)
            
            # 3. Detect Command
            cmd_match = False
            if "CMD_PLOT" in response_text:
                try:
                    # Parse command: CMD_PLOT|table|type
                    cmd_part = response_text.split("CMD_PLOT|")[1].strip()
                    table_name, graph_type = cmd_part.split("|")
                    
                    # Store logic to run in the Canvas column
                    st.session_state.last_cmd = {"table": table_name.strip(), "type": graph_type.strip()}
                    cmd_match = True
                except:
                    st.error("Agent tried to plot but sent a bad command.")

            # 4. Append Assistant Message
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            with st.chat_message("assistant"):
                st.markdown(response_text.split("CMD_PLOT")[0].strip())
            
            # Force rerun to update the Right Canvas immediately
            if cmd_match:
                st.rerun()

# === RIGHT COLUMN: VISUAL CANVAS ===
with col_canvas:
    st.subheader("📊 Visualization Canvas")
    
    if st.session_state.last_cmd:
        cmd = st.session_state.last_cmd
        table = cmd['table']
        g_type = cmd['type']
        
        # Fetch Data
        df = get_data_for_graph(table)
        
        if df is not None and not df.empty:
            # 1. Auto-Detect Columns based on Graph Type (Simple Logic for POC)
            # In a full app, the LLM could also specify WHICH columns to use in the CMD_PLOT command
            num_cols = df.select_dtypes(include=['number']).columns.tolist()
            cat_cols = df.select_dtypes(include=['object']).columns.tolist()
            date_cols = [c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()]
            
            config = {'type': g_type, 'title': f"{g_type.title()} of {table}"}
            
            # Smart Column Mapping for the Templates
            if g_type == 'line':
                config['x'] = date_cols[0] if date_cols else df.columns[0]
                config['y'] = num_cols[0] if num_cols else df.columns[1]
            elif g_type == 'bar':
                config['x'] = cat_cols[0] if cat_cols else df.columns[0]
                config['y'] = num_cols[0] if num_cols else df.columns[1]
            elif g_type == 'histogram':
                config['x'] = num_cols[0] if num_cols else df.columns[0]
            elif g_type == 'scatter':
                config['x'] = num_cols[0] if num_cols else df.columns[0]
                config['y'] = num_cols[1] if len(num_cols) > 1 else df.columns[1]

            # 2. Generate Figure using your graph.py factory
            fig = graph_factory(df, config)
            
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                st.success(f"Rendered {g_type} for {table}")
            else:
                st.error(f"Could not render graph. Check data types in {table}.")
        else:
            st.warning(f"Table '{table}' is empty or not found.")
    else:
        # Empty State (Grafana Style Placeholder)
        st.markdown("""
        <div style='text-align: center; color: #555; padding-top: 100px;'>
            <h3>No Active Graph</h3>
            <p>Ask the agent on the left to visualize a table.</p>
        </div>
        """, unsafe_allow_html=True)
