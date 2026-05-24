# ─────────────────────────────────────────────────────────────────
# INSTALL:
# pip install -r requirements.txt
#
# RUN:
# streamlit run loan_dashboard.py
#
# NOTE:
# final_result_prediction.xlsx
# must be in same folder
# ─────────────────────────────────────────────────────────────────

import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

from google import genai
from datetime import datetime

# ─────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Loan Executive Dashboard",
    page_icon="🏦",
    layout="wide"
)

# ─────────────────────────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────────────────────────
BG_COLOR = "#F4F7FB"
TEXT_COLOR = "#1F2937"
SUBTEXT_COLOR = "#6B7280"

GROUP_ORDER = [
    "High Risk",
    "Medium Risk",
    "Moderate-Low Risk",
    "Low Risk"
]

GROUP_COLORS = {
    "High Risk": "#D96C6C",
    "Medium Risk": "#E6A96B",
    "Moderate-Low Risk": "#D8C36A",
    "Low Risk": "#7DB8A6",
}

# ─────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>

.main {{
    background-color: {BG_COLOR};
}}

.block-container {{
    padding-top: 2rem;
    padding-bottom: 2rem;
}}

[data-testid="stMetric"] {{
    background: linear-gradient(
        145deg,
        #ffffff,
        #f5f9ff
    );

    border-radius: 24px;

    padding: 24px;

    box-shadow:
    0 10px 28px rgba(0,0,0,0.08),
    inset 0 1px 0 rgba(255,255,255,0.8);

    min-height: 145px;

    border: 1px solid rgba(255,255,255,0.8);
}}

[data-testid="stMetricLabel"] {{
    font-size: 15px;
    font-weight: 600;
    color: {SUBTEXT_COLOR};
}}

[data-testid="stMetricValue"] {{
    font-size: 34px;
    font-weight: 800;
    color: {TEXT_COLOR};
}}

[data-testid="stMetricDelta"] {{
    font-size: 13px;
}}

div[data-testid="stPlotlyChart"] {{

    background: linear-gradient(
        145deg,
        #ffffff,
        #f5f9ff
    );

    border-radius: 24px;

    padding: 16px;

    box-shadow:
    0 10px 28px rgba(0,0,0,0.08),
    inset 0 1px 0 rgba(255,255,255,0.8);

    margin-bottom: 20px;
}}

h1, h2, h3 {{
    color: {TEXT_COLOR};
}}

</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():

    df = pd.read_excel(
        "final_result_prediction.xlsx"
    )

    rename_map = {
        "1. High Risk": "High Risk",
        "2. Medium Risk": "Medium Risk",
        "3. Moderate-Low Risk": "Moderate-Low Risk",
        "4. Low Risk": "Low Risk"
    }

    df["decile_group"] = (
        df["decile_group"]
        .map(rename_map)
    )

    df["decile_group"] = pd.Categorical(
        df["decile_group"],
        categories=GROUP_ORDER,
        ordered=True
    )

    return df

raw_df = load_data()

# ─────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────
with st.sidebar:

    st.title("🏦 Loan")

    st.caption(
        "Executive Command Center"
    )

    st.divider()

    term_opt = ["All"] + sorted(
        raw_df["term"].unique()
    )

    sel_term = st.selectbox(
        "Loan Term",
        options=term_opt,
        index=0
    )

    st.markdown(
        "### Interest Rate Range (%)"
    )
    
    abs_min = float(
        raw_df["int_rate"].min()
    )
    
    abs_max = float(
        raw_df["int_rate"].max()
    )
    
    # OPTION ALL
    use_all_ir = st.checkbox(
        "All Interest Rates",
        value=True
    )
    
    if use_all_ir:
    
        ir_min = abs_min
        ir_max = abs_max
    
        st.caption(
            f"Using full range: {abs_min:.2f}% - {abs_max:.2f}%"
        )
    
    else:
    
        col_a, col_b = st.columns(2)
    
        ir_min = col_a.number_input(
            "Min",
            min_value=abs_min,
            max_value=abs_max,
            value=abs_min,
            step=0.5,
            format="%.2f"
        )
    
        ir_max = col_b.number_input(
            "Max",
            min_value=abs_min,
            max_value=abs_max,
            value=abs_max,
            step=0.5,
            format="%.2f"
        )


    st.divider()

    st.caption(
        "Filters affect all charts & KPIs"
    )

