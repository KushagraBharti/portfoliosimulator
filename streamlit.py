#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy_financial as npf


# App Title
st.set_page_config(page_title="VC Fund Simulator", page_icon="https://atas.vc/img/favicon.png")
st.markdown('<a href="https://atas.vc/"><img src="https://atas.vc/img/logo.png" width="150"></a>', unsafe_allow_html=True)
st.markdown(
    "This open source model was developed by [Andrew Chan](https://www.linkedin.com/in/chandr3w/) "
    "from [Atas VC](https://atas.vc/)."
)

st.title('VC Portfolio Simulator')

stages = ['Pre-Seed', 'Seed', 'Series A', 'Series B']
existing_portfolio_columns = [
    "Company",
    "Entry Stage",
    "Invested Capital ($MM)",
    "Current Stage",
    "Current Ownership (%)",
    "Follow-on Reserve ($MM)",
    "Future Dilution (%)",
    "Failure Probability (%)",
    "Exit Valuation Low ($MM)",
    "Exit Valuation High ($MM)",
    "Expected Exit Year",
]
example_existing_portfolio = pd.DataFrame([
    {
        "Company": "Example GridCo",
        "Entry Stage": "Seed",
        "Invested Capital ($MM)": 1.0,
        "Current Stage": "Seed",
        "Current Ownership (%)": 8.0,
        "Follow-on Reserve ($MM)": 0.5,
        "Future Dilution (%)": 20.0,
        "Failure Probability (%)": 30.0,
        "Exit Valuation Low ($MM)": 25.0,
        "Exit Valuation High ($MM)": 150.0,
        "Expected Exit Year": 6,
    },
    {
        "Company": "Example MineOps",
        "Entry Stage": "Pre-Seed",
        "Invested Capital ($MM)": 0.75,
        "Current Stage": "Pre-Seed",
        "Current Ownership (%)": 10.0,
        "Follow-on Reserve ($MM)": 0.75,
        "Future Dilution (%)": 25.0,
        "Failure Probability (%)": 35.0,
        "Exit Valuation Low ($MM)": 20.0,
        "Exit Valuation High ($MM)": 250.0,
        "Expected Exit Year": 7,
    },
    {
        "Company": "Example SpectrumCo",
        "Entry Stage": "Seed",
        "Invested Capital ($MM)": 1.25,
        "Current Stage": "Seed",
        "Current Ownership (%)": 7.5,
        "Follow-on Reserve ($MM)": 1.0,
        "Future Dilution (%)": 20.0,
        "Failure Probability (%)": 25.0,
        "Exit Valuation Low ($MM)": 40.0,
        "Exit Valuation High ($MM)": 300.0,
        "Expected Exit Year": 6,
    },
])

existing_portfolio_tab = st.tabs(["Existing Portfolio"])[0]
with existing_portfolio_tab:
    st.subheader("Existing Portfolio Inputs")
    include_existing_portfolio = st.checkbox("Include existing portfolio in simulations", value=False)
    use_example_existing_portfolio = st.checkbox("Populate example assumptions", value=False)
    st.caption(
        "Enter current holdings with ownership and reserve assumptions. "
        "Reserves count as additional paid-in capital, and future dilution is applied once before exit. "
        "Leave the table blank if you only want to simulate new deployment."
    )
    existing_portfolio_input = st.data_editor(
        example_existing_portfolio if use_example_existing_portfolio else pd.DataFrame(columns=existing_portfolio_columns),
        num_rows="dynamic",
        column_config={
            "Entry Stage": st.column_config.SelectboxColumn("Entry Stage", options=stages),
            "Current Stage": st.column_config.SelectboxColumn("Current Stage", options=stages + ["Series C", "IPO"]),
            "Invested Capital ($MM)": st.column_config.NumberColumn("Invested Capital ($MM)", min_value=0.0, step=0.1),
            "Current Ownership (%)": st.column_config.NumberColumn("Current Ownership (%)", min_value=0.0, max_value=100.0, step=0.1),
            "Follow-on Reserve ($MM)": st.column_config.NumberColumn("Follow-on Reserve ($MM)", min_value=0.0, step=0.1),
            "Future Dilution (%)": st.column_config.NumberColumn("Future Dilution (%)", min_value=0.0, max_value=100.0, step=1.0),
            "Failure Probability (%)": st.column_config.NumberColumn("Failure Probability (%)", min_value=0.0, max_value=100.0, step=1.0),
            "Exit Valuation Low ($MM)": st.column_config.NumberColumn("Exit Valuation Low ($MM)", min_value=0.0, step=1.0),
            "Exit Valuation High ($MM)": st.column_config.NumberColumn("Exit Valuation High ($MM)", min_value=0.0, step=1.0),
            "Expected Exit Year": st.column_config.NumberColumn("Expected Exit Year", min_value=0, max_value=20, step=1),
        },
    )

# Sidebar inputs
st.sidebar.header('Fund Parameters')
fund_size = st.sidebar.number_input("Fund Size ($MM)", min_value=1, max_value=500, value=100, step=1)
initial_stage = st.sidebar.selectbox('Initial Investment Stage', stages)
stage_index = stages.index(initial_stage)

# Management Fee
st.sidebar.header('Fund Management Fee')
management_fee_pct = st.sidebar.slider('Annual Management Fee (%)', 0.0, 5.0, 2.0, step=0.1)
management_fee_years = st.sidebar.slider('Years Management Fee is Charged', 1, 10, 10, step=1)
deployment_years = st.sidebar.slider('Number of Deployment Years', 1, 10, 5, step=1)

# Robust Portfolio Allocation
st.sidebar.header('Portfolio Allocation (%) per Stage')
valid_stages = stages[stage_index:]
stage_allocations = {}
allocation_values = []
remaining_alloc = 100

