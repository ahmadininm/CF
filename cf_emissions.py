# Scenario Planning as a single editable table
st.subheader("Scenario Planning (Editable Table)")

# Create a table with default percentages of 100%
scenario_df = pd.DataFrame({
    "Item": bau_data["Item"],
    "Percentage (%)": [100.0] * len(bau_data)
})

st.write("Please adjust the percentages in the table below as needed. "
         "For example, entering '110' will represent a 10% increase from BAU usage, "
         "while '85' represents a 15% decrease.")

# Display the editable table
edited_scenario_df = st.experimental_data_editor(
    scenario_df, 
    num_rows="dynamic",
    use_container_width=True
)

# Convert updated percentages into fractions
usage_percentages = edited_scenario_df["Percentage (%)"].values / 100

# Calculate new emissions based on edited percentages
daily_emissions_scenario = sum(
    bau_data["Daily Usage (Units)"].values * usage_percentages * bau_data["Emission Factor (kg CO2e/unit)"].values
)
yearly_emissions_scenario = daily_emissions_scenario * 365

total_emissions_daily_bau = bau_data["Daily Emissions (kg CO2e)"].sum()
total_emissions_yearly_bau = total_emissions_daily_bau * 365

# Calculate savings compared to BAU
co2_saving_kg = total_emissions_yearly_bau - yearly_emissions_scenario
co2_saving_percent = (co2_saving_kg / total_emissions_yearly_bau) * 100 if total_emissions_yearly_bau != 0 else 0

# Display results
st.write("### Scenario Results")
st.write(f"**Total Daily Emissions (Scenario):** {daily_emissions_scenario:.2f} kg CO2e/day")
st.write(f"**Total Annual Emissions (Scenario):** {yearly_emissions_scenario:.2f} kg CO2e/year")
st.write(f"**CO2e Saving compared to BAU (kg CO2e/year):** {co2_saving_kg:.2f} kg CO2e")
st.write(f"**CO2e Saving compared to BAU (%):** {co2_saving_percent:.2f}%")
