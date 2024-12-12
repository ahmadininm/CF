import pandas as pd
import streamlit as st
import numpy as np

# Default materials and energy (units changed to use m³/day)
default_items = [
    "Gas (kWh/day)", 
    "Electricity (kWh/day)", 
    "Nitrogen (m³/day)", 
    "Hydrogen (m³/day)", 
    "Argon (m³/day)", 
    "Helium (m³/day)"
]

# Emission Factors (hidden from the user) - keys updated to match item names
emission_factors = {
    "Gas (kWh/day)": 0.182928926,
    "Electricity (kWh/day)": 0.207074289,
    "Nitrogen (m³/day)": 0.090638487,
    "Hydrogen (m³/day)": 1.07856,
    "Argon (m³/day)": 6.342950515,
    "Helium (m³/day)": 0.660501982
}

# Main Title and Description
st.title("Sustainability Decision Assistant")
st.write("*A tool to prioritise scenarios for carbon savings and resource efficiency, enabling data-driven sustainable decisions.*")

# Input BAU values
st.subheader("Enter Daily Usage for Business As Usual (BAU)")
bau_data = pd.DataFrame({
    "Item": default_items,
    "Daily Usage (Units)": [0.0] * len(default_items)
})

for i in range(len(bau_data)):
    bau_data.loc[i, "Daily Usage (Units)"] = st.number_input(
        f"{bau_data['Item'][i]}:",
        min_value=0.0,
        step=0.1,
        value=0.0,
        key=f"bau_input_{i}"
    )

# Fill missing emission factors in the DataFrame
bau_data["Emission Factor (kg CO₂e/unit)"] = bau_data["Item"].map(emission_factors).fillna(0)

# Calculate emissions for BAU
bau_data["Daily Emissions (kg CO₂e)"] = bau_data["Daily Usage (Units)"] * bau_data["Emission Factor (kg CO₂e/unit)"]
bau_data["Annual Emissions (kg CO₂e)"] = bau_data["Daily Emissions (kg CO₂e)"] * 365

# Display BAU summary
st.write("### BAU Results")
total_daily_bau = bau_data['Daily Emissions (kg CO₂e)'].sum()
total_annual_bau = bau_data['Annual Emissions (kg CO₂e)'].sum()

st.write(f"**Total Daily Emissions (BAU):** {total_daily_bau:.2f} kg CO₂e/day")
st.write(f"**Total Annual Emissions (BAU):** {total_annual_bau:.2f} kg CO₂e/year")

# Scenario Planning
st.subheader("Scenario Planning (Editable Table)")
num_scenarios = st.number_input("How many scenarios do you want to add?", min_value=1, step=1, value=1, key="num_scenarios")

# Use session_state to remember scenario_df
if "scenario_data" not in st.session_state:
    st.session_state["scenario_data"] = pd.DataFrame()

# If number of scenarios changed, recreate scenario_df
if st.session_state.get("prev_num_scenarios", 1) != num_scenarios or st.session_state["scenario_data"].empty:
    scenario_columns = ["Item"] + [f"Scenario {i+1} (%)" for i in range(num_scenarios)]
    scenario_data = [[item] + [100.0]*num_scenarios for item in bau_data["Item"]]
    scenario_df = pd.DataFrame(scenario_data, columns=scenario_columns)
    st.session_state["scenario_data"] = scenario_df
else:
    scenario_df = st.session_state["scenario_data"]

st.write("Please adjust the percentages for each scenario. Double-click a cell to edit the value.")
st.write("The percentage represents usage relative to BAU. For example, 90% means the item is at 90% of its BAU usage, thereby achieving a 10% reduction.")

try:
    edited_scenario_df = st.data_editor(scenario_df, use_container_width=True, key="scenario_editor")
except AttributeError:
    edited_scenario_df = st.experimental_data_editor(scenario_df, use_container_width=True)

# Update the scenario_data in session_state
if not edited_scenario_df.equals(st.session_state["scenario_data"]):
    st.session_state["scenario_data"] = edited_scenario_df.copy()
st.session_state["prev_num_scenarios"] = num_scenarios

# Calculate scenario emissions and savings
results = []
for col in edited_scenario_df.columns[1:]:
    usage_percentages = edited_scenario_df[col].values / 100.0
    scenario_daily_emissions = (bau_data["Daily Usage (Units)"].values \
                                * usage_percentages \
                                * bau_data["Emission Factor (kg CO₂e/unit)"].values).sum()
    scenario_annual_emissions = scenario_daily_emissions * 365
    co2_saving_kg = total_annual_bau - scenario_annual_emissions
    co2_saving_percent = (co2_saving_kg / total_annual_bau * 100) if total_annual_bau != 0 else 0

    results.append({
        "Scenario": col.replace(" (%)",""),
        "Total Daily Emissions (kg CO₂e)": scenario_daily_emissions,
        "Total Annual Emissions (kg CO₂e)": scenario_annual_emissions,
        "CO₂ Saving (kg CO₂e/year)": co2_saving_kg,
        "CO₂ Saving (%)": co2_saving_percent
    })

