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

if "bau_data" not in st.session_state:
    st.session_state["bau_data"] = bau_data.copy()

for i in range(len(bau_data)):
    st.session_state["bau_data"].loc[i, "Daily Usage (Units)"] = st.number_input(
        f"{bau_data['Item'][i]}:",
        min_value=0.0,
        step=0.1,
        value=st.session_state["bau_data"].loc[i, "Daily Usage (Units)"]
    )

bau_data = st.session_state["bau_data"]

# Option to add custom items
st.subheader("Add Custom Items (Optional)")
st.write("If there are any additional sources of emissions not accounted for above, you can add them here.")
if "custom_items" not in st.session_state:
    st.session_state["custom_items"] = pd.DataFrame(columns=["Item", "Daily Usage (Units)"])

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
        new_row = pd.DataFrame({"Item": [item_name], "Daily Usage (Units)": [usage]})
        if item_name.strip() and item_name not in st.session_state["custom_items"]["Item"].values:
            st.session_state["custom_items"] = pd.concat([st.session_state["custom_items"], new_row], ignore_index=True)
            emission_factors[item_name] = emission_factor

# Update BAU data with custom items
bau_data = pd.concat([bau_data, st.session_state["custom_items"]], ignore_index=True)
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

if "scenario_data" not in st.session_state or len(st.session_state["scenario_data"].columns) != num_scenarios + 1:
    scenario_columns = ["Item"] + [f"Scenario {i+1} (%)" for i in range(num_scenarios)]
    scenario_data = [[item] + [100.0]*num_scenarios for item in bau_data["Item"]]
    st.session_state["scenario_data"] = pd.DataFrame(scenario_data, columns=scenario_columns)

scenario_df = st.session_state["scenario_data"]

st.write("Please adjust the percentages for each scenario. Double-click a cell to edit the value.")
st.write("The percentage represents usage relative to BAU. For example, 90% means the item is at 90% of its BAU usage, thereby achieving a 10% reduction.")

try:
    edited_scenario_df = st.data_editor(scenario_df, use_container_width=True, key="scenario_editor")
except AttributeError:
    edited_scenario_df = st.experimental_data_editor(scenario_df, use_container_width=True)

st.session_state["scenario_data"] = edited_scenario_df

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

# Handle Total Scores and Ranking
try:
    sum_df = results_df.copy()
    sum_df["Total Score"] = sum_df.drop(columns=["Scenario"]).sum(axis=1)
    sum_df["Rank"] = sum_df["Total Score"].rank(method="dense", ascending=False).astype(int)
    st.write("### Total Scores and Ranking")
    st.dataframe(sum_df)
except ImportError:
    st.write("To visualize rankings with gradient styles, ensure `matplotlib` is installed.")
