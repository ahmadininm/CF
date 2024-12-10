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
bau_data["Daily Emissions (kg CO2e)"] = bau_data["Daily Usage (Units)"] * bau_data["Emission Factor (kg CO2e/unit)"]

# Total emissions
total_emissions_daily = bau_data["Daily Emissions (kg CO2e)"].sum()
total_emissions_yearly = total_emissions_daily * 365

# Display results
st.subheader("Results")
st.write(f"**Total Daily Emissions:** {total_emissions_daily:.2f} kg CO2e/day")
st.write(f"**Total Annual Emissions:** {total_emissions_yearly:.2f} kg CO2e/year")

# Display detailed table
st.subheader("Detailed Emissions Breakdown")
st.dataframe(bau_data[["Item", "Daily Usage (Units)", "Daily Emissions (kg CO2e)"]])

# Plot emissions breakdown
st.subheader("Emissions Breakdown Chart")
st.bar_chart(bau_data.set_index("Item")["Daily Emissions (kg CO2e)"])
