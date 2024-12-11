import pandas as pd
import streamlit as st

# Default materials and energy
default_items = ["Gas (kWh/day)", "Electricity (kWh/day)", 
                 "Nitrogen (cubic m/day)", "Hydrogen (cubic m/day)", 
                 "Argon (cubic m/day)", "Helium (cubic m/day)"]

# Emission Factors (hidden from the user)
emission_factors = {
    "Gas (kWh/day)": 0.182928926,        # kg CO2e/kWh
    "Electricity (kWh/day)": 0.207074289,  # kg CO2e/kWh
    "Nitrogen (cubic m/day)": 0.090638487,  # kg CO2e/m³
    "Hydrogen (cubic m/day)": 1.07856,     # kg CO2e/m³
    "Argon (cubic m/day)": 6.342950515,    # kg CO2e/m³
    "Helium (cubic m/day)": 0.660501982    # kg CO2e/m³
}

# Streamlit Application
st.title("Business as Usual (BAU) Carbon Emission Calculator")

# Input BAU values
st.subheader("Enter Daily Usage for Business As Usual (BAU)")
bau_data = pd.DataFrame({
    "Item": default_items,
    "Daily Usage (Units)": [0] * len(default_items)  # Empty starting values
})

# Collect BAU inputs using Streamlit widgets
for i in range(len(bau_data)):
    bau_data.loc[i, "Daily Usage (Units)"] = st.number_input(
        f"{bau_data['Item'][i]}:",
        min_value=0.0,
        step=0.1,
        value=0.0
    )

# Calculate emissions for BAU
bau_data["Emission Factor (kg CO2e/unit)"] = bau_data["Item"].map(emission_factors)
bau_data["Daily Emissions (kg CO2e)"] = bau_data["Daily Usage (Units)"] * bau_data["Emission Factor (kg CO2e/unit)"]
bau_data["Annual Emissions (kg CO2e)"] = bau_data["Daily Emissions (kg CO2e)"] * 365

# Display BAU summary
st.write("### BAU Results")
st.write(f"**Total Daily Emissions (BAU):** {bau_data['Daily Emissions (kg CO2e)'].sum():.2f} kg CO2e/day")
st.write(f"**Total Annual Emissions (BAU):** {bau_data['Annual Emissions (kg CO2e)'].sum():.2f} kg CO2e/year")

# Scenario Planning
st.subheader("Scenario Planning")
num_scenarios = st.number_input("How many scenarios do you want to add?", min_value=1, step=1, value=1)

# Create a DataFrame for scenarios with default values
scenario_columns = ["Scenario"] + default_items
scenarios = pd.DataFrame(columns=scenario_columns)
scenarios["Scenario"] = [f"Scenario {i + 1}" for i in range(num_scenarios)]
scenarios.loc[:, default_items] = 100.0  # Default percentages to 100%

# Editable table for scenario inputs
st.write("### Adjust Scenario Percentages (Default: 100%)")
edited_scenarios = st.experimental_data_editor(scenarios, num_rows="dynamic")

# Process scenarios and calculate emissions
results = []
total_emissions_daily_bau = bau_data["Daily Emissions (kg CO2e)"].sum()
total_emissions_yearly_bau = total_emissions_daily_bau * 365

for _, row in edited_scenarios.iterrows():
    scenario_name = row["Scenario"]
    usage_percentages = row[default_items].values / 100  # Convert percentages to fractions
    daily_emissions = sum(
        bau_data["Daily Usage (Units)"].values * usage_percentages * bau_data["Emission Factor (kg CO2e/unit)"].values
    )
    yearly_emissions = daily_emissions * 365
    co2_saving_kg = total_emissions_yearly_bau - yearly_emissions
    co2_saving_percent = (co2_saving_kg / total_emissions_yearly_bau) * 100 if total_emissions_yearly_bau != 0 else 0

    results.append({
        "Scenario": scenario_name,
        "Total (kg CO2e/day)": daily_emissions,
        "Total (kg CO2e/year)": yearly_emissions,
        "CO2e Saving compared to BAS (kg CO2e/year)": co2_saving_kg,
        "CO2e Saving compared to BAS (%)": co2_saving_percent
    })

# Display results
results_df = pd.DataFrame(results)
st.subheader("Scenario Results")
st.dataframe(results_df)

# Option to download results as a CSV
st.download_button(
    label="Download Scenario Results as CSV",
    data=results_df.to_csv(index=False),
    file_name="scenario_results.csv",
    mime="text/csv"
)