# ─────────────────────────────────────────────────────────────────
# APPLY FILTERS
# ─────────────────────────────────────────────────────────────────
df = raw_df[
    raw_df["int_rate"].between(
        ir_min,
        ir_max
    )
].copy()

if sel_term != "All":

    df = df[
        df["term"] == sel_term
    ]

# ─────────────────────────────────────────────────────────────────
# EMPLOYMENT BUCKET
# ─────────────────────────────────────────────────────────────────
df["emp_bucket"] = pd.cut(
    df["emp_length_int"],
    bins=[-1, 1, 3, 5, 7, 10],
    labels=[
        "<1 yr",
        "1–3 yrs",
        "4–5 yrs",
        "6–7 yrs",
        "8–10+ yrs"
    ]
)

# ─────────────────────────────────────────────────────────────────
# SQLITE
# ─────────────────────────────────────────────────────────────────
conn = sqlite3.connect(":memory:")

df.to_sql(
    "loan_data",
    conn,
    index=False,
    if_exists="replace"
)

# ─────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────
st.title(
    "Loan Executive Dashboard"
)

st.caption(
    f"""
Executive Portfolio Risk Monitoring •
Updated {datetime.now().strftime('%d %b %Y %H:%M')}
"""
)

# ─────────────────────────────────────────────────────────────────
# KPI SECTION
# ─────────────────────────────────────────────────────────────────
total = len(df)

high_n = (
    df["decile_group"] == "High Risk"
).sum()

high_pct = round(
    high_n / total * 100,
    1
) if total else 0

avg_ir = round(
    df["int_rate"].mean(),
    2
)

avg_inc = int(
    df["annual_inc"].mean()
)

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.metric(
        "📁 Total Loans",
        f"{total:,}"
    )

with k2:

    st.metric(
        label="⚠️ High Risk Rate",
        value=f"{high_pct}%",
        delta=f"{high_n:,} loans",
        delta_color="inverse"
    )

with k3:
    st.metric(
        "💰 Avg Interest Rate",
        f"{avg_ir}%"
    )

with k4:
    st.metric(
        "👤 Avg Annual Income",
        f"${avg_inc:,.0f}"
    )

# ─────────────────────────────────────────────────────────────────
# LEGEND
# ─────────────────────────────────────────────────────────────────
fig_legend = go.Figure()

for g in GROUP_ORDER:

    fig_legend.add_trace(
        go.Bar(
            name=g,
            x=[0],
            y=[0],

            marker=dict(
                color=GROUP_COLORS[g],

                line=dict(
                    color="white",
                    width=1.5
                )
            ),

            showlegend=True
        )
    )

fig_legend.update_layout(

    height=60,

    margin=dict(
        l=0,
        r=0,
        t=0,
        b=0
    ),

    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",

    legend=dict(
        orientation="h",

        yanchor="middle",
        y=0.5,

        xanchor="center",
        x=0.5,

        font=dict(
            size=14,
            color=TEXT_COLOR
        ),

        bgcolor="rgba(255,255,255,0.7)",
        bordercolor="rgba(255,255,255,0.3)",
        borderwidth=1
    ),

    xaxis=dict(
        visible=False
    ),

    yaxis=dict(
        visible=False
    )
)

st.plotly_chart(
    fig_legend,
    use_container_width=True,
    config={
        "displayModeBar": False
    }
)