results_df = pd.DataFrame(results)
results_df.index = range(1, len(results_df) + 1)

st.write("### Scenario Results")
st.dataframe(results_df)

st.subheader("CO₂ Savings Compared to BAU (%)")
st.bar_chart(results_df.set_index("Scenario")["CO₂ Saving (%)"], use_container_width=True)

# Initialize other_name and other_scale
other_name = ""
other_scale = ""

# Ask about additional criteria
st.write("Apart from the environmental impact (e.g., CO₂ saved) calculated above, which of the following criteria are also important to your organisation? Please select all that apply and then assign values for each scenario.")

criteria_options = {
    "Technical Feasibility": "1-10 scale, higher = better",
    "Supplier Reliability and Technology Readiness": "1-10 scale, higher = better",
    "Implementation Complexity": "1-10 scale, higher = better",
    "Scalability": "1-10 scale, higher = better",
    "Maintenance Requirements": "1-10 scale, higher = better",
    "Regulatory Compliance": "1-10 scale, higher = better",
    "Risk for Workforce Safety": "1-10 scale, higher = better",
    "Risk for Operations": "1-10 scale, higher = better",
    "Impact on Product Quality": "1-10 scale, higher = better",
    "Customer and Stakeholder Alignment": "1-10 scale, higher = better",
    "Priority for our organisation": "1-10 scale, higher = better",
    "Initial investment (£)": "Lower = better",
    "Return on Investment (ROI)(years)": "Lower = better",
    "Other": "Custom criteria"
}

selected_criteria = st.multiselect(
    "Select the criteria you want to consider:",
    list(criteria_options.keys())
)

if "Other" in selected_criteria:
    other_name = st.text_input("Enter the name for the 'Other' criterion:")
    other_scale = st.radio("Does a higher number represent a more beneficial outcome for this criterion?", ["Yes", "No"])
    if other_name.strip():
        selected_criteria.remove("Other")
        selected_criteria.append(other_name.strip())
        criteria_options[other_name.strip()] = "1-10 scale, higher = better" if other_scale == "Yes" else "Lower = better"

# Get scenario names
scenario_names = [col.replace(" (%)", "") for col in edited_scenario_df.columns[1:]]

if "criteria_data" not in st.session_state:
    st.session_state["criteria_data"] = pd.DataFrame()

if selected_criteria:
    criteria_df = st.session_state["criteria_data"].copy()

    # Initialize criteria data if empty or criteria changed
    if criteria_df.empty or list(criteria_df["Scenario"]) != scenario_names:
        criteria_df = pd.DataFrame({"Scenario": scenario_names})
        for c in selected_criteria:
            criteria_df[c] = 0
        st.session_state["criteria_data"] = criteria_df

    st.write("Please assign values for each selected criterion to each scenario. Double-click a cell to edit.")

    column_config = {"Scenario": st.column_config.TextColumn("Scenario", disabled=True)}
    for crit in selected_criteria:
        column_config[crit] = st.column_config.NumberColumn(label=crit, min_value=1, max_value=10)

    try:
        edited_criteria_df = st.data_editor(criteria_df, use_container_width=True, column_config=column_config, key="criteria_editor")
    except AttributeError:
        edited_criteria_df = st.experimental_data_editor(criteria_df, use_container_width=True)

    if not edited_criteria_df.equals(st.session_state["criteria_data"]):
        st.session_state["criteria_data"] = edited_criteria_df

    if st.button("Run the model"):
        scaled_criteria_df = edited_criteria_df.copy()

        # Normalize criteria
        for crit in selected_criteria:
            values = scaled_criteria_df[crit]
            if crit in ["Initial investment (£)", "Return on Investment (ROI)(years)"] or (other_name == crit and other_scale == "No"):
                scaled_criteria_df[crit] = 10 - 9 * (values - values.min()) / (values.max() - values.min()) if values.max() != values.min() else 10
            else:
                scaled_criteria_df[crit] = 1 + 9 * (values - values.min()) / (values.max() - values.min()) if values.max() != values.min() else 10

        st.write("### Normalised Results (All Criteria Scaled 1-10)")
        st.dataframe(scaled_criteria_df)

        # Summarize scores and rank
        sum_df = scaled_criteria_df.copy()
        sum_df["Total Score"] = sum_df.drop(columns=["Scenario"]).sum(axis=1)
        sum_df["Rank"] = sum_df["Total Score"].rank(ascending=False).astype(int)

        st.write("### Total Scores and Ranking")
        st.dataframe(sum_df.style.background_gradient(cmap="RdYlGn", subset=["Total Score"]))