num_simulations = st.sidebar.slider('Number of Simulations', 1, 1000, 100)

# Default allocation map
default_allocation_map = {
    'Pre-Seed': 20,
    'Seed': 60,
    'Series A': 10,
    'Series B': 10
}

st.sidebar.header('Portfolio Allocation (%) per Stage')
valid_stages = stages[stage_index:]
stage_allocations = {}
allocation_values = []
remaining_alloc = 100

for i, stage in enumerate(valid_stages):
    default_value = default_allocation_map.get(stage, 0)
    # Cap default at remaining allocation
    default_slider_value = min(default_value, remaining_alloc)

    if i == len(valid_stages) - 1:
        allocation = remaining_alloc
        st.sidebar.write(f"Allocation to {stage}: {allocation}% (auto-set)")
    else:
        max_alloc = remaining_alloc
        if max_alloc == 0:
            allocation = 0
            st.sidebar.write(f"Allocation to {stage}: 0% (auto-set since fully allocated)")
        else:
            allocation = st.sidebar.slider(
                f'Allocation to {stage} (%)',
                min_value=0,
                max_value=max_alloc,
                value=default_slider_value,
                step=5
            )
        remaining_alloc -= allocation
    allocation_values.append(allocation)
    stage_allocations[stage] = allocation

if sum(allocation_values) != 100:
    st.sidebar.warning(f"Total allocation is {sum(allocation_values)}%. Adjust allocations to total exactly 100%.")

st.sidebar.header('Entry Valuations and Check Sizes per Stage ($MM)')
valuations, check_sizes = {}, {}

# Separate out each stage by individual Valuation
# stages = ['Pre-Seed', 'Seed', 'Series A', 'Series B']

valuations['Pre-Seed'] = st.sidebar.slider(f'Entry Valuation Range Pre-Seed', 2, 40, (3, 6), step=1)
check_sizes['Pre-Seed'] = st.sidebar.slider(f'Check Size Range Pre-Seed', 0.1, 3.0, (1.0, 1.5), step=0.1)

valuations['Seed'] = st.sidebar.slider(f'Entry Valuation Range Seed', 4, 50, (8, 15), step=1)
check_sizes['Seed'] = st.sidebar.slider(f'Check Size Range Seed', 0.25, 10.0, (2.0, 5.0), step=0.1)

valuations['Series A'] = st.sidebar.slider(f'Entry Valuation Range Series A', 20, 200, (40, 80), step=1)
check_sizes['Series A'] = st.sidebar.slider(f'Check Size Range Series A', 1.0, 20.0, (5.0, 10.0), step=0.5)

valuations['Series B'] = st.sidebar.slider(f'Entry Valuation Range Series B', 50, 400, (100, 150), step=5)
check_sizes['Series B'] = st.sidebar.slider(f'Check Size Range Series B', 1, 40, (5, 10), step=1)

st.sidebar.header('Stage Progression Probabilities (%)')
prob_advancement = {}
years_to_next = {}
for i in range(stage_index, len(stages)-1):
    if i==0:
        prob_advancement[stages[i]+' to '+stages[i+1]] = st.sidebar.slider(f'{stages[i]} → {stages[i+1]}', 0, 100, 50, step=1)
        years_to_next[stages[i]+' to '+stages[i+1]] = st.sidebar.slider(f'Years from {stages[i]} to {stages[i+1]}', 0, 10, (1,2), step=1)
    elif i==1:
        prob_advancement[stages[i]+' to '+stages[i+1]] = st.sidebar.slider(f'{stages[i]} → {stages[i+1]}', 0, 100, 33, step=1)
        years_to_next[stages[i]+' to '+stages[i+1]] = st.sidebar.slider(f'Years from {stages[i]} to {stages[i+1]}', 0, 10, (1,3), step=1)
        
    elif i==2:
        prob_advancement[stages[i]+' to '+stages[i+1]] = st.sidebar.slider(f'{stages[i]} → {stages[i+1]}', 0, 100, 48, step=1)
        years_to_next[stages[i]+' to '+stages[i+1]] = st.sidebar.slider(f'Years from {stages[i]} to {stages[i+1]}', 0, 10, (1,3), step=1)
        
prob_advancement['Series B to Series C'] = st.sidebar.slider('Series B → Series C', 0, 100, 43, step=1)
prob_advancement['Series C to IPO'] = st.sidebar.slider('Series C → IPO', 0, 100, 28, step=1)
years_to_next['Series B to Series C'] = st.sidebar.slider('Years from Series B to Series C', 0, 10, (1,3), step=1)
years_to_next['Series C to IPO'] = st.sidebar.slider('Years from Series C to IPO', 0, 10, (1,), step=1)

# Series B → Series C and Series C → IPO
#prob_advancement['Series B to Series C'] = st.sidebar.slider('Series B → Series C', 0, 100, 40, step=5)

#prob_advancement['Series C to IPO'] = st.sidebar.slider('Series C → IPO', 0, 100, 20, step=5)

st.sidebar.header('Dilution per Round (%)')
dilution = {}
for i in range(stage_index, len(stages)-1):
    dilution[stages[i]+' to '+stages[i+1]] = st.sidebar.slider(f'Dilution {stages[i]} → {stages[i+1]}', 0, 100, (10,25), step=5)
dilution['Series B to Series C'] = st.sidebar.slider('Dilution Series B → Series C', 0, 100, (10,15), step=5)
dilution['Series C to IPO'] = st.sidebar.slider('Dilution Series C → IPO', 0, 100, (10,15), step=5)

