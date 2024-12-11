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
        # Add to BAU Data
        new_row = pd.DataFrame({
            "Item": [item_name],
            "Daily Usage (Units)": [usage],
            "Emission Factor (kg CO2e/unit)": [emission_factor]
        })
        bau_data = pd.concat([bau_data, new_row], ignore_index=True)
        emission_factors[item_name] = emission_factor  # Add to emission factors dictionary

# Fill missing emission factors in the DataFrame
bau_data["Emission Factor (kg CO2e/unit)"] = bau_data["Item"].map(emission_factors)
bau_data["Emission Factor (kg CO2e/unit)"] = bau_data["Emission Factor (kg CO2e/unit)"].fillna(0)

# Calculate emissions for BAU
bau_data["Daily Emissions (kg CO2e)"] = bau_data["Daily Usage (Units)"] * bau_data["Emission Factor (kg CO2e/unit)"]
bau_data["Annual Emissions (kg CO2e)"] = bau_data["Daily Emissions (kg CO2e)"] * 365

# Display BAU summary
st.write("### BAU Results")
st.write(f"**Total Daily Emissions (BAU):** {bau_data['Daily Emissions (kg CO2e)'].sum():.2f} kg CO2e/day")
st.write(f"**Total Annual Emissions (BAU):** {bau_data['Annual Emissions (kg CO2e)'].sum():.2f} kg CO2e/year")

# Visualize BAU emissions
st.bar_chart(bau_data.set_index("Item")["Daily Emissions (kg CO2e)"], use_container_width=True)

# Scenario Planning
st.subheader("Scenario Planning")
st.write("Modify the default percentages (100%) to simulate changes in material and energy usage. "
         "For example, changing the value to 110% increases the usage by 10%, and setting it to 85% "
         "reduces it by 15%.")

num_scenarios = st.number_input("How many scenarios do you want to add?", min_value=1, step=1, value=1)

# Scenario input table simulation
scenario_inputs = []
for i in range(num_scenarios):
    with st.expander(f"Scenario {i + 1}"):
        scenario = {"Scenario": f"Scenario {i + 1}"}
        for item in default_items + [row["Item"] for _, row in bau_data.iterrows() if row["Item"] not in default_items]:
            scenario[item] = st.number_input(
                f"{item} for Scenario {i + 1} (%)",
                min_value=0.0,
                max_value=200.0,
                value=100.0,
                step=1.0,
                key=f"{item}_scenario_{i}"
            )
        scenario_inputs.append(scenario)

# Convert scenario inputs into a DataFrame
scenarios = pd.DataFrame(scenario_inputs)

# Ensure column alignment between BAU data and scenario percentages
scenarios = scenarios[["Scenario"] + bau_data["Item"].tolist()]

# Process scenarios and calculate emissions
results = []
total_emissions_daily_bau = bau_data["Daily Emissions (kg CO2e)"].sum()
total_emissions_yearly_bau = total_emissions_daily_bau * 365

for _, row in scenarios.iterrows():
    scenario_name = row["Scenario"]
    usage_percentages = row[bau_data["Item"]].values / 100  # Convert percentages to fractions
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

# Visualize scenario emissions and savings
st.subheader("CO2 Savings Compared to BAS (%)")
st.bar_chart(results_df.set_index("Scenario")["CO2e Saving compared to BAS (%)"])

# Option to download results as a CSV
st.download_button(
    label="Download Scenario Results as CSV",
    data=results_df.to_csv(index=False),
    file_name="scenario_results.csv",
    mime="text/csv"
)