# ─────────────────────────────────────────────────────────────────
# HELPER CHART 
# ─────────────────────────────────────────────────────────────────
def pct_stacked_bar(
    df,
    col,
    title,
    cat_order=None,
    horizontal=False,
    height=360
):

    grp = (
        df.groupby(
            [col, "decile_group"],
            observed=True
        )
        .size()
        .reset_index(name="count")
    )

    cats = (
        cat_order
        if cat_order
        else sorted(df[col].dropna().unique())
    )

    totals = (
        grp.groupby(
            col,
            observed=True
        )["count"]
        .sum()
        .to_dict()
    )

    fig = go.Figure()

    for g in GROUP_ORDER:

        sub = grp[
            grp["decile_group"] == g
        ]

        pcts = []
        texts = []

        for c in cats:

            cnt = sub[
                sub[col] == c
            ]["count"].sum()

            tot = totals.get(c, 1)

            pct = round(
                cnt / tot * 100,
                1
            )

            pcts.append(pct)

            texts.append(
                f"{pct}% ({cnt})"
            )

        if horizontal:

            fig.add_trace(
                go.Bar(
                    name=g,

                    y=[str(c) for c in cats],

                    x=pcts,

                    orientation="h",

                    marker=dict(
                        color=GROUP_COLORS[g],

                        line=dict(
                            color="white",
                            width=1.2
                        )
                    ),

                    text=texts,

                    textposition="inside",

                    insidetextanchor="middle",

                    textangle=0,

                    textfont=dict(
                        size=12,
                        color="white"
                    ),

                    showlegend=False
                )
            )

        else:

            fig.add_trace(
                go.Bar(
                    name=g,

                    x=[str(c) for c in cats],

                    y=pcts,

                    marker=dict(
                        color=GROUP_COLORS[g],

                        line=dict(
                            color="white",
                            width=1.2
                        )
                    ),

                    text=texts,

                    textposition="inside",

                    insidetextanchor="middle",

                    textangle=0,

                    textfont=dict(
                        size=12,
                        color="white"
                    ),

                    showlegend=False
                )
            )

    fig.update_layout(

        barmode="stack",

        title=dict(
            text=title,

            font=dict(
                size=22,
                color=TEXT_COLOR
            )
        ),

        height=height,

        paper_bgcolor="white",

        plot_bgcolor="white",

        font=dict(
            family="Arial",
            size=13,
            color=TEXT_COLOR
        ),

        margin=dict(
            l=10,
            r=10,
            t=60,
            b=20
        ),

        xaxis=dict(
            showgrid=False,
            zeroline=False,
            tickangle=0,
            title=""
        ),

        yaxis=dict(
            showgrid=False,
            zeroline=False,
            tickangle=0,
            title=""
        )
    )

    return fig

# ─────────────────────────────────────────────────────────────────
# CHART 1
# ─────────────────────────────────────────────────────────────────
st.plotly_chart(
    pct_stacked_bar(
        df,
        "grade",
        "Risk Distribution by Loan Grade",
        cat_order=list("ABCDEFG"),
        height=340
    ),
    use_container_width=True,
    config={
        "displayModeBar": False
    }
)

# ─────────────────────────────────────────────────────────────────
# CHART 2
# ─────────────────────────────────────────────────────────────────
pur_order = (
    df.groupby("purpose")["loan_id"]
    .count()
    .sort_values(ascending=True)
    .index
    .tolist()
)

st.plotly_chart(
    pct_stacked_bar(
        df,
        "purpose",
        "Risk Distribution by Loan Purpose",
        cat_order=pur_order,
        horizontal=True,
        height=500
    ),
    use_container_width=True,
    config={
        "displayModeBar": False
    }
)

# ─────────────────────────────────────────────────────────────────
# ROW CHARTS
# ─────────────────────────────────────────────────────────────────
row_a, row_b = st.columns(2)

with row_a:

    st.plotly_chart(
        pct_stacked_bar(
            df,
            "home_ownership",
            "Risk Distribution by Home Ownership",
            cat_order=[
                "RENT",
                "MORTGAGE",
                "OWN"
            ]
        ),
        use_container_width=True,
        config={
            "displayModeBar": False
        }
    )

