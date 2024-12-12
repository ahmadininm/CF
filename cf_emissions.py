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
    "Gas (kWh/day)": 0.182928926,         # kg CO₂e/kWh
    "Electricity (kWh/day)": 0.207074289, # kg CO₂e/kWh
    "Nitrogen (m³/day)": 0.090638487,     # kg CO₂e/m³
    "Hydrogen (m³/day)": 1.07856,         # kg CO₂e/m³
    "Argon (m³/day)": 6.342950515,        # kg CO₂e/m³
    "Helium (m³/day)": 0.660501982        # kg CO₂e/m³
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
        value=0.0
    )

# Option to add custom items
st.subheader("Add Custom Items (Optional)")
st.write("If there are any additional sources of emissions not accounted for above, you can add them here.")
if st.checkbox("Add custom items?"):
    num_custom_items = st.number_input("How many custom items would you like to add?", min_value=1, step=1, value=1)
    for i in range(num_custom_items):
        item_name = st.text_input(f"Custom Item {i + 1} Name:", key=f"custom_item_name_{i}")
        emission_factor = st.number_input(
            f"Custom Item {i + 1} Emission Factor (kg CO₂e/unit):", 
            min_value=0.0000001, 
            step=0.0000001, 
            value=0.0000001,
            key=f"custom_emission_factor_{i}"
        )
        usage = st.number_input(
            f"Custom Item {i + 1} Daily Usage (Units):", 
            min_value=0.0, 
            step=0.1, 
            value=0.0,
            key=f"custom_usage_{i}"
        )
        # Add to BAU Data
        new_row = pd.DataFrame({"Item": [item_name], "Daily Usage (Units)": [usage]})
        bau_data = pd.concat([bau_data, new_row], ignore_index=True)
        emission_factors[item_name] = emission_factor

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

# Visualize BAU emissions
st.bar_chart(bau_data.set_index("Item")["Daily Emissions (kg CO₂e)"], use_container_width=True)

# Scenario Planning
st.subheader("Scenario Planning (Editable Table)")
num_scenarios = st.number_input("How many scenarios do you want to add?", min_value=1, step=1, value=1)

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
st.session_state["scenario_data"] = edited_scenario_df.copy()
st.session_state["prev_num_scenarios"] = num_scenarios

# Convert columns (except Item) to numeric
for col in edited_scenario_df.columns[1:]:
    edited_scenario_df[col] = pd.to_numeric(edited_scenario_df[col], errors='coerce').fillna(100.0)

