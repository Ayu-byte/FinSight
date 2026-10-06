from pathlib import Path
import html
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / 'src') not in sys.path:
    sys.path.append(str(ROOT / 'src'))

from analytics.insights import (  # noqa: E402
    behavioral_summary,
    budget_summary,
    budget_vs_actual,
    calculate_savings_goal,
    derived_insights,
    detect_recurring_expenses,
    enrich_transactions,
    filter_transactions,
    generate_insights,
    kpis,
    load_budgets,
    load_data,
    month_over_month,
    monthly_trend,
    persona_category_matrix,
    spending_by_category,
    top_merchants,
)
from analytics.anomalies import anomaly_summary, detect_spending_anomalies  # noqa: E402
from analytics.benchmarking import benchmark_insights, calculate_peer_benchmarks  # noqa: E402

st.set_page_config(page_title='FinSight', page_icon='₹', layout='wide', initial_sidebar_state='collapsed')

COLOR_SEQUENCE = ['#14b8a6', '#6366f1', '#f97316', '#ef4444', '#38bdf8', '#8b5cf6', '#22c55e', '#ec4899', '#eab308', '#64748b']
FLOW_COLORS = {'Income': '#10b981', 'Expense': '#ef4444'}
BUDGET_COLORS = {'Budget': '#6366f1', 'Actual': '#f97316'}
PERIOD_COLORS = {'Previous Month': '#94a3b8', 'Current Month': '#14b8a6'}
MONTH_LABELS = {month: pd.Timestamp(year=2025, month=month, day=1).strftime('%B') for month in range(1, 13)}