with row_b:

    st.plotly_chart(
        pct_stacked_bar(
            df,
            "emp_bucket",
            "Risk Distribution by Employment Length",
            cat_order=[
                "<1 yr",
                "1–3 yrs",
                "4–5 yrs",
                "6–7 yrs",
                "8–10+ yrs"
            ]
        ),
        use_container_width=True,
        config={
            "displayModeBar": False
        }
    )

# ─────────────────────────────────────────────────────────────────
# SECOND ROW
# ─────────────────────────────────────────────────────────────────
row_c, row_d = st.columns(2)

with row_c:

    st.plotly_chart(
        pct_stacked_bar(
            df,
            "verification_status",
            "Risk Distribution by Verification Status",
            cat_order=[
                "Verified",
                "Source Verified",
                "Not Verified"
            ]
        ),
        use_container_width=True,
        config={
            "displayModeBar": False
        }
    )

with row_d:

    fig_inc = go.Figure()

    for g in GROUP_ORDER:

        subset = df[
            df["decile_group"] == g
        ]["annual_inc"]

        fig_inc.add_trace(
            go.Box(
                y=subset,

                name=g,

                marker_color=GROUP_COLORS[g],

                boxmean="sd",

                marker_size=4,

                showlegend=False
            )
        )

    fig_inc.update_layout(

        title=dict(
            text="Annual Income Distribution",

            font=dict(
                size=22,
                color=TEXT_COLOR
            )
        ),

        plot_bgcolor="rgba(0,0,0,0)",

        paper_bgcolor="rgba(0,0,0,0)",

        margin=dict(
            l=10,
            r=10,
            t=60,
            b=10
        ),

        height=340,

        font=dict(
            family="Arial",
            size=13,
            color=TEXT_COLOR
        ),

        xaxis=dict(
            showgrid=False,
            tickangle=0
        ),

        yaxis=dict(
            showgrid=False,
            title="Annual Income ($)"
        )
    )

    st.plotly_chart(
        fig_inc,
        use_container_width=True,
        config={
            "displayModeBar": False
        }
    )

# ─────────────────────────────────────────────────────────────────
# DTI KPI SECTION
# ─────────────────────────────────────────────────────────────────
st.subheader(
    "💳 Average Debt-to-Income Ratio"
)

dti_cols = st.columns(4)

ICONS = {
    "High Risk": "🚨",
    "Medium Risk": "⚠️",
    "Moderate-Low Risk": "📊",
    "Low Risk": "🛡️"
}

for i, g in enumerate(GROUP_ORDER):

    avg_dti = df[
        df["decile_group"] == g
    ]["dti"].mean()

    val = (
        f"{avg_dti:.1f}%"
        if not np.isnan(avg_dti)
        else "N/A"
    )

    count_group = len(
        df[df["decile_group"] == g]
    )


    with dti_cols[i]:

        risk_delta_color = {
            "High Risk": "inverse",          # merah
            "Medium Risk": "off",            # default
            "Moderate-Low Risk": "off",      # default
            "Low Risk": "normal"             # hijau
        }
    
        st.metric(
            label=f"{ICONS[g]} {g}",
            value=val,
            delta=f"{count_group:,} loans",
            delta_color=risk_delta_color[g]
        )

# ─────────────────────────────────────────────────────────────────
# CHATBOT
# ─────────────────────────────────────────────────────────────────
st.divider()

st.subheader(
    "✦ ARIA — AI Risk Advisor"
)

st.caption(
    "Powered by Gemini Text-to-SQL"
)

# ─────────────────────────────────────────────────────────────────
# API KEY INPUT
# ─────────────────────────────────────────────────────────────────
user_api_key = st.text_input(
    "Enter Gemini API Key",
    type="password",
    placeholder="Paste your Gemini API key here..."
)

# ─────────────────────────────────────────────────────────────────
# CREATE CLIENT ONLY IF API EXISTS
# ─────────────────────────────────────────────────────────────────
client = None

