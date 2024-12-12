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

# Initialize BAU table in session state
if "bau_data" not in st.session_state:
    st.session_state["bau_data"] = pd.DataFrame({
        "Item": default_items,
        "Daily Usage (Units)": [0.0] * len(default_items)
    })

bau_data = st.session_state["bau_data"]

# Collect BAU inputs
for i in range(len(bau_data)):
    bau_data.loc[i, "Daily Usage (Units)"] = st.number_input(
        f"{bau_data['Item'][i]}:",
        min_value=0.0,
        step=0.1,
        value=bau_data.loc[i, "Daily Usage (Units)"],
        key=f"bau_input_{i}"
    )

st.session_state["bau_data"] = bau_data

# Option to add custom items
st.subheader("Add Custom Items (Optional)")
st.write("If there are any additional sources of emissions not accounted for above, you can add them here.")

# Manage custom items
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

# Scenario Planning
st.subheader("Scenario Planning (Editable Table)")

# Initialize Scenario Data
if "scenario_data" not in st.session_state:
    st.session_state["scenario_data"] = pd.DataFrame()

if st.session_state["scenario_data"].empty or len(st.session_state["scenario_data"].columns) != num_scenarios + 1:
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