st.sidebar.header('Exit Valuations and Loss Ratio ($MM)')
exit_valuations = {}
zero_probabilities = {}
for stage in valid_stages + ['Series C', 'IPO']:
    if stage == 'Pre-Seed':
        exit_valuations[stage] = st.sidebar.slider(f'Exit Valuation at {stage}', 2, 20, (4, 10), step=1)
        zero_probabilities[stage] = st.sidebar.slider(f'Probability of Total Loss at {stage} (%)', 0, 100, 30, step=5)
    elif stage == 'Seed':
        exit_valuations[stage] = st.sidebar.slider(f'Exit Valuation at {stage}', 2, 40, (5, 10), step=1)
        zero_probabilities[stage] = st.sidebar.slider(f'Probability of Total Loss at {stage} (%)', 0, 100, 30, step=5)

    elif stage == 'Series A':
        exit_valuations[stage] = st.sidebar.slider(f'Exit Valuation at {stage}', 10, 100, (20, 40), step=1)
        zero_probabilities[stage] = st.sidebar.slider(f'Probability of Total Loss at {stage} (%)', 0, 100, 30, step=5)

    elif stage == 'Series B':
        exit_valuations[stage] = st.sidebar.slider(f'Exit Valuation at {stage}', 20, 200, (40, 120), step=1)
        zero_probabilities[stage] = st.sidebar.slider(f'Probability of Total Loss at {stage} (%)', 0, 100, 20, step=5)
    elif stage == 'Series C':
        exit_valuations[stage] = st.sidebar.slider(f'Exit Valuation at {stage}', 100, 1000, (200, 500), step=10)
        zero_probabilities[stage] = st.sidebar.slider(f'Probability of Total Loss at {stage} (%)', 0, 100, 20, step=5)

    elif stage == 'IPO':
        exit_valuations[stage] = st.sidebar.slider(f'Exit Valuation at {stage}', 1000, 10000, (1000, 2000), step=100)
        zero_probabilities[stage] = st.sidebar.slider(f'Probability of Total Loss at {stage} (%)', 0, 100, 0, step=5)
    else:
        continue
        
total_mgmt_fee   = fund_size * (management_fee_pct / 100) * management_fee_years
deployable_capital = fund_size - total_mgmt_fee


