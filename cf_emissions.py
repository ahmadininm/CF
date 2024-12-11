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
st.subheader("Enter your daily usage values below:")

# Input table for default items
bau_data = pd.DataFrame({
    "Item": default_items,
    "Daily Usage (Units)": [0] * len(default_items)
})

# Collect user inputs using Streamlit widgets
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
    custom_items = []
    custom_emission_factors = []
    custom_usages = []

    num_custom_items = st.number_input("How many custom items would you like to add?", min_value=1, step=1, value=1)
    for i in range(num_custom_items):
        item_name = st.text_input(f"Custom Item {i + 1} Name:")
        emission_factor = st.number_input(f"Custom Item {i + 1} Emission Factor (kg CO2e/unit):", min_value=0.0, step=0.01)
        usage = st.number_input(f"Custom Item {i + 1} Daily Usage (Units):", min_value=0.0, step=0.1)
        custom_items.append(item_name)
        custom_emission_factors.append(emission_factor)
        custom_usages.append(usage)

    # Add custom items to the DataFrame
    for i in range(len(custom_items)):
        bau_data = pd.concat(
            [bau_data, pd.DataFrame({"Item": [custom_items[i]], "Daily Usage (Units)": [custom_usages[i]]})],
            ignore_index=True
        )
        emission_factors[custom_items[i]] = custom_emission_factors[i]

# Calculate emissions
bau_data["Emission Factor (kg CO2e/unit)"] = bau_data["Item"].map(emission_factors)
bau_data["Daily Emissions (kg CO2e)"] = bau_data["Daily Usage (Units)"].values * bau_data["Emission Factor (kg CO2e/unit)"].values

# Total emissions for BAU
total_emissions_daily_bau = bau_data["Daily Emissions (kg CO2e)"].sum()
total_emissions_yearly_bau = total_emissions_daily_bau * 365

# Display BAU results
st.subheader("BAU Results")
st.write(f"**Total Daily Emissions (BAU):** {total_emissions_daily_bau:.2f} kg CO2e/day")
st.write(f"**Total Annual Emissions (BAU):** {total_emissions_yearly_bau:.2f} kg CO2e/year")

# Scenario Planning
st.subheader("Scenario Planning")
num_scenarios = st.number_input("How many scenarios do you want to add?", min_value=1, step=1, value=1)

# Generate a table for scenarios
scenarios = pd.DataFrame(columns=["Scenario"] + default_items)
scenarios["Scenario"] = [f"Scenario {i + 1}" for i in range(num_scenarios)]
scenarios.loc[-1] = ["BAS"] + [100] * len(default_items)  # Add BAU as the first row
scenarios.index = scenarios.index + 1  # Reindex
scenarios.sort_index(inplace=True)

# Manually build table inputs
st.write("Adjust the percentage values for each scenario (Default: 100%).")
edited_scenarios = scenarios.copy()
for i in range(len(edited_scenarios)):
    for col in default_items:
        edited_scenarios.loc[i, col] = st.number_input(
            f"{edited_scenarios.loc[i, 'Scenario']} - {col} (%)",
            min_value=0.0,
            max_value=200.0,  # Allow up to 200% usage
            value=edited_scenarios.loc[i, col],
            step=1.0
        )

# Process scenarios to calculate emissions
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