def apply_visual_theme() -> None:
    st.markdown(
        '''
        <style>
        :root {
            --fs-primary: #0f766e;
            --fs-accent: #6366f1;
            --fs-soft: #ecfeff;
            --fs-border: rgba(100, 116, 139, .20);
        }
        .stApp {
            background:
                radial-gradient(circle at 88% 4%, rgba(99, 102, 241, .10), transparent 24rem),
                radial-gradient(circle at 18% 12%, rgba(20, 184, 166, .10), transparent 26rem),
                var(--background-color);
        }
        .block-container { max-width: 1480px; padding-top: 1.6rem; padding-bottom: 3rem; }
        [data-testid="stSidebar"] {
            border-right: 1px solid var(--fs-border);
            background: linear-gradient(180deg, rgba(15, 118, 110, .09), rgba(99, 102, 241, .04));
        }
        [data-testid="stSidebar"] h2 { color: var(--fs-primary); letter-spacing: -.02em; }
        .fs-hero {
            position: relative;
            overflow: hidden;
            padding: 1.45rem 1.65rem;
            margin-bottom: 1.15rem;
            border: 1px solid rgba(20, 184, 166, .28);
            border-radius: 22px;
            background: linear-gradient(120deg, rgba(15, 118, 110, .96), rgba(67, 56, 202, .92));
            color: white;
            box-shadow: 0 18px 45px rgba(15, 118, 110, .16);
            animation: fs-rise .55s ease-out both;
        }
        .fs-hero::after {
            content: '';
            position: absolute;
            width: 230px; height: 230px; right: -65px; top: -115px;
            border-radius: 50%; border: 42px solid rgba(255,255,255,.09);
        }
        .fs-kicker { font-size: .75rem; font-weight: 750; letter-spacing: .14em; opacity: .82; }
        .fs-hero h1 { color: white; margin: .2rem 0 .15rem; font-size: clamp(2rem, 4vw, 3.2rem); letter-spacing: -.045em; }
        .fs-hero p { margin: 0; max-width: 720px; color: rgba(255,255,255,.86); }
        [data-testid="stMetric"] {
            padding: 1rem 1.05rem;
            border: 1px solid var(--fs-border);
            border-radius: 16px;
            background: color-mix(in srgb, var(--background-color) 93%, #14b8a6 7%);
            box-shadow: 0 8px 24px rgba(15, 23, 42, .05);
            transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
            animation: fs-rise .45s ease-out both;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-3px);
            border-color: rgba(20, 184, 166, .48);
            box-shadow: 0 14px 30px rgba(15, 118, 110, .10);
        }
        [data-testid="stMetricValue"] {
            color: var(--fs-primary);
            letter-spacing: -.035em;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: .4rem; padding: .35rem; border: 1px solid var(--fs-border);
            border-radius: 14px; background: rgba(148, 163, 184, .08);
        }
        .stTabs [data-baseweb="tab"] { border-radius: 10px; padding: .55rem .95rem; }
        .stTabs [aria-selected="true"] { background: rgba(20, 184, 166, .14); color: var(--fs-primary); }
        .stTabs [data-baseweb="tab-highlight"] { background-color: #14b8a6; }
        [data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {
            border: 1px solid var(--fs-border); border-radius: 16px; overflow: hidden;
            background: color-mix(in srgb, var(--background-color) 96%, #14b8a6 4%);
        }
        div[data-baseweb="select"] > div:focus-within,
        [data-testid="stNumberInput"] input:focus,
        [data-testid="stTextInput"] input:focus { border-color: #14b8a6 !important; box-shadow: 0 0 0 1px #14b8a6 !important; }
        .stSlider [role="slider"] { background-color: #0f766e; border-color: #0f766e; }
        .stAlert { border-radius: 14px; }
        .fs-insights-panel {
            margin: 1.2rem 0 1rem;
            padding: 1rem;
            border: 1px solid rgba(20, 184, 166, .22);
            border-radius: 18px;
            background: linear-gradient(135deg, rgba(20, 184, 166, .10), rgba(99, 102, 241, .07));
            box-shadow: 0 12px 30px rgba(15, 23, 42, .05);
            animation: fs-rise .45s ease-out both;
        }
        .fs-insights-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .75rem;
            margin-bottom: .75rem;
        }
        .fs-insights-title { font-weight: 800; letter-spacing: -.02em; }
        .fs-insights-meta { color: #64748b; font-size: .82rem; }
        .fs-insights-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: .65rem;
        }
        .fs-insight-chip {
            display: flex;
            gap: .65rem;
            align-items: flex-start;
            min-height: 72px;
            padding: .72rem .8rem;
            border: 1px solid rgba(100, 116, 139, .17);
            border-radius: 14px;
            background: color-mix(in srgb, var(--background-color) 94%, white 6%);
        }
        .fs-insight-dot {
            width: .72rem;
            height: .72rem;
            flex: 0 0 .72rem;
            margin-top: .24rem;
            border-radius: 999px;
            background: #14b8a6;
            box-shadow: 0 0 0 4px rgba(20, 184, 166, .13);
        }
        .fs-insight-chip.high .fs-insight-dot {
            background: #f97316;
            box-shadow: 0 0 0 4px rgba(249, 115, 22, .15);
        }
        .fs-insight-chip.behavior .fs-insight-dot {
            background: #6366f1;
            box-shadow: 0 0 0 4px rgba(99, 102, 241, .14);
        }
        .fs-insight-message { font-size: .93rem; line-height: 1.35; }
        @keyframes fs-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; }
        }
        @media (max-width: 640px) {
            .block-container { padding: 1.8rem .9rem 2rem; }
            .fs-hero { padding: 1.1rem; margin: .35rem 0 .85rem; border-radius: 18px; }
            .fs-hero h1 { font-size: 2.25rem; line-height: 1.05; }
            .fs-hero p { font-size: .98rem; }
            .stTabs [data-baseweb="tab-list"] { overflow-x: auto; flex-wrap: nowrap; }
            .stTabs [data-baseweb="tab"] { white-space: nowrap; }
            [data-testid="stMetric"] { padding: .85rem; }
            [data-testid="stMetricValue"] { font-size: 2rem; }
            .fs-insights-panel { padding: .85rem; }
            .fs-insights-head { display: block; }
            .fs-insights-grid { grid-template-columns: 1fr; }
        }
        </style>
        ''',
        unsafe_allow_html=True,
    )


apply_visual_theme()


def rupee(value: float) -> str:
    return f'₹{value:,.0f}'


def pct(value: float | None) -> str:
    return 'N/A' if value is None or pd.isna(value) else f'{value:.1f}%'


def ordinal(value: float | None) -> str:
    if value is None or pd.isna(value):
        return 'N/A'
    rounded = int(round(float(value)))
    if 11 <= rounded % 100 <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(rounded % 10, 'th')
    return f'{rounded}{suffix}'