def normalize_existing_portfolio(existing_df):
    if existing_df is None or existing_df.empty:
        return pd.DataFrame()

    df = existing_df.copy()
    numeric_columns = [
        "Invested Capital ($MM)",
        "Current Ownership (%)",
        "Follow-on Reserve ($MM)",
        "Future Dilution (%)",
        "Failure Probability (%)",
        "Exit Valuation Low ($MM)",
        "Exit Valuation High ($MM)",
        "Expected Exit Year",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    df["Company"] = df["Company"].fillna("").astype(str).str.strip()
    df["Entry Stage"] = df["Entry Stage"].where(df["Entry Stage"].isin(stages), initial_stage)
    df["Current Stage"] = df["Current Stage"].where(df["Current Stage"].isin(stages + ["Series C", "IPO"]), initial_stage)

    df = df[(df["Company"] != "") & (df["Invested Capital ($MM)"] > 0) & (df["Current Ownership (%)"] > 0)]
    if df.empty:
        return pd.DataFrame()

    df["Current Ownership (%)"] = df["Current Ownership (%)"].clip(0, 100)
    df["Follow-on Reserve ($MM)"] = df["Follow-on Reserve ($MM)"].clip(lower=0)
    df["Future Dilution (%)"] = df["Future Dilution (%)"].clip(0, 100)
    df["Failure Probability (%)"] = df["Failure Probability (%)"].clip(0, 100)
    df["Exit Valuation Low ($MM)"] = df["Exit Valuation Low ($MM)"].clip(lower=0)
    df["Exit Valuation High ($MM)"] = np.maximum(df["Exit Valuation High ($MM)"], df["Exit Valuation Low ($MM)"])
    df["Expected Exit Year"] = df["Expected Exit Year"].clip(lower=0).round().astype(int)

    return df


existing_portfolio_assumptions = (
    normalize_existing_portfolio(existing_portfolio_input)
    if include_existing_portfolio
    else pd.DataFrame()
)

if include_existing_portfolio and existing_portfolio_assumptions.empty:
    st.warning(
        "Existing portfolio simulation is enabled, but no valid holdings were found. "
        "Add at least a company name, invested capital, and current ownership."
    )


def simulate_existing_portfolio(existing_df):
    if existing_df is None or existing_df.empty:
        return pd.DataFrame()

    investments = []
    for _, holding in existing_df.iterrows():
        invested_capital = holding["Invested Capital ($MM)"]
        reserve_amount = holding["Follow-on Reserve ($MM)"]
        entry_amount = invested_capital + reserve_amount
        ownership = (holding["Current Ownership (%)"] / 100) * (1 - holding["Future Dilution (%)"] / 100)

        if np.random.rand() * 100 <= holding["Failure Probability (%)"]:
            exit_valuation = 0
            exit_amount = 0
            exit_stage = holding["Current Stage"]
        else:
            exit_valuation = np.random.uniform(
                holding["Exit Valuation Low ($MM)"],
                holding["Exit Valuation High ($MM)"],
            )
            exit_amount = ownership * exit_valuation
            exit_stage = "Exit"

        investments.append({
            "Source": "Existing Portfolio",
            "Company": holding["Company"],
            "Entry Stage": holding["Entry Stage"],
            "Current Stage": holding["Current Stage"],
            "Entry Amount": entry_amount,
            "Initial Invested ($MM)": invested_capital,
            "Follow-on Reserve ($MM)": reserve_amount,
            "Ownership (%)": ownership * 100,
            "Exit Stage": exit_stage,
            "Exit Valuation ($MM)": exit_valuation,
            "Exit Amount": exit_amount,
            "Deployment Year": 0,
            "Exit Year": holding["Expected Exit Year"],
        })

    return pd.DataFrame(investments)


# Simulation function
def simulate_portfolio():
    investments = []

    for stage in valid_stages:
        allocation_amount = (stage_allocations[stage] / 100) * deployable_capital
        deployed_in_stage = 0

        while deployed_in_stage < allocation_amount:
            valuation = np.random.uniform(*valuations[stage])
            check_size = np.random.uniform(*check_sizes[stage])
            check_size = min(check_size, allocation_amount - deployed_in_stage)
            deployed_in_stage += check_size
            equity = check_size / valuation

            investment = {
                'Source': 'New Deployment',
                'Company': f'{stage} Investment {len(investments) + 1}',
                'Entry Stage': stage,
                'Entry Amount': check_size
            }
            current_stage = stage

            stages_sequence = stages[stages.index(stage):] + ['Series C', 'IPO']
            for prev_stage, next_stage in zip(stages_sequence, stages_sequence[1:]):
                key = f"{prev_stage} to {next_stage}"
                if np.random.rand() * 100 <= prob_advancement.get(key, 0):
                    dilution_pct = np.random.uniform(*dilution.get(key, (0,0))) / 100
                    equity *= (1 - dilution_pct)
                    current_stage = next_stage
                else:
                    break


            if np.random.rand() * 100 <= zero_probabilities.get(current_stage, 0):
                exit_amount = 0
            else:
                exit_valuation = np.random.uniform(*exit_valuations[current_stage])
                exit_amount = equity * exit_valuation
            investment.update({'Current Stage': current_stage, 'Exit Stage': current_stage, 'Exit Amount': exit_amount})
            investments.append(investment)

    simulated_investments = pd.DataFrame(investments)
    existing_investments = simulate_existing_portfolio(existing_portfolio_assumptions)

    if not existing_investments.empty:
        return pd.concat([simulated_investments, existing_investments], ignore_index=True, sort=False)

    return simulated_investments

# Run simulations
all_sim_results = [simulate_portfolio() for _ in range(num_simulations)]
paid_in = [res['Entry Amount'].sum() for res in all_sim_results]
distributions = [res['Exit Amount'].sum() for res in all_sim_results]
moics = [d/p for d,p in zip(distributions, paid_in)]

# Calculate fund-level IRR based on simulated cash flows
adjusted_irrs = []
realized_years_list = []
for sim_df in all_sim_results:
    cash_flows_by_year = {}
    if 'Source' not in sim_df.columns:
        sim_df['Source'] = 'New Deployment'
    if 'Deployment Year' not in sim_df.columns:
        sim_df['Deployment Year'] = np.nan

    new_deployment_rows = sim_df['Source'].fillna('New Deployment') == 'New Deployment'
    if new_deployment_rows.any():
        sim_df.loc[new_deployment_rows, 'Deployment Year'] = np.random.randint(
            0,
            deployment_years,
            size=new_deployment_rows.sum()
        )
    sim_df.loc[~new_deployment_rows, 'Deployment Year'] = sim_df.loc[
        ~new_deployment_rows,
        'Deployment Year'
    ].fillna(0)

    # Track entries and exits by year with stage-based holding period
    for _, inv in sim_df.iterrows():
        year = int(inv['Deployment Year'])
        cash_flows_by_year[year] = cash_flows_by_year.get(year, 0) - inv['Entry Amount']

        if pd.notna(inv.get('Exit Year', np.nan)):
            exit_year = int(inv['Exit Year'])
        else:
            # Use years from stage sliders (range or fixed) and sum per stage
            entry_stage = inv['Entry Stage']
            exit_stage = inv['Exit Stage']
            stage_order = stages + ['Series C', 'IPO']
            entry_index = stage_order.index(entry_stage)
            exit_index = stage_order.index(exit_stage)

            hold_years = 0
            for i in range(entry_index, exit_index):
                key = stage_order[i] + ' to ' + stage_order[i + 1]
                years_slider = years_to_next.get(key, 0)
                # If the slider is a range, sample from it
                if isinstance(years_slider, tuple):
                    stage_years = np.random.uniform(*years_slider)
                else:
                    stage_years = years_slider
                hold_years += stage_years

            exit_year = year + int(np.ceil(hold_years))
        cash_flows_by_year[exit_year] = cash_flows_by_year.get(exit_year, 0) + inv['Exit Amount']

    # Add annual management fees during deployment
    for fee_year in range(management_fee_years):
        fee = fund_size * (management_fee_pct / 100)
        cash_flows_by_year[fee_year] = cash_flows_by_year.get(fee_year, 0) - fee

    # Re-indent IRR calculation inside the simulation loop
    max_exit_year = max(cash_flows_by_year.keys())
    years = range(0, max_exit_year + 1)
    cash_flows = [cash_flows_by_year.get(y, 0) for y in years]

    # Use the exact cash_flow_schedule logic for IRR calculation
    cash_flow_schedule = pd.DataFrame(sorted(cash_flows_by_year.items()), columns=["Year", "Net Cash Flow"])
    cash_flow_list = cash_flow_schedule['Net Cash Flow'].tolist()

    if all(c <= 0 for c in cash_flow_list[1:]):
        fund_irr = 0
    else:
        try:
            irr_val = npf.irr(cash_flow_list)
            fund_irr = 0 if (irr_val is None or np.isnan(irr_val)) else irr_val * 100
        except:
            fund_irr = 0

    adjusted_irrs.append(fund_irr)
    realized_years_list.append(max_exit_year)





# Apply Management Fee
fund_life_years = 10
management_fees = [fund_size * (management_fee_pct / 100) * management_fee_years for _ in paid_in]
adjusted_distributions = [d - fee for d, fee in zip(distributions, management_fees)]
adjusted_moics = [max(d / p, 0) for d, p in zip(adjusted_distributions, paid_in)]


# Display summary statistics
st.subheader("Simulation Summary Statistics")
# First row of metrics
row1 = st.columns(4)
for col, metric, val in zip(
    row1,
    ["Paid-in", "Distributed", "MOIC", "Mean IRR %"],
    [
        np.mean(paid_in),
        np.mean(distributions),
        np.mean(moics),
        np.mean(adjusted_irrs)
    ]
):
    col.metric(f"{metric}", f"{val:,.2f}")

# Second row of metrics
row2 = st.columns(4)
for col, metric, val in zip(
    row2,
    ["Net DPI", "# Investments", "Mgmt Fees"],
    [
                np.mean([ad / p for ad, p in zip(adjusted_distributions, paid_in)]),  # Net DPI after fees
        np.mean([len(r) for r in all_sim_results]),
        np.mean(management_fees)
    ]
):
    if metric == "Mgmt Fees":
        col.metric(f"{metric}", f"${val:,.2f}MM")
    else:
        col.metric(f"{metric}", f"{val:.2f}")

if include_existing_portfolio and not existing_portfolio_assumptions.empty:
    st.subheader("Existing vs. New Portfolio Contribution")
    contribution_rows = []
    for source in ["Existing Portfolio", "New Deployment"]:
        source_paid_in = [
            res.loc[res["Source"] == source, "Entry Amount"].sum()
            if "Source" in res.columns else 0
            for res in all_sim_results
        ]
        source_distributed = [
            res.loc[res["Source"] == source, "Exit Amount"].sum()
            if "Source" in res.columns else 0
            for res in all_sim_results
        ]
        mean_paid_in = np.mean(source_paid_in)
        mean_distributed = np.mean(source_distributed)
        contribution_rows.append({
            "Source": source,
            "Mean Paid-in ($MM)": mean_paid_in,
            "Mean Distributed ($MM)": mean_distributed,
            "Mean MOIC": mean_distributed / mean_paid_in if mean_paid_in else 0,
        })

    contribution_df = pd.DataFrame(contribution_rows)
    st.dataframe(
        contribution_df.style.format({
            "Mean Paid-in ($MM)": "{:,.2f}",
            "Mean Distributed ($MM)": "{:,.2f}",
            "Mean MOIC": "{:,.2f}",
        })
    )

# MOIC Distribution
st.subheader("Distribution of Fund MOIC")
fig, ax = plt.subplots(figsize=(8, 4), dpi=120)
sns.histplot(moics, bins=15, kde=True, ax=ax)
st.pyplot(fig)

# Stacked Bar Chart - Entry vs Exit per Investment
st.subheader("Entry Capital vs. Exit Value per Investment (Sample Simulation)")
sample_sim = all_sim_results[0].reset_index(drop=True)

fig, ax = plt.subplots(figsize=(12, 6), dpi=120)

# Compute gain/loss
exit_minus_entry = sample_sim['Exit Amount'] - sample_sim['Entry Amount']
gains = exit_minus_entry.clip(lower=0)
losses = exit_minus_entry.clip(upper=0)

# Plot entry amount
ax.bar(sample_sim.index, sample_sim['Entry Amount'], label='Initial Investment', color='skyblue')

# Plot gains in green
ax.bar(sample_sim.index, gains, bottom=sample_sim['Entry Amount'], label='Gain', color='seagreen', alpha=0.7)

# Plot losses in red
ax.bar(sample_sim.index, losses, bottom=sample_sim['Entry Amount'], label='Loss', color='crimson', alpha=0.7)

ax.set_xlabel('Investment #')
ax.set_ylabel('Value ($MM)')
ax.set_title('Stacked Entry Capital and Exit Value per Investment')
ax.legend()

st.pyplot(fig)


# Investment Schedule
st.subheader("Sample Simulation Investments")
st.dataframe(all_sim_results[0])
st.download_button(
    "Download sample simulation CSV",
    data=all_sim_results[0].to_csv(index=False).encode("utf-8"),
    file_name="sample_simulation.csv",
    mime="text/csv",
)


# Bonus Portfolio Modeling Lab
st.header("Portfolio Modeling Lab")
st.caption(
    "Experimental branch: a more opinionated fund-construction lab layered on top of the original simulator. "
    "It keeps the model transparent rather than pretending public data can predict private outcomes precisely."
)

bonus_presets = {
    "Balanced seed fund": {
        "avg_check": 2.0,
        "reserve_ratio": 0.75,
        "recycling_pct": 10,
        "follow_on_year": 3,
        "outcome_preset": "Industrial power law",
        "reserve_strategy": "Pro-rata every winner",
    },
    "Concentrated hard-tech": {
        "avg_check": 2.8,
        "reserve_ratio": 1.25,
        "recycling_pct": 5,
        "follow_on_year": 4,
        "outcome_preset": "Deep-tech heavy tail",
        "reserve_strategy": "Concentrate reserves in winners",
    },
    "Capital efficient pre-seed": {
        "avg_check": 1.1,
        "reserve_ratio": 0.4,
        "recycling_pct": 15,
        "follow_on_year": 2,
        "outcome_preset": "Capital efficient",
        "reserve_strategy": "Fixed reserve ratio",
    },
}

outcome_presets = {
    "Industrial power law": pd.DataFrame(
        [
            {"Bucket": "Writeoff", "Probability": 0.55, "Multiple": 0.0, "Hold Years": 4},
            {"Bucket": "Small return", "Probability": 0.25, "Multiple": 1.5, "Hold Years": 5},
            {"Bucket": "Good return", "Probability": 0.15, "Multiple": 6.0, "Hold Years": 7},
            {"Bucket": "Fund returner", "Probability": 0.05, "Multiple": 45.0, "Hold Years": 9},
        ]
    ),
    "Deep-tech heavy tail": pd.DataFrame(
        [
            {"Bucket": "Writeoff", "Probability": 0.62, "Multiple": 0.0, "Hold Years": 5},
            {"Bucket": "Small return", "Probability": 0.20, "Multiple": 1.3, "Hold Years": 6},
            {"Bucket": "Good return", "Probability": 0.13, "Multiple": 8.0, "Hold Years": 8},
            {"Bucket": "Fund returner", "Probability": 0.05, "Multiple": 75.0, "Hold Years": 10},
        ]
    ),
    "Capital efficient": pd.DataFrame(
        [
            {"Bucket": "Writeoff", "Probability": 0.50, "Multiple": 0.0, "Hold Years": 3},
            {"Bucket": "Small return", "Probability": 0.30, "Multiple": 1.7, "Hold Years": 5},
            {"Bucket": "Good return", "Probability": 0.15, "Multiple": 5.0, "Hold Years": 6},
            {"Bucket": "Fund returner", "Probability": 0.05, "Multiple": 30.0, "Hold Years": 8},
        ]
    ),
}

scenario_adjustments = {
    "Conservative": {"winner_probability": 0.75, "winner_multiple": 0.65, "writeoff_probability": 1.15},
    "Base": {"winner_probability": 1.0, "winner_multiple": 1.0, "writeoff_probability": 1.0},
    "High": {"winner_probability": 1.2, "winner_multiple": 1.35, "writeoff_probability": 0.9},
}


def adjusted_outcome_table(outcome_table, scenario_name):
    table = outcome_table.copy()
    adjustment = scenario_adjustments[scenario_name]
    winner_rows = table["Bucket"].isin(["Good return", "Fund returner"])
    writeoff_rows = table["Bucket"] == "Writeoff"

    table.loc[winner_rows, "Probability"] *= adjustment["winner_probability"]
    table.loc[writeoff_rows, "Probability"] *= adjustment["writeoff_probability"]
    table["Probability"] = table["Probability"] / table["Probability"].sum()
    table.loc[winner_rows, "Multiple"] *= adjustment["winner_multiple"]

    return table


def simulate_bonus_strategy(
    scenario_name,
    outcome_table,
    avg_check,
    reserve_ratio,
    reserve_strategy,
    recycling_pct,
    follow_on_year,
    simulation_count,
):
    table = adjusted_outcome_table(outcome_table, scenario_name)
    investable_capital = max(deployable_capital, 0)

    if reserve_strategy == "No reserves":
        initial_pool = investable_capital
        reserve_pool = 0
    else:
        initial_pool = investable_capital / (1 + reserve_ratio)
        reserve_pool = investable_capital - initial_pool

    company_count = max(1, int(initial_pool / max(avg_check, 0.1)))
    initial_paid = company_count * avg_check
    probabilities = table["Probability"].to_numpy()
    multiples = table["Multiple"].to_numpy()
    hold_years = table["Hold Years"].to_numpy()
    bucket_names = table["Bucket"].to_numpy()

    results = []
    yearly_cashflows = []

    for _ in range(simulation_count):
        bucket_indexes = np.random.choice(len(table), size=company_count, p=probabilities)
        selected_multiples = multiples[bucket_indexes]
        selected_buckets = bucket_names[bucket_indexes]
        selected_hold_years = hold_years[bucket_indexes]

        reserve_deployed = 0
        reserve_distribution = 0

        if reserve_pool > 0:
            if reserve_strategy == "Fixed reserve ratio":
                eligible_mask = selected_multiples > 0
            elif reserve_strategy == "Pro-rata every winner":
                eligible_mask = selected_multiples >= 1.5
            else:
                eligible_mask = selected_buckets == "Fund returner"

            eligible_count = int(eligible_mask.sum())
            if eligible_count > 0:
                reserve_per_company = min(reserve_pool / eligible_count, avg_check * max(reserve_ratio, 0.1))
                reserve_deployed = reserve_per_company * eligible_count
                reserve_distribution = (
                    reserve_per_company
                    * np.maximum(selected_multiples[eligible_mask] * 0.55, 0)
                ).sum()

        initial_distribution = (avg_check * selected_multiples).sum()
        early_distribution = (
            avg_check
            * selected_multiples[selected_hold_years <= max(follow_on_year + 2, 3)]
        ).sum()
        recycled_capital = min(
            early_distribution * (recycling_pct / 100),
            fund_size * 0.15,
        )
        recycled_distribution = recycled_capital * max(np.mean(selected_multiples[selected_multiples > 0]) if (selected_multiples > 0).any() else 0, 0)

        paid_in_total = initial_paid + reserve_deployed + recycled_capital
        gross_distribution = initial_distribution + reserve_distribution + recycled_distribution
        net_distribution = gross_distribution - total_mgmt_fee
        gross_moic = gross_distribution / paid_in_total if paid_in_total else 0
        net_dpi = max(net_distribution / paid_in_total, 0) if paid_in_total else 0

        cashflows = {0: 0}
        annual_initial = initial_paid / max(deployment_years, 1)
        for year in range(deployment_years):
            cashflows[year] = cashflows.get(year, 0) - annual_initial
        for fee_year in range(management_fee_years):
            cashflows[fee_year] = cashflows.get(fee_year, 0) - fund_size * (management_fee_pct / 100)
        if reserve_deployed:
            cashflows[follow_on_year] = cashflows.get(follow_on_year, 0) - reserve_deployed
        if recycled_capital:
            cashflows[follow_on_year] = cashflows.get(follow_on_year, 0) - recycled_capital

        for multiple, hold_year in zip(selected_multiples, selected_hold_years):
            cashflows[int(hold_year)] = cashflows.get(int(hold_year), 0) + avg_check * multiple
        if reserve_distribution:
            cashflows[min(follow_on_year + 4, 12)] = cashflows.get(min(follow_on_year + 4, 12), 0) + reserve_distribution
        if recycled_distribution:
            cashflows[min(follow_on_year + 5, 12)] = cashflows.get(min(follow_on_year + 5, 12), 0) + recycled_distribution

        years = list(range(0, max(cashflows.keys()) + 1))
        cashflow_list = [cashflows.get(year, 0) for year in years]
        try:
            irr_value = npf.irr(cashflow_list)
            irr_percent = 0 if irr_value is None or np.isnan(irr_value) else irr_value * 100
        except Exception:
            irr_percent = 0

        for year in years:
            yearly_cashflows.append(
                {
                    "Scenario": scenario_name,
                    "Year": year,
                    "Net Cash Flow ($MM)": cashflows.get(year, 0),
                }
            )

        results.append(
            {
                "Scenario": scenario_name,
                "Companies": company_count,
                "Initial Paid-in ($MM)": initial_paid,
                "Reserve Deployed ($MM)": reserve_deployed,
                "Recycled ($MM)": recycled_capital,
                "Total Paid-in ($MM)": paid_in_total,
                "Gross Distributed ($MM)": gross_distribution,
                "Gross MOIC": gross_moic,
                "Net DPI": net_dpi,
                "IRR %": irr_percent,
                "Loss of Capital": net_distribution < paid_in_total,
                "Fund Returner Count": int((selected_buckets == "Fund returner").sum()),
            }
        )

    return pd.DataFrame(results), pd.DataFrame(yearly_cashflows), table


def summarize_bonus_results(results_df):
    return pd.Series(
        {
            "Companies": results_df["Companies"].mean(),
            "Initial Paid-in ($MM)": results_df["Initial Paid-in ($MM)"].mean(),
            "Reserve Deployed ($MM)": results_df["Reserve Deployed ($MM)"].mean(),
            "Recycled ($MM)": results_df["Recycled ($MM)"].mean(),
            "Total Paid-in ($MM)": results_df["Total Paid-in ($MM)"].mean(),
            "Gross Distributed ($MM)": results_df["Gross Distributed ($MM)"].mean(),
            "Gross MOIC": results_df["Gross MOIC"].mean(),
            "Net DPI": results_df["Net DPI"].mean(),
            "IRR %": results_df["IRR %"].mean(),
            "P(LP Net < 1.0x)": results_df["Loss of Capital"].mean(),
            "Mean Fund Returners": results_df["Fund Returner Count"].mean(),
        }
    )


with st.container():
    preset_name = st.selectbox("Assumption preset", list(bonus_presets.keys()))
    preset = bonus_presets[preset_name]

    lab_cols = st.columns(3)
    with lab_cols[0]:
        bonus_avg_check = st.number_input(
            "Average initial check ($MM)",
            min_value=0.1,
            max_value=25.0,
            value=float(preset["avg_check"]),
            step=0.1,
        )
        bonus_reserve_strategy = st.selectbox(
            "Reserve strategy",
            ["No reserves", "Fixed reserve ratio", "Pro-rata every winner", "Concentrate reserves in winners"],
            index=["No reserves", "Fixed reserve ratio", "Pro-rata every winner", "Concentrate reserves in winners"].index(preset["reserve_strategy"]),
        )
    with lab_cols[1]:
        bonus_reserve_ratio = st.slider(
            "Reserve ratio",
            min_value=0.0,
            max_value=3.0,
            value=float(preset["reserve_ratio"]),
            step=0.05,
        )
        bonus_recycling_pct = st.slider(
            "Recycling percentage",
            min_value=0,
            max_value=50,
            value=int(preset["recycling_pct"]),
            step=1,
        )
    with lab_cols[2]:
        bonus_follow_on_year = st.slider(
            "Follow-on timing year",
            min_value=1,
            max_value=8,
            value=int(preset["follow_on_year"]),
            step=1,
        )
        bonus_simulations = st.slider(
            "Bonus lab simulations",
            min_value=50,
            max_value=1000,
            value=200,
            step=100,
        )

    bonus_outcome_preset = st.selectbox(
        "Power-law outcome preset",
        list(outcome_presets.keys()),
        index=list(outcome_presets.keys()).index(preset["outcome_preset"]),
    )
    selected_outcome_table = outcome_presets[bonus_outcome_preset]

    st.subheader("Outcome Buckets")
    edited_outcome_table = st.data_editor(
        selected_outcome_table,
        num_rows="fixed",
        column_config={
            "Bucket": st.column_config.TextColumn("Bucket", disabled=True),
            "Probability": st.column_config.NumberColumn("Probability", min_value=0.0, max_value=1.0, step=0.01),
            "Multiple": st.column_config.NumberColumn("Multiple", min_value=0.0, step=0.5),
            "Hold Years": st.column_config.NumberColumn("Hold Years", min_value=1, max_value=15, step=1),
        },
    )
    if edited_outcome_table["Probability"].sum() <= 0:
        st.error("Outcome probabilities must sum to more than zero.")
    else:
        edited_outcome_table["Probability"] = edited_outcome_table["Probability"] / edited_outcome_table["Probability"].sum()

    assumption_summary = {
        "preset": preset_name,
        "fund_size_mm": fund_size,
        "deployable_capital_mm": deployable_capital,
        "management_fee_pct": management_fee_pct,
        "management_fee_years": management_fee_years,
        "deployment_years": deployment_years,
        "average_initial_check_mm": bonus_avg_check,
        "reserve_strategy": bonus_reserve_strategy,
        "reserve_ratio": bonus_reserve_ratio,
        "recycling_pct": bonus_recycling_pct,
        "follow_on_year": bonus_follow_on_year,
        "outcome_preset": bonus_outcome_preset,
        "outcome_buckets": edited_outcome_table.to_dict(orient="records"),
    }

    st.subheader("Assumption Summary")
    st.json(assumption_summary)
    export_cols = st.columns(2)
    with export_cols[0]:
        st.download_button(
            "Download assumptions JSON",
            data=json.dumps(assumption_summary, indent=2).encode("utf-8"),
            file_name="portfolio_lab_assumptions.json",
            mime="application/json",
        )
    with export_cols[1]:
        st.download_button(
            "Download assumptions CSV",
            data=pd.DataFrame([assumption_summary]).drop(columns=["outcome_buckets"]).to_csv(index=False).encode("utf-8"),
            file_name="portfolio_lab_assumptions.csv",
            mime="text/csv",
        )

    scenario_results = []
    scenario_cashflows = []
    scenario_tables = {}
    for scenario_name in ["Conservative", "Base", "High"]:
        result_df, cashflow_df, table = simulate_bonus_strategy(
            scenario_name,
            edited_outcome_table,
            bonus_avg_check,
            bonus_reserve_ratio,
            bonus_reserve_strategy,
            bonus_recycling_pct,
            bonus_follow_on_year,
            bonus_simulations,
        )
        scenario_results.append(summarize_bonus_results(result_df).rename(scenario_name))
        scenario_cashflows.append(cashflow_df)
        scenario_tables[scenario_name] = table

    scenario_summary_df = pd.DataFrame(scenario_results)
    st.subheader("Scenario Comparison")
    st.dataframe(
        scenario_summary_df.style.format({
            "Companies": "{:,.1f}",
            "Initial Paid-in ($MM)": "{:,.2f}",
            "Reserve Deployed ($MM)": "{:,.2f}",
            "Recycled ($MM)": "{:,.2f}",
            "Total Paid-in ($MM)": "{:,.2f}",
            "Gross Distributed ($MM)": "{:,.2f}",
            "Gross MOIC": "{:,.2f}",
            "Net DPI": "{:,.2f}",
            "IRR %": "{:,.1f}",
            "P(LP Net < 1.0x)": "{:.0%}",
            "Mean Fund Returners": "{:,.2f}",
        })
    )

    st.download_button(
        "Download scenario comparison CSV",
        data=scenario_summary_df.reset_index(names="Scenario").to_csv(index=False).encode("utf-8"),
        file_name="portfolio_lab_scenarios.csv",
        mime="text/csv",
    )

    st.subheader("J-Curve / Cash-Flow Preview")
    cashflow_summary_df = (
        pd.concat(scenario_cashflows, ignore_index=True)
        .groupby(["Scenario", "Year"], as_index=False)["Net Cash Flow ($MM)"]
        .mean()
    )
    pivot_cashflows = cashflow_summary_df.pivot(index="Year", columns="Scenario", values="Net Cash Flow ($MM)").fillna(0)
    st.line_chart(pivot_cashflows)
    st.dataframe(pivot_cashflows.style.format("{:,.2f}"))

    st.subheader("Sensitivity Analysis")
    base_moic = scenario_summary_df.loc["Base", "Net DPI"]
    sensitivity_cases = []
    sensitivity_inputs = [
        ("Average check", "average_check", bonus_avg_check * 0.8, bonus_avg_check * 1.2),
        ("Reserve ratio", "reserve_ratio", max(bonus_reserve_ratio - 0.25, 0), bonus_reserve_ratio + 0.25),
        ("Recycling", "recycling_pct", max(bonus_recycling_pct - 10, 0), min(bonus_recycling_pct + 10, 50)),
        ("Follow-on year", "follow_on_year", max(bonus_follow_on_year - 1, 1), min(bonus_follow_on_year + 1, 8)),
    ]

    for label, key, low_value, high_value in sensitivity_inputs:
        case_values = []
        for value in [low_value, high_value]:
            avg_check_case = value if key == "average_check" else bonus_avg_check
            reserve_ratio_case = value if key == "reserve_ratio" else bonus_reserve_ratio
            recycling_case = value if key == "recycling_pct" else bonus_recycling_pct
            follow_on_case = int(value) if key == "follow_on_year" else bonus_follow_on_year

            case_df, _, _ = simulate_bonus_strategy(
                "Base",
                edited_outcome_table,
                avg_check_case,
                reserve_ratio_case,
                bonus_reserve_strategy,
                recycling_case,
                follow_on_case,
                max(75, int(bonus_simulations / 2)),
            )
            case_values.append(summarize_bonus_results(case_df)["Net DPI"])

        sensitivity_cases.append(
            {
                "Driver": label,
                "Low Case Net DPI": case_values[0],
                "High Case Net DPI": case_values[1],
                "Spread vs Base": max(abs(case_values[0] - base_moic), abs(case_values[1] - base_moic)),
            }
        )

    sensitivity_df = pd.DataFrame(sensitivity_cases).sort_values("Spread vs Base", ascending=False)
    st.dataframe(
        sensitivity_df.style.format({
            "Low Case Net DPI": "{:,.2f}",
            "High Case Net DPI": "{:,.2f}",
            "Spread vs Base": "{:,.2f}",
        })
    )
    st.bar_chart(sensitivity_df.set_index("Driver")["Spread vs Base"])

    st.subheader("Model Notes")
    st.markdown(
        """
        - The bonus lab uses transparent outcome buckets rather than hidden private-market data.
        - Reserve dollars are deployed into eligible companies based on the selected reserve strategy.
        - Follow-on returns are haircut to reflect later entry prices.
        - Recycling is modeled as a single redeployment of early distributions and is capped at 15% of fund size.
        - The loss-of-capital readout is the share of simulations where net distributions after management fees fail to return paid-in capital.
        """
    )