# Calculate scenario emissions and savings
results = []
for col in edited_scenario_df.columns[1:]:
    usage_percentages = edited_scenario_df[col].values / 100.0
    scenario_daily_emissions = (bau_data["Daily Usage (Units)"].values 
                                * usage_percentages 
                                * bau_data["Emission Factor (kg CO₂e/unit)"].values).sum()
    scenario_annual_emissions = scenario_daily_emissions * 365
    co2_saving_kg = total_annual_bau - scenario_annual_emissions
    co2_saving_percent = (co2_saving_kg / total_annual_bau * 100) if total_annual_bau != 0 else 0

    results.append({
        "Scenario": col.replace(" (%)",""),  # Remove " (%)" from the scenario name
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

# Option to download scenario results as CSV
st.download_button(
    label="Download Scenario Results as CSV",
    data=results_df.to_csv(index=False),
    file_name="scenario_results.csv",
    mime="text/csv"
)

# Initialize other_name and other_scale
other_name = ""
other_scale = ""

# Ask about additional criteria
st.write("Apart from the environmental impact (e.g., CO₂ saved) calculated above, which of the following criteria are also important to your organisation? Please select all that apply and then assign values for each scenario.")

# Criteria options
criteria_options = {
    "Technical Feasibility": "<span style='color:red;'>1-4: low feasibility</span>, <span style='color:orange;'>5-6: moderate</span>, <span style='color:green;'>7-10: high feasibility</span>",
    "Supplier Reliability and Technology Readiness": "<span style='color:red;'>1-4: unreliable/immature</span>, <span style='color:orange;'>5-6: mostly reliable</span>, <span style='color:green;'>7-10: fully reliable & proven</span>",
    "Implementation Complexity": "<span style='color:red;'>1-4: very complex</span>, <span style='color:orange;'>5-6: moderate complexity</span>, <span style='color:green;'>7-10: easy to implement</span>",
    "Scalability": "<span style='color:red;'>1-4: hard to scale</span>, <span style='color:orange;'>5-6: moderate</span>, <span style='color:green;'>7-10: easy to scale</span>",
    "Maintenance Requirements": "<span style='color:red;'>1-4: high maintenance</span>, <span style='color:orange;'>5-6: moderate</span>, <span style='color:green;'>7-10: low maintenance</span>",
    "Regulatory Compliance": "<span style='color:red;'>1-4: risk of non-compliance</span>, <span style='color:orange;'>5-6: mostly compliant</span>, <span style='color:green;'>7-10: fully compliant or beyond</span>",
    "Risk for Workforce Safety": "<span style='color:red;'>1-4: significant safety risks</span>, <span style='color:orange;'>5-6: moderate risks</span>, <span style='color:green;'>7-10: very low risk</span>",
    "Risk for Operations": "<span style='color:red;'>1-4: high operational risk</span>, <span style='color:orange;'>5-6: moderate risk</span>, <span style='color:green;'>7-10: minimal risk</span>",
    "Impact on Product Quality": "<span style='color:red;'>1-4: reduces quality</span>, <span style='color:orange;'>5-6: acceptable</span>, <span style='color:green;'>7-10: improves or maintains quality</span>",
    "Customer and Stakeholder Alignment": "<span style='color:red;'>1-4: low alignment</span>, <span style='color:orange;'>5-6: moderate</span>, <span style='color:green;'>7-10: high alignment</span>",
    "Priority for our organisation": "<span style='color:red;'>1-4: low priority</span>, <span style='color:orange;'>5-6: moderate</span>, <span style='color:green;'>7-10: top priority</span>",
    "Initial investment (£)": "Enter the upfront cost needed (no scale limit).",
    "Return on Investment (ROI)(years)": "Enter the time (in years) to recover the initial cost (no scale limit).",
    "Other": "If your desired criterion is not listed, select this and specify it."
}

selected_criteria = st.multiselect(
    "Select the criteria you want to consider:",
    list(criteria_options.keys())
)

if "Other" in selected_criteria:
    other_name = st.text_input("Enter the name for the 'Other' criterion:")
    other_scale = st.radio("Does a higher number represent a more beneficial (e.g., more sustainable) outcome for this 'Other' criterion?", ["Yes", "No"])
    if other_name.strip():
        selected_criteria.remove("Other")
        selected_criteria.append(other_name.strip())
        if other_scale == "Yes":
            criteria_options[other_name.strip()] = "1-10 scale, higher = more beneficial"
        else:
            criteria_options[other_name.strip()] = "1-10 scale, higher = less beneficial (inverse interpretation)"

for crit in selected_criteria:
    st.markdown(f"**{crit}:** {criteria_options[crit]}", unsafe_allow_html=True)

# Minimal changes: get scenario_names from the scenario table rather than results_df
# This ensures if there are multiple scenarios, they appear correctly.
scenario_names = [col.replace(" (%)","") for col in edited_scenario_df.columns[1:]]

if "prev_selected_criteria" not in st.session_state:
    st.session_state["prev_selected_criteria"] = []

if "criteria_data" not in st.session_state:
    st.session_state["criteria_data"] = pd.DataFrame()

if selected_criteria:
    # If criteria changed, adjust the data structure
    if set(selected_criteria) != set(st.session_state["prev_selected_criteria"]):
        criteria_df = st.session_state["criteria_data"].copy()
        if criteria_df.empty or list(criteria_df["Scenario"]) != scenario_names:
            criteria_df = pd.DataFrame({"Scenario": scenario_names})

        # Add missing criteria columns
        for c in selected_criteria:
            if c not in criteria_df.columns and c != "Scenario":
                criteria_df[c] = 0

        # Remove any columns not in selected_criteria
        for c in list(criteria_df.columns):
            if c != "Scenario" and c not in selected_criteria:
                criteria_df.drop(columns=c, inplace=True)

        st.session_state["criteria_data"] = criteria_df.copy()
        st.session_state["prev_selected_criteria"] = selected_criteria.copy()
    else:
        criteria_df = st.session_state["criteria_data"].copy()

    st.write("Please assign values for each selected criterion to each scenario. Double-click a cell to edit. For (1-10) criteria, only enter values between 1 and 10.")

    scale_criteria = {
        "Technical Feasibility", "Supplier Reliability and Technology Readiness", "Implementation Complexity",
        "Scalability", "Maintenance Requirements", "Regulatory Compliance", "Risk for Workforce Safety",
        "Risk for Operations", "Impact on Product Quality", "Customer and Stakeholder Alignment",
        "Priority for our organisation"
    }

    if other_name.strip() and other_name.strip() in selected_criteria and other_scale == "Yes":
        scale_criteria.add(other_name.strip())

    column_config = {}
    column_config["Scenario"] = st.column_config.TextColumn("Scenario", disabled=True)
    for crit in selected_criteria:
        if crit in scale_criteria:
            column_config[crit] = st.column_config.NumberColumn(label=crit, min_value=1, max_value=10)
        elif crit in ["Initial investment (£)", "Return on Investment (ROI)(years)"]:
            column_config[crit] = st.column_config.NumberColumn(label=crit)
        else:
            column_config[crit] = st.column_config.NumberColumn(label=crit)

    try:
        edited_criteria_df = st.data_editor(criteria_df, use_container_width=True, column_config=column_config, key="criteria_editor")
    except AttributeError:
        edited_criteria_df = st.experimental_data_editor(criteria_df, use_container_width=True)

    st.session_state["criteria_data"] = edited_criteria_df.copy()
else:
    st.session_state["criteria_data"] = pd.DataFrame()
    st.session_state["prev_selected_criteria"] = []

# Scaling logic
if selected_criteria and 'edited_criteria_df' in locals() and edited_criteria_df is not None and not edited_criteria_df.empty:
    scaled_criteria_df = edited_criteria_df.copy()

    inversion_criteria = []
    if "Return on Investment (ROI)(years)" in selected_criteria:
        inversion_criteria.append("Return on Investment (ROI)(years)")
    if "Initial investment (£)" in selected_criteria:
        inversion_criteria.append("Initial investment (£)")

    if other_name.strip():
        if other_scale == "No":
            inversion_criteria.append(other_name.strip())
        else:
            scale_criteria.add(other_name.strip())

    for crit in selected_criteria:
        values = scaled_criteria_df[crit].values.astype(float)
        min_val = np.min(values)
        max_val = np.max(values)

        if crit in scale_criteria:
            pass
        elif crit in inversion_criteria:
            if max_val == min_val:
                scaled_values = np.ones_like(values) * 10
            else:
                scaled_values = 10 - 9 * (values - min_val) / (max_val - min_val)
            scaled_criteria_df[crit] = scaled_values
        else:
            if max_val == min_val:
                scaled_values = np.ones_like(values) * 10
            else:
                scaled_values = 1 + 9 * (values - min_val) / (max_val - min_val)
            scaled_criteria_df[crit] = scaled_values

    st.write("### Normalised Results (All Criteria Scaled 1-10)")
    st.dataframe(scaled_criteria_df)
else:
    st.write("No criteria selected or no data available to scale.")