def render_smart_insights(insights: list[dict[str, object]], visible_count: int = 2) -> None:
    visible = insights[:visible_count]
    hidden = insights[visible_count:]
    chips = []
    for insight in visible:
        severity = 'high' if insight.get('severity') == 'high' else 'normal'
        chips.append(
            '<div class="fs-insight-chip {severity}"><span class="fs-insight-dot"></span>'
            '<div class="fs-insight-message">{message}</div></div>'.format(
                severity=severity,
                message=html.escape(str(insight['message'])),
            )
        )

    st.markdown(
        '''
        <div class="fs-insights-panel">
            <div class="fs-insights-head">
                <div class="fs-insights-title">Smart insights</div>
                <div class="fs-insights-meta">Top {visible_count} shown · {total_count} total</div>
            </div>
            <div class="fs-insights-grid">{chips}</div>
        </div>
        '''.format(
            visible_count=len(visible),
            total_count=len(insights),
            chips=''.join(chips),
        ),
        unsafe_allow_html=True,
    )

    if hidden:
        with st.expander(f'Show {len(hidden)} more smart insight{"s" if len(hidden) != 1 else ""}'):
            for insight in hidden:
                st.write(f'- {insight["message"]}')


def render_behavior_summary(notes: list[str], visible_count: int = 3) -> None:
    visible = notes[:visible_count]
    hidden = notes[visible_count:]
    chips = []
    for note in visible:
        chips.append(
            '<div class="fs-insight-chip behavior"><span class="fs-insight-dot"></span>'
            '<div class="fs-insight-message">{message}</div></div>'.format(
                message=html.escape(note),
            )
        )

    st.markdown(
        '''
        <div class="fs-insights-panel">
            <div class="fs-insights-head">
                <div class="fs-insights-title">Behavior summary</div>
                <div class="fs-insights-meta">{visible_count} quick pattern{plural}</div>
            </div>
            <div class="fs-insights-grid">{chips}</div>
        </div>
        '''.format(
            visible_count=len(visible),
            plural='' if len(visible) == 1 else 's',
            chips=''.join(chips),
        ),
        unsafe_allow_html=True,
    )

    if hidden:
        with st.expander(f'Show {len(hidden)} more behavior note{"s" if len(hidden) != 1 else ""}'):
            for note in hidden:
                st.write(f'- {note}')


def money_axis(fig):
    fig.update_layout(
        yaxis_tickprefix='₹',
        hovermode='x unified',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'family': 'Inter, ui-sans-serif, system-ui'},
        margin={'l': 25, 'r': 20, 't': 55, 'b': 25},
    )
    return fig


def animate_chart(fig):
    """Apply consistent motion and visual polish when a chart first draws or updates."""
    fig.update_layout(
        transition={'duration': 500, 'easing': 'cubic-in-out'},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'family': 'Inter, ui-sans-serif, system-ui'},
        margin={'l': 25, 'r': 20, 't': 55, 'b': 25},
    )
    return fig


@st.cache_data
def cached_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    users, transactions = load_data()
    budgets = load_budgets()
    return users, transactions, enrich_transactions(users, transactions), budgets


try:
    users_df, transactions_df, enriched, budgets_df = cached_data()
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

