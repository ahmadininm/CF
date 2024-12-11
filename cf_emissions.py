import pandas as pd
import streamlit as st

# Default materials and energy
default_items = ["Gas (kWh/day)", "Electricity (kWh/day)", 
                 "Nitrogen (cubic m/day)", "Hydrogen (cubic m/day)", 
                 "Argon (cubic m/day)", "Helium (cubic m/day)"]

# Emission Factors (hidden from the user)
emission_factors = {
    "Gas (kWh/day)": 0.182928926,         # kg CO2e/kWh
    "Electricity (kWh/day)": 0.207074289, # kg CO2e/kWh
    "Nitrogen (cubic m/day)": 0.090638487,# kg CO2e/m³
    "Hydrogen (cubic m/day)": 1.07856,    # kg CO2e/m³
    "Argon (cubic m/day)": 6.342950515,   # kg CO2e/m³
    "Helium (cubic m/day)": 0.660501982   # kg CO2e/m³
}

st.title("Business as Usual (BAU) Carbon Emission Calculator")

# Input BAU values
st.subheader("Enter Daily Usage for Business As Usual (BAU)")
bau_data = pd.DataFrame({
    "Item": default_items,
    "Daily Usage (Units)": [0.0] * len(default_items)
})

# Collect BAU inputs
for i in range(len(bau_data)):
    bau_data.loc[i, "Daily Usage (Units)"] = st.number_input(
        f"{bau_data['Item'][i]}:",
        min_value=0.0,
        step=0.1,
        value=0.0
    )

# Option to add custom items
st.subheader("Add Custom Items (Optional)")
if st.checkbox("Add custom items?"):
    num_custom_items = st.number_input("How many custom items would you like to add?", min_value=1, step=1, value=1)
    for i in range(num_custom_items):
        item_name = st.text_input(f"Custom Item {i + 1} Name:", key=f"custom_item_name_{i}")
        emission_factor = st.number_input(
            f"Custom Item {i + 1} Emission Factor (kg CO2e/unit):", 
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
        # Add to BAU data
        new_row = pd.DataFrame({
            "Item": [item_name],
            "Daily Usage (Units)": [usage],
            "Emission Factor (kg CO2e/unit)": [emission_factor]
        })
        bau_data = pd.concat([bau_data, new_row], ignore_index=True)
        emission_factors[item_name] = emission_factor

# Fill missing emission factors
bau_data["Emission Factor (kg CO2e/unit)"] = bau_data["Item"].map(emission_factors).fillna(0)

# Calculate BAU emissions
bau_data["Daily Emissions (kg CO2e)"] = bau_data["Daily Usage (Units)"] * bau_data["Emission Factor (kg CO2e/unit)"]
bau_data["Annual Emissions (kg CO2e)"] = bau_data["Daily Emissions (kg CO2e)"] * 365

# Display BAU results
st.write("### BAU Results")
total_daily_bau = bau_data['Daily Emissions (kg CO2e)'].sum()
total_annual_bau = bau_data['Annual Emissions (kg CO2e)'].sum()

st.write(f"**Total Daily Emissions (BAU):** {total_daily_bau:.2f} kg CO2e/day")
st.write(f"**Total Annual Emissions (BAU):** {total_annual_bau:.2f} kg CO2e/year")

# Visualise BAU emissions
st.bar_chart(bau_data.set_index("Item")["Daily Emissions (kg CO2e)"], use_container_width=True)

# Scenario Planning with editable table
st.subheader("Scenario Planning (Editable Table)")

scenario_df = pd.DataFrame({
    "Item": bau_data["Item"],
    "Percentage (%)": [100.0] * len(bau_data)
})

st.write("Please adjust the percentages in the table below as needed. "
         "For example, entering '110' will represent a 10% increase from BAU usage, "
         "while '85' represents a 15% decrease.")

# Use experimental_data_editor if data_editor is not working
edited_scenario_df = st.experimental_data_editor(
    scenario_df,
    use_container_width=True
)

# Convert updated percentages into fractions
# Ensure the column is numeric
edited_scenario_df["Percentage (%)"] = pd.to_numeric(edited_scenario_df["Percentage (%)"], errors='coerce').fillna(100.0)

usage_percentages = edited_scenario_df["Percentage (%)"].values / 100

# Calculate scenario emissions
daily_emissions_scenario = sum(
    bau_data["Daily Usage (Units)"].values * usage_percentages * bau_data["Emission Factor (kg CO2e/unit)"].values
)
yearly_emissions_scenario = daily_emissions_scenario * 365

co2_saving_kg = total_annual_bau - yearly_emissions_scenario
co2_saving_percent = (co2_saving_kg / total_annual_bau) * 100 if total_annual_bau != 0 else 0

# Display scenario results
st.write("### Scenario Results")
st.write(f"**Total Daily Emissions (Scenario):** {daily_emissions_scenario:.2f} kg CO2e/day")
st.write(f"**Total Annual Emissions (Scenario):** {yearly_emissions_scenario:.2f} kg CO2e/year")
st.write(f"**CO2e Saving compared to BAU (kg CO2e/year):** {co2_saving_kg:.2f} kg CO2e")
st.write(f"**CO2e Saving compared to BAU (%):** {co2_saving_percent:.2f}%")

# Download scenario results
scenario_results = pd.DataFrame({
    "Scenario": ["Editable Scenario"],
    "Total Daily Emissions (kg CO2e)": [daily_emissions_scenario],
    "Total Annual Emissions (kg CO2e)": [yearly_emissions_scenario],
    "CO2 Saving (kg CO2e/year)": [co2_saving_kg],
    "CO2 Saving (%)": [co2_saving_percent]
})

st.download_button(
    label="Download Scenario Results as CSV",
    data=scenario_results.to_csv(index=False),
    file_name="scenario_results.csv",
    mime="text/csv"
)
