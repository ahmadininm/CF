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

# Input daily usage for BAS
st.subheader("Business as Usual (BAU) Inputs")
bau_data = pd.DataFrame({
    "Item": default_items,
    "Daily Usage (Units)": [3000, 1000, 500, 200, 100, 50]  # Example default values
})
bau_data["Emission Factor (kg CO2e/unit)"] = bau_data["Item"].map(emission_factors)
bau_data["Daily Emissions (kg CO2e)"] = bau_data["Daily Usage (Units)"] * bau_data["Emission Factor (kg CO2e/unit)"]
bau_data["Annual Emissions (kg CO2e)"] = bau_data["Daily Emissions (kg CO2e)"] * 365

# Display BAS details
st.write("### BAS Details")
st.dataframe(bau_data[["Item", "Daily Usage (Units)", "Daily Emissions (kg CO2e)", "Annual Emissions (kg CO2e)"]])

# Calculate total BAS emissions
total_emissions_daily_bau = bau_data["Daily Emissions (kg CO2e)"].sum()
total_emissions_yearly_bau = total_emissions_daily_bau * 365
st.write(f"**Total Daily Emissions (BAU):** {total_emissions_daily_bau:.2f} kg CO2e/day")
st.write(f"**Total Annual Emissions (BAU):** {total_emissions_yearly_bau:.2f} kg CO2e/year")

# Scenario Planning
st.subheader("Scenario Planning")
num_scenarios = st.number_input("How many scenarios do you want to add?", min_value=1, step=1, value=1)

# Create a table for scenarios with default values of 100%
scenarios = pd.DataFrame(columns=["Scenario"] + default_items)
scenarios["Scenario"] = [f"Scenario {i + 1}" for i in range(num_scenarios)]
scenarios.loc[:, default_items] = 100.0  # Default all percentages to 100%

# Editable scenario table
st.write("### Edit Scenario Percentages (Relative to BAS)")
edited_scenarios = st.experimental_data_editor(scenarios)

# Process scenarios and calculate emissions
results = []
for i, row in edited_scenarios.iterrows():
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

# Convert results to a DataFrame and display
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