st.markdown(
    '''
    <div class="fs-hero">
        <div class="fs-kicker">PERSONAL FINANCE, MADE VISIBLE</div>
        <h1>FinSight</h1>
        <p>Explore spending patterns, stay ahead of budgets, and turn everyday transactions into clearer financial decisions.</p>
    </div>
    ''',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header('FinSight controls')
    st.caption('Shape the dashboard around a cohort or one student.')
    st.subheader('Overview scope')
    persona_options = sorted(enriched['persona'].dropna().unique())
    selected_persona = st.selectbox('Persona', ['All Personas'] + persona_options)
    selected_personas = None if selected_persona == 'All Personas' else [selected_persona]

    context_source = enriched if selected_personas is None else enriched[enriched['persona'].isin(selected_personas)]
    user_options = context_source[['user_id', 'name']].drop_duplicates().sort_values('user_id')
    user_labels = {f'{row.user_id} - {row.name}': int(row.user_id) for row in user_options.itertuples()}
    selected_user_labels = st.multiselect('Students for Overview', list(user_labels.keys()), help='Only the Overview tab uses this multi-select for aggregate KPIs and charts.')
    selected_users = [user_labels[label] for label in selected_user_labels]

    st.divider()
    st.subheader('Student deep dive')
    detail_pool = user_options[user_options['user_id'].isin(selected_users)] if selected_users else user_options
    detail_labels = {f'{row.user_id} - {row.name}': int(row.user_id) for row in detail_pool.itertuples()}
    selected_detail_label = st.selectbox('Student for Budget, Trends, Recurring, and Planner', list(detail_labels.keys()), help='Detailed tabs analyze this single student.') if detail_labels else None
    analysis_user_id = detail_labels[selected_detail_label] if selected_detail_label else None
    selected_month = st.selectbox('Month', list(MONTH_LABELS), format_func=lambda month: MONTH_LABELS[month], index=9)

context_data = filter_transactions(enriched, personas=selected_personas, users=selected_users)
detail_student_name = selected_detail_label.split(' - ', 1)[1] if selected_detail_label else 'No student selected'
if context_data.empty:
    st.warning('No transactions are available for the selected persona/student context.')
    st.stop()

expense_categories = sorted(enriched.loc[enriched['type'].eq('Expense'), 'category'].dropna().unique())
overview_tab, budget_tab, trends_tab, anomalies_tab, benchmarking_tab, recurring_tab, planner_tab = st.tabs([
    'Overview', 'Budget', 'Trends', 'Anomalies', 'Benchmarking',
    'Recurring', 'Savings Planner',
])

with overview_tab:
    st.subheader('Financial snapshot')
    st.caption('A high-level view of cash flow, spending concentration, and payment behavior.')
    metrics = kpis(context_data)
    top_cols = st.columns(3)
    top_cols[0].metric('Total Income', rupee(metrics['total_income']))
    top_cols[1].metric('Total Expenses', rupee(metrics['total_expenses']))
    top_cols[2].metric('Net Savings', rupee(metrics['net_savings']))
    bottom_cols = st.columns(2)
    bottom_cols[0].metric('Savings Rate', f'{metrics["savings_rate"]:.1f}%')
    bottom_cols[1].metric('Average Transaction Value', rupee(metrics['average_transaction_value']))

    left, right = st.columns((1.35, 1))
    with left:
        trend = monthly_trend(context_data)
        if trend.empty:
            st.info('No monthly trend available for this context.')
        else:
            fig = px.line(trend, x='month_name', y='amount', color='type', markers=True, color_discrete_map=FLOW_COLORS, title='Income vs Expenses Over Time')
            fig.update_layout(yaxis_title='Amount', xaxis_title='Month', legend_title='Type')
            st.plotly_chart(animate_chart(money_axis(fig)), width='stretch')
    with right:
        category_spend = spending_by_category(context_data).head(10)
        if category_spend.empty:
            st.info('No expense categories available for this context.')
        else:
            fig = px.bar(category_spend, x='amount', y='category', orientation='h', color_discrete_sequence=COLOR_SEQUENCE, title='Top Spending Categories')
            fig.update_layout(xaxis_title='Amount', yaxis_title='', yaxis={'categoryorder': 'total ascending'}, xaxis_tickprefix='₹')
            st.plotly_chart(animate_chart(fig), width='stretch')

    left, right = st.columns(2)
    with left:
        merchant_df = top_merchants(context_data, limit=10)
        if merchant_df.empty:
            st.info('No merchant spending available for this context.')
        else:
            fig = px.bar(merchant_df, x='amount', y='merchant', orientation='h', color='transactions', color_continuous_scale='Blues', title='Top Merchants by Spend')
            fig.update_layout(xaxis_title='Amount', yaxis_title='', yaxis={'categoryorder': 'total ascending'}, xaxis_tickprefix='₹')
            st.plotly_chart(animate_chart(fig), width='stretch')
    with right:
        payment_df = context_data.groupby('payment_method', as_index=False)['transaction_id'].count().rename(columns={'transaction_id': 'transactions'})
        if payment_df.empty:
            st.info('No payment method data available for this context.')
        else:
            fig = px.pie(payment_df, names='payment_method', values='transactions', hole=0.45, color_discrete_sequence=COLOR_SEQUENCE, title='Payment Method Distribution')
            st.plotly_chart(animate_chart(fig), width='stretch')

    if analysis_user_id is None or budgets_df.empty:
        st.info('Select a detailed student and ensure budgets are generated to view data-driven insights.')
    else:
        smart_insights = generate_insights(enriched, budgets_df, users_df, analysis_user_id, selected_month, 2025)
        if smart_insights:
            render_smart_insights(smart_insights)
        else:
            st.info('No significant deterministic insights for this student/month selection.')

    behavior_notes = derived_insights(context_data)
    if behavior_notes:
        render_behavior_summary(behavior_notes)

    with st.expander('Explore behavior charts'):
        left, right = st.columns(2)
        with left:
            matrix = persona_category_matrix(context_data)
            if matrix.empty:
                st.info('No persona/category matrix available.')
            else:
                fig = px.imshow(
                    matrix,
                    aspect='auto',
                    color_continuous_scale='YlGnBu',
                    title='Persona and Category Spend Matrix',
                    labels={'color': 'Spend (INR)'},
                )
                fig.update_layout(xaxis_title='Category', yaxis_title='Persona', coloraxis_colorbar={'tickprefix': '₹'})
                fig.update_traces(hovertemplate='Persona=%{y}<br>Category=%{x}<br>Spend=₹%{z:,.0f}<extra></extra>')
                st.plotly_chart(animate_chart(fig), width='stretch')
        with right:
            behavior = behavioral_summary(context_data)
            if behavior.empty:
                st.info('No weekday/weekend expense data available.')
            else:
                fig = px.bar(behavior, x='persona', y='amount', color='week_part', barmode='group', color_discrete_sequence=COLOR_SEQUENCE, title='Weekend vs Weekday Spending')
                fig.update_layout(xaxis_title='', yaxis_title='Amount', xaxis_tickangle=-30, yaxis_tickprefix='₹')
                st.plotly_chart(animate_chart(fig), width='stretch')

with budget_tab:
    st.subheader('Budget health')
    st.caption(f'Analyzing {detail_student_name} for {MONTH_LABELS[selected_month]} 2025.')
    if budgets_df.empty:
        st.info('No budget data available. Run python src/generator/generate_budgets.py.')
    elif analysis_user_id is None:
        st.info('Select a detailed student to view budget analysis.')
    else:
        budget_category_filter = st.multiselect('Budget categories', expense_categories, key='budget_categories')
        budget_df = budget_vs_actual(enriched, budgets_df, analysis_user_id, selected_month, 2025, budget_category_filter or None)
        summary = budget_summary(budget_df)
        cols = st.columns(4)
        cols[0].metric('Total Monthly Budget', rupee(summary['total_budget']))
        cols[1].metric('Actual Spending', rupee(summary['actual_spending']))
        cols[2].metric('Budget Variance', rupee(summary['variance']))
        cols[3].metric('Utilization', pct(summary['utilization_pct']))

        if budget_df.empty:
            st.info('No budget data available for this selection.')
        else:
            chart_df = budget_df.melt(id_vars='category', value_vars=['budget_amount', 'actual_amount'], var_name='metric', value_name='amount')
            chart_df['metric'] = chart_df['metric'].map({'budget_amount': 'Budget', 'actual_amount': 'Actual'})
            fig = px.bar(chart_df, x='category', y='amount', color='metric', barmode='group', color_discrete_map=BUDGET_COLORS, title='Budget vs Actual by Category')
            fig.update_layout(xaxis_title='', yaxis_title='Amount', xaxis_tickangle=-30, yaxis_tickprefix='₹')
            st.plotly_chart(animate_chart(fig), width='stretch')

            table = budget_df.copy()
            table['Budget'] = table['budget_amount'].map(rupee)
            table['Actual'] = table['actual_amount'].map(rupee)
            table['Variance'] = table['variance'].map(rupee)
            table['Variance %'] = table['variance_pct'].map(pct)
            table['Utilization %'] = table['budget_utilization_pct'].map(pct)
            st.dataframe(table[['category', 'Budget', 'Actual', 'Variance', 'Variance %', 'Utilization %', 'status']].rename(columns={'category': 'Category', 'status': 'Status'}), width='stretch', hide_index=True)

with trends_tab:
    st.subheader('Spending momentum')
    st.caption(f'Analyzing {detail_student_name}. Month-over-month comparison deliberately includes the immediately preceding calendar month.')
    if analysis_user_id is None:
        st.info('Select a detailed student to view trend analysis.')
    else:
        trend_category_filter = st.multiselect('Trend categories', expense_categories, key='trend_categories')
        mom = month_over_month(enriched, analysis_user_id, selected_month, 2025, trend_category_filter or None)
        cols = st.columns(4)
        cols[0].metric('Current Month Spending', rupee(mom['current_total']))
        cols[1].metric('Previous Month Spending', rupee(mom['previous_total']))
        cols[2].metric('Absolute Change', rupee(mom['change']))
        cols[3].metric('Percentage Change', pct(mom['pct_change']))

        if mom['previous_total'] == 0:
            st.info('Previous-month data is unavailable for this period.')
        comparison = mom['category_comparison']
        if comparison.empty:
            st.info('No expense categories available for this month-over-month comparison.')
        else:
            inc = mom['largest_increase']
            dec = mom['largest_decrease']
            callout_cols = st.columns(2)
            callout_cols[0].info('Largest increase: ' + (f"{inc['category']} ({rupee(inc['change'])})" if inc else 'N/A'))
            callout_cols[1].info('Largest decrease: ' + (f"{dec['category']} ({rupee(abs(dec['change']))})" if dec else 'N/A'))

            chart_df = comparison.melt(id_vars='category', value_vars=['previous_amount', 'current_amount'], var_name='period', value_name='amount')
            chart_df['period'] = chart_df['period'].map({'previous_amount': 'Previous Month', 'current_amount': 'Current Month'})
            fig = px.bar(chart_df, x='category', y='amount', color='period', barmode='group', color_discrete_map=PERIOD_COLORS, title='Previous Month vs Current Month by Category')
            fig.update_layout(xaxis_title='', yaxis_title='Amount', xaxis_tickangle=-30, yaxis_tickprefix='₹')
            st.plotly_chart(animate_chart(fig), width='stretch')

            table = comparison.copy()
            table['Previous Month'] = table['previous_amount'].map(rupee)
            table['Current Month'] = table['current_amount'].map(rupee)
            table['Change'] = table['change'].map(rupee)
            table['Change %'] = table['change_label']
            st.dataframe(table[['category', 'Previous Month', 'Current Month', 'Change', 'Change %']].rename(columns={'category': 'Category'}), width='stretch', hide_index=True)

with anomalies_tab:
    st.subheader('Spending Anomalies')
    st.caption("Transactions are identified using statistical patterns in the student's historical category-level spending. These are unusual expenses, not fraud alerts.")
    if analysis_user_id is None:
        st.info('Select a detailed student to analyze unusual spending.')
    else:
        all_anomalies = detect_spending_anomalies(enriched, analysis_user_id)
        summary = anomaly_summary(enriched, all_anomalies, analysis_user_id)
        cols = st.columns(4)
        cols[0].metric('Anomalies Detected', f"{summary['count']:,}")
        cols[1].metric('Anomalous Spend', rupee(summary['anomalous_spend']))
        cols[2].metric('% of Total Expenses', pct(summary['expense_share_pct']))
        cols[3].metric('Most Affected Category', summary['most_affected_category'])

        anomaly_categories = sorted(all_anomalies['category'].unique()) if not all_anomalies.empty else []
        display_category = st.selectbox('Anomaly category', ['All Categories'] + anomaly_categories)
        shown = all_anomalies if display_category == 'All Categories' else all_anomalies[all_anomalies['category'] == display_category]
        if shown.empty:
            st.info('No statistically significant spending anomalies were detected for this student.')
        else:
            student_expenses = enriched[(enriched['user_id'] == analysis_user_id) & (enriched['type'] == 'Expense')].copy()
            if display_category != 'All Categories':
                student_expenses = student_expenses[student_expenses['category'] == display_category]
            plot_data = student_expenses.merge(
                shown[['transaction_id', 'severity']], on='transaction_id', how='left'
            )
            plot_data['classification'] = plot_data['severity'].fillna('Typical')
            fig = px.scatter(
                plot_data, x='date', y='amount', color='classification', hover_name='merchant',
                hover_data=['category'], color_discrete_map={'Typical': '#94a3b8', 'Moderate': '#f97316', 'High': '#ef4444'},
                title='Expense Transactions Over Time',
            )
            fig.update_layout(xaxis_title='Date', yaxis_title='Amount', yaxis_tickprefix='₹', legend_title='Classification')
            st.plotly_chart(animate_chart(fig), width='stretch')
            st.caption('Typical Amount is the median of this student\u2019s own history in the same category. Medians can look low because everyday small purchases dominate the history, while the Threshold (Q3 + 2.0 \u00d7 IQR) marks the statistical outlier boundary.')
            table = shown.copy()
            table['Date'] = pd.to_datetime(table['date']).dt.strftime('%d %b %Y')
            table['Amount'] = table['amount'].map(rupee)
            table['Typical Amount'] = table['category_median'].map(rupee)
            table['Threshold'] = table['upper_bound'].map(rupee)
            st.dataframe(table[['Date', 'merchant', 'category', 'Amount', 'Typical Amount', 'Threshold', 'severity']].rename(columns={'merchant': 'Merchant', 'category': 'Category', 'severity': 'Severity'}), width='stretch', hide_index=True)

with benchmarking_tab:
    st.subheader('Peer Benchmarking')
    st.caption('Compare normalized monthly behavior with similar students. Medians reduce the effect of unusually large values.')
    if analysis_user_id is None:
        st.info('Select a detailed student to compare peer behavior.')
    else:
        peer_scope = st.radio('Peer Group', ['Same Persona', 'All Students'], horizontal=True)
        benchmark = calculate_peer_benchmarks(enriched, users_df, analysis_user_id, peer_scope=peer_scope)
        if not benchmark['available']:
            st.warning(benchmark['reason'])
        else:
            st.caption(f"Selected Student: {detail_student_name} · Persona: {benchmark['persona']} · Peer Count: {benchmark['peer_count']}")
            result = benchmark['table'].set_index('metric')
            kpi_metrics = ['Average Monthly Expenses', 'Savings Rate', 'Food & Dining', 'Shopping']
            cols = st.columns(4)
            for column, metric in zip(cols, kpi_metrics):
                row = result.loc[metric]
                if row['unit'] == 'percent':
                    column.metric(metric, pct(row['student_value']), f"{row['difference']:+.1f} pp vs median")
                else:
                    column.metric(metric, rupee(row['student_value']), f"{rupee(abs(row['difference']))} {'above' if row['difference'] >= 0 else 'below'} median")

            money = benchmark['table'][benchmark['table']['metric'].isin(['Food & Dining', 'Shopping', 'Transportation', 'Entertainment'])]
            chart = money.melt(id_vars='metric', value_vars=['student_value', 'peer_median'], var_name='series', value_name='amount')
            chart['series'] = chart['series'].map({'student_value': 'You', 'peer_median': 'Peer Median'})
            fig = px.bar(chart, x='amount', y='metric', color='series', barmode='group', orientation='h', color_discrete_map={'You': '#14b8a6', 'Peer Median': '#6366f1'}, title='Average Monthly Category Spending')
            fig.update_layout(xaxis_title='Amount', yaxis_title='', xaxis_tickprefix='₹', legend_title='')
            st.plotly_chart(animate_chart(fig), width='stretch')

            table = benchmark['table'].copy()
            table['You'] = table.apply(lambda row: pct(row['student_value']) if row['unit'] == 'percent' else f"{row['student_value']:.1f}" if row['unit'] == 'count' else rupee(row['student_value']), axis=1)
            table['Peer Median'] = table.apply(lambda row: pct(row['peer_median']) if row['unit'] == 'percent' else f"{row['peer_median']:.1f}" if row['unit'] == 'count' else rupee(row['peer_median']), axis=1)
            table['Difference'] = table.apply(lambda row: f"{row['difference']:+.1f} pp" if row['unit'] == 'percent' else f"{row['difference']:+.1f}" if row['unit'] == 'count' else f"₹{row['difference']:+,.0f}", axis=1)
            table['Difference %'] = table['difference_pct'].map(lambda value: 'N/A' if pd.isna(value) else f'{value:+.1f}%')
            table['Percentile'] = table['percentile'].map(ordinal)
            st.dataframe(table[['metric', 'You', 'Peer Median', 'Difference', 'Difference %', 'Percentile']].rename(columns={'metric': 'Metric'}), width='stretch', hide_index=True)
            for observation in benchmark_insights(benchmark):
                st.info(observation)

with recurring_tab:
    st.subheader('Recurring commitments')
    st.caption('Only strong, independently detected payment patterns appear here.')
    if analysis_user_id is None:
        st.info('Select a detailed student to detect recurring expense patterns.')
    else:
        recurring = detect_recurring_expenses(enriched, analysis_user_id)
        recurring_items = recurring['items']
        cols = st.columns(3)
        cols[0].metric('Likely Recurring Expenses', f'{len(recurring_items):,}')
        cols[1].metric('Monthly Recurring Cost', rupee(recurring['monthly_total']))
        cols[2].metric('Annual Recurring Cost', rupee(recurring['annual_total']))

        if recurring_items.empty:
            st.info('No strong recurring expense patterns detected for this student.')
        else:
            table = recurring_items.copy()
            table['Avg Amount'] = table['average_amount'].map(rupee)
            table['Monthly Cost'] = table['estimated_monthly_cost'].map(rupee)
            st.dataframe(table[['merchant', 'category', 'estimated_frequency', 'Avg Amount', 'Monthly Cost', 'confidence']].rename(columns={'merchant': 'Merchant', 'category': 'Category', 'estimated_frequency': 'Frequency', 'confidence': 'Confidence'}), width='stretch', hide_index=True)
            with st.expander('Detection details'):
                details = recurring_items.copy()
                details['Amount CV'] = details['amount_cv'].map(lambda value: f'{value:.2f}')
                details['Monthly Interval Match'] = details['monthly_interval_share'].map(pct)
                details['Single Txn Month Share'] = details['single_transaction_month_share'].map(pct)
                st.dataframe(details[['merchant', 'transactions', 'distinct_months', 'Amount CV', 'Monthly Interval Match', 'Single Txn Month Share', 'confidence_score']], width='stretch', hide_index=True)

with planner_tab:
    st.subheader('Savings planner')
    st.caption('Adjust controllable categories to explore a realistic path toward your goal.')
    if analysis_user_id is None:
        st.info('Select a detailed student to simulate a savings goal.')
    else:
        inputs, output = st.columns((0.8, 1.2))
        with inputs:
            goal_amount = st.number_input('Savings Goal Amount (₹)', min_value=1, value=25000, step=1000)
            target_months = st.number_input('Target Period (months)', min_value=1, value=6, step=1)
            initial_plan = calculate_savings_goal(enriched, budgets_df, analysis_user_id, float(goal_amount), int(target_months))
            overrides = {}
            if not initial_plan['recommendations'].empty:
                st.caption('What-if reduction percentages')
                for row in initial_plan['recommendations'].itertuples():
                    overrides[row.category] = st.slider(f'{row.category} reduction', 0.0, 30.0, float(row.suggested_reduction_pct), 0.5, format='%.1f%%')
            plan = calculate_savings_goal(enriched, budgets_df, analysis_user_id, float(goal_amount), int(target_months), overrides)

        with output:
            row1 = st.columns(3)
            row1[0].metric('Required Monthly Savings', rupee(plan['required_monthly_savings']))
            row1[1].metric('Current Avg Savings', rupee(plan['current_average_savings']))
            row1[2].metric('Monthly Gap', rupee(plan['monthly_gap']))
            row2 = st.columns(3)
            row2[0].metric('Potential Savings', rupee(plan['potential_monthly_savings']))
            row2[1].metric('Projected Savings', rupee(plan['projected_monthly_savings']))
            row2[2].metric('Remaining Gap', rupee(plan['remaining_gap']))
            projected_months = plan['expected_months_projected']
            st.metric('Estimated Months to Goal', 'N/A' if projected_months is None else f'{projected_months:.1f}')
            st.info(plan['status'])
            st.caption(f"Likely recurring expenses account for approximately {rupee(plan['recurring']['monthly_total'])} per month. This is an analytical estimate, not financial advice.")

        if plan['recommendations'].empty:
            st.info('No discretionary reduction candidates were found from historical spending.')
        else:
            rec_table = plan['recommendations'].copy()
            rec_table['Avg Monthly Spend'] = rec_table['avg_monthly_spend'].map(rupee)
            rec_table['Reduction'] = rec_table['suggested_reduction_pct'].map(pct)
            rec_table['Estimated Saving'] = rec_table['estimated_monthly_saving'].map(rupee)
            st.dataframe(rec_table[['category', 'Avg Monthly Spend', 'Reduction', 'Estimated Saving', 'reason']].rename(columns={'category': 'Category', 'reason': 'Basis'}), width='stretch', hide_index=True)

        with st.expander('Historical spending basis'):
            profile_table = plan['category_profile'].copy()
            if profile_table.empty:
                st.info('Insufficient expense history to show a spending basis.')
            else:
                profile_table['Avg Monthly Spend'] = profile_table['avg_monthly_spend'].map(rupee)
                profile_table['Expense Share'] = profile_table['share_of_expenses'].map(pct)
                st.dataframe(profile_table[['category', 'Avg Monthly Spend', 'Expense Share']].rename(columns={'category': 'Category'}), width='stretch', hide_index=True)

st.caption(f'{len(context_data):,} transactions in current overview context from {len(transactions_df):,} generated records')


