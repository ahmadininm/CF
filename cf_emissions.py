import pandas as pd
import streamlit as st

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
    "Gas (kWh/day)": 0.182928926,         # kg co2e/kWh
    "Electricity (kWh/day)": 0.207074289, # kg co2e/kWh
    "Nitrogen (m³/day)": 0.090638487,     # kg co2e/m³
    "Hydrogen (m³/day)": 1.07856,         # kg co2e/m³
    "Argon (m³/day)": 6.342950515,        # kg co2e/m³
    "Helium (m³/day)": 0.660501982        # kg co2e/m³
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
            f"Custom Item {i + 1} Emission Factor (kg co2e/unit):", 
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
bau_data["Emission Factor (kg co2e/unit)"] = bau_data["Item"].map(emission_factors).fillna(0)

# Calculate emissions for BAU
bau_data["Daily Emissions (kg co2e)"] = bau_data["Daily Usage (Units)"] * bau_data["Emission Factor (kg co2e/unit)"]
bau_data["Annual Emissions (kg co2e)"] = bau_data["Daily Emissions (kg co2e)"] * 365

# Display BAU summary
st.write("### BAU Results")
total_daily_bau = bau_data['Daily Emissions (kg co2e)'].sum()
total_annual_bau = bau_data['Annual Emissions (kg co2e)'].sum()

st.write(f"**Total Daily Emissions (BAU):** {total_daily_bau:.2f} kg co2e/day")
st.write(f"**Total Annual Emissions (BAU):** {total_annual_bau:.2f} kg co2e/year")

# Visualize BAU emissions
st.bar_chart(bau_data.set_index("Item")["Daily Emissions (kg co2e)"], use_container_width=True)

# Scenario Planning
st.subheader("Scenario Planning (Editable Table)")
num_scenarios = st.number_input("How many scenarios do you want to add?", min_value=1, step=1, value=1)

# Create a DataFrame with one column per scenario
scenario_columns = ["Item"] + [f"Scenario {i+1} (%)" for i in range(num_scenarios)]
scenario_data = [[item] + [100.0]*num_scenarios for item in bau_data["Item"]]
scenario_df = pd.DataFrame(scenario_data, columns=scenario_columns)

st.write("Please adjust the percentages for each scenario. Double-click a cell to edit the value.")
st.write("The percentage represents usage relative to BAU. For example, 90% means the item is at 90% of its BAU usage, thereby achieving a 10% reduction.")

# If st.data_editor is not available, use st.experimental_data_editor
try:
    edited_scenario_df = st.data_editor(scenario_df, use_container_width=True)
except AttributeError:
    edited_scenario_df = st.experimental_data_editor(scenario_df, use_container_width=True)

# Convert columns (except Item) to numeric
for col in edited_scenario_df.columns[1:]:
    edited_scenario_df[col] = pd.to_numeric(edited_scenario_df[col], errors='coerce').fillna(100.0)

# Calculate scenario emissions and savings
results = []
for col in edited_scenario_df.columns[1:]:
    usage_percentages = edited_scenario_df[col].values / 100.0
    scenario_daily_emissions = (bau_data["Daily Usage (Units)"].values 
                                * usage_percentages 
                                * bau_data["Emission Factor (kg co2e/unit)"].values).sum()
    scenario_annual_emissions = scenario_daily_emissions * 365
    co2_saving_kg = total_annual_bau - scenario_annual_emissions
    co2_saving_percent = (co2_saving_kg / total_annual_bau * 100) if total_annual_bau != 0 else 0

    results.append({
        "Scenario": col.replace(" (%)",""),  # Remove " (%)" from the scenario name
        "Total Daily Emissions (kg co2e)": scenario_daily_emissions,
        "Total Annual Emissions (kg co2e)": scenario_annual_emissions,
        "co2 saving (kg co2e/year)": co2_saving_kg,
        "co2 saving (%)": co2_saving_percent
    })

results_df = pd.DataFrame(results)

st.write("### Scenario Results")
st.dataframe(results_df)

st.subheader("co2 Savings Compared to BAU (%)")
st.bar_chart(results_df.set_index("Scenario")["co2 saving (%)"], use_container_width=True)

# Option to download scenario results as CSV
st.download_button(
    label="Download Scenario Results as CSV",
    data=results_df.to_csv(index=False),
    file_name="scenario_results.csv",
    mime="text/csv"
)