if user_api_key:

    try:

        client = genai.Client(
            api_key=user_api_key
        )

    except Exception as e:

        st.error(
            f"Invalid API Key: {str(e)}"
        )

# ─────────────────────────────────────────────────────────────────
# TEXT TO SQL
# ─────────────────────────────────────────────────────────────────
def build_sql_prompt(question):

    return f"""
You are an expert Text-to-SQL generator.

Convert user questions into VALID SQLite SQL queries.

DATABASE TABLE:
loan_data

COLUMNS:
- loan_id (TEXT)
- grade (TEXT)
- home_ownership (TEXT)
- purpose (TEXT)
- verification_status (TEXT)
- term (TEXT)
- emp_length_int (INTEGER)  -- 0=<1yr, 10=10+yrs
- mth_since_issue_d (INTEGER)
- int_rate (FLOAT)
- mths_since_earliest_cr_line (INTEGER)
- acc_now_delinq (INTEGER)
- inq_last_6mnths (INTEGER)
- annual_inc (INTEGER)
- dti (FLOAT)
- decile (INTEGER)          -- 1=highest risk, 10=lowest risk
- decile_group (TEXT)       -- "High Risk", "Medium Risk", "Moderate-Low Risk", "Low Risk"

STRICT RULES:
1. ONLY generate SQL. No explanation. No markdown.
2. ONLY use SQLite syntax and table loan_data.
3. If unrelated: return exactly INVALID_QUERY


QUESTION:
{question}
"""


def generate_sql(question):

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=build_sql_prompt(question)
    )

    sql = (
        response.text
        .replace("```sql", "")
        .replace("```", "")
        .strip()
    )

    return sql

def summarize_result(
    question,
    result_df
):

    prompt = f"""
You are ARIA, executive banking AI advisor.
Answer professionally based ONLY on the SQL result below.

QUESTION:
{question}

SQL RESULT:
{result_df.to_string(index=False)}

RULES: Be concise. Executive tone. Give insights. Do NOT hallucinate.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text

# ─────────────────────────────────────────────────────────────────
# CHAT HISTORY
# ─────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:

    st.session_state.messages = [
        {
            "role": "assistant",
            "content":
            """

Hello, I am **ARIA**.\n\n
Ask me anything about:\n
- Risk distribution across decile groups\n
- Grade / purpose / home ownership breakdown\n
- Delinquency, DTI, income segmentation\n
- Interest rate & verification insights\n
- Employment length & decile analysis

            """
        }
    ]

# ─────────────────────────────────────────────────────────────────
# DISPLAY CHAT
# ─────────────────────────────────────────────────────────────────
for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):

        st.markdown(msg["content"])

# ─────────────────────────────────────────────────────────────────
# USER INPUT
# ─────────────────────────────────────────────────────────────────
if prompt := st.chat_input(
    "Ask anything about the loan portfolio..."
):

    with st.chat_message("user"):

        st.markdown(prompt)

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("assistant"):

        try:

            sql_query = generate_sql(prompt)

            if sql_query == "INVALID_QUERY":

                reply = (
                    "That question is outside "
                    "the available dataset."
                )

                st.markdown(reply)

            else:

                with st.expander(
                    "Generated SQL"
                ):

                    st.code(
                        sql_query,
                        language="sql"
                    )

                result_df = pd.read_sql_query(
                    sql_query,
                    conn
                )

                st.subheader(
                    "Query Result"
                )

                st.dataframe(
                    result_df,
                    use_container_width=True
                )

                reply = summarize_result(
                    prompt,
                    result_df
                )

                st.markdown(reply)

            st.session_state.messages.append({
                "role": "assistant",
                "content": reply
            })

        except Exception as e:

            st.error(
                f"❌ Error: {str(e)}"
            )

# ─────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────
st.divider()

st.caption("""Model: Gemini 2.5 Flash · Features: Text-to-SQL · Natural language querying · Executive AI summaries""")