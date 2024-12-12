import pandas as pd
import streamlit as st
import numpy as np

def keyword_based_assignment(description):
    # Define keyword mappings for criteria
    keyword_mappings = {
        "Technical Feasibility": {"easy", "simple", "straightforward", "feasible"},
        "Supplier Reliability and Technology Readiness": {"reliable", "proven", "mature", "stable"},
        "Implementation Complexity": {"complex", "difficult", "challenging", "simple"},
        "Scalability": {"scalable", "expandable", "grow", "increase"},
        "Maintenance Requirements": {"low maintenance", "easy", "simple", "minimal"},
        "Regulatory Compliance": {"compliant", "regulatory", "approved", "certified"},
        "Risk for Workforce Safety": {"safe", "no risk", "low risk", "secure"},
        "Risk for Operations": {"low risk", "minimal risk", "secure", "stable"},
        "Impact on Product Quality": {"high quality", "consistent", "improves", "maintains"},
        "Customer and Stakeholder Alignment": {"aligned", "support", "demand", "expect"},
        "Priority for our organisation": {"important", "priority", "focus", "critical"}
    }

    # Initialize criteria values
    criteria_values = {key: 5 for key in keyword_mappings.keys()}  # Default to 5 (neutral)

    # Assign values based on keywords in description
    for criterion, keywords in keyword_mappings.items():
        for keyword in keywords:
            if keyword in description.lower():
                criteria_values[criterion] = 10  # Max value if keyword found

    return criteria_values

def main():
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
        "Gas (kWh/day)": 0.182928926,         # kg CO₂e/kWh
        "Electricity (kWh/day)": 0.207074289, # kg CO₂e/kWh
        "Nitrogen (m³/day)": 0.090638487,     # kg CO₂e/m³
        "Hydrogen (m³/day)": 1.07856,         # kg CO₂e/m³
        "Argon (m³/day)": 6.342950515,        # kg CO₂e/m³
        "Helium (m³/day)": 0.660501982        # kg CO₂e/m³
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
            # Add to BAU Data
            new_row = pd.DataFrame({"Item": [item_name], "Daily Usage (Units)": [usage]})
            bau_data = pd.concat([bau_data, new_row], ignore_index=True)
            emission_factors[item_name] = emission_factor

    # Fill missing emission factors in the DataFrame
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

    # Create a DataFrame for scenario descriptions
    scenario_desc_columns = ["Scenario", "Description"]
    scenario_desc_data = [[f"Scenario {i+1}", ""] for i in range(num_scenarios)]
    scenario_desc_df = pd.DataFrame(scenario_desc_data, columns=scenario_desc_columns)

    st.write("Please describe each scenario. Double-click a cell to edit the description.")

    # If st.data_editor is not available, use st.experimental_data_editor
    try:
        edited_scenario_desc_df = st.data_editor(scenario_desc_df, use_container_width=True)
    except AttributeError:
        edited_scenario_desc_df = st.experimental_data_editor(scenario_desc_df, use_container_width=True)

    # Save edited scenario descriptions to session state
    st.session_state['edited_scenario_desc_df'] = edited_scenario_desc_df

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
                                    * bau_data["Emission Factor (kg CO₂e/unit)"].values).sum()
        scenario_annual_emissions = scenario_daily_emissions * 365
        co2_saving_kg = total_annual_bau - scenario_annual_emissions
        co2_saving_percent = (co2_saving_kg / total_annual_bau * 100) if total_annual_bau != 0 else 0

        results.append({
            "Scenario": col.replace(" (%)",""),  # Remove " (%)" from the scenario name
            "Total Daily Emissions (kg CO₂e)": scenario_daily_emissions,
            "Total Annual Emissions (kg CO₂e)": scenario_annual_emissions,
            "CO₂ Saving (kg CO₂e/year)": co2_saving_kg,
            "CO₂ Saving (%)": co2_saving_percent
        })

    results_df = pd.DataFrame(results)
    # Reindex the results to start from 1
    results_df.index = range(1, len(results_df) + 1)

    st.write("### Scenario Results")
    st.dataframe(results_df)

    st.subheader("CO₂ Savings Compared to BAU (%)")
    st.bar_chart(results_df.set_index("Scenario")["CO₂ Saving (%)"], use_container_width=True)

    # Option to download scenario results as CSV
    st.download_button(
        label="Download Scenario Results as CSV",
        data=results_df.to_csv(index=False),
        file_name="scenario_results.csv",
        mime="text/csv"
    )

    # Ask about additional criteria
    st.write("Apart from the environmental impact (e.g., CO₂ saved) calculated above, which of the following criteria are also important to your organisation? Please select all that apply and then assign values for each scenario.")
    criteria_options = {
        "Technical Feasibility": "<span style='color:red;'>1-4: low feasibility</span>, <span style='color:orange;'>5-6: moderate</span>, <span style='color:green;'>7-10: high feasibility</span>",
        "Supplier Reliability and Technology Readiness": "<span style='color:red;'>1-4: unreliable/immature</span>, <span style='color:orange;'>5-6: mostly reliable</span>, <span style='color:green;'>7-10: reliable/mature</span>",
        "Implementation Complexity": "<span style='color:red;'>1-4: very complex</span>, <span style='color:orange;'>5-6: moderate complexity</span>, <span style='color:green;'>7-10: easy to implement</span>",
        "Scalability": "<span style='color:red;'>1-4: hard to scale</span>, <span style='color:orange;'>5-6: moderate</span>, <span style='color:green;'>7-10: easy to scale</span>",
        "Maintenance Requirements": "<span style='color:red;'>1-4: high maintenance</span>, <span style='color:orange;'>5-6: moderate</span>, <span style='color:green;'>7-10: low maintenance</span>",
        "Regulatory Compliance": "<span style='color:red;'>1-4: risk of non-compliance</span>, <span style='color:orange;'>5-6: mostly compliant</span>, <span style='color:green;'>7-10: fully compliant</span>",
        "Risk for Workforce Safety": "<span style='color:red;'>1-4: significant safety risks</span>, <span style='color:orange;'>5-6: moderate risks</span>, <span style='color:green;'>7-10: very low risk</span>",
        "Risk for Operations": "<span style='color:red;'>1-4: high operational risk</span>, <span style='color:orange;'>5-6: moderate risk</span>, <span style='color:green;'>7-10: minimal risk</span>",
        "Impact on Product Quality": "<span style='color:red;'>1-4: reduces quality</span>, <span style='color:orange;'>5-6: acceptable</span>, <span style='color:green;'>7-10: improves or maintains quality</span>",
        "Customer and Stakeholder Alignment": "<span style='color:red;'>1-4: low alignment</span>, <span style='color:orange;'>5-6: moderate</span>, <span style='color:green;'>7-10: high alignment</span>",
        "Priority for our organisation": "<span style='color:red;'>1-4: low priority</span>, <span style='color:orange;'>5-6: moderate</span>, <span style='color:green;'>7-10: top priority</span>",
        "Initial investment (£)": "Enter the upfront cost needed (no scale limit).",
        "Return on Investment (ROI)(years)": "Enter the time (in years) to recover the initial cost (no scale limit).",
        "Other": "If your desired criterion is not listed, select this and specify it."
    }

    # Let user select criteria
    selected_criteria = st.multiselect(
        "Select the criteria you want to consider:",
        list(criteria_options.keys())
    )

    # Initialize other_name and other_scale to avoid UnboundLocalError
    other_name = ""
    other_scale = "Yes"

    # If user selected "Other", ask for custom criterion name and a yes/no question
    if "Other" in selected_criteria:
        other_name = st.text_input("Enter the name for the 'Other' criterion:")
        other_scale = st.radio("Does a higher number represent a more beneficial (e.g., more sustainable) outcome for this 'Other' criterion?", ["Yes", "No"])
        if other_name.strip():
            # Replace "Other" with user-defined name
            selected_criteria.remove("Other")
            selected_criteria.append(other_name.strip())
            # Include a note based on their response
            if other_scale == "Yes":
                criteria_options[other_name.strip()] = "1-10 scale, higher = more beneficial"
            else:
                criteria_options[other_name.strip()] = "1-10 scale, higher = less beneficial (inverse interpretation)"

    # Show descriptions for selected criteria (with HTML enabled)
    for crit in selected_criteria:
        st.markdown(f"**{crit}:** {criteria_options[crit]}", unsafe_allow_html=True)

    # If criteria selected, display an editable table for scenarios vs criteria
    if selected_criteria:
        scenario_names = results_df["Scenario"].tolist()
        criteria_df = pd.DataFrame(columns=["Scenario"] + selected_criteria)
        criteria_df["Scenario"] = scenario_names

        # Initialize all values to 0
        for c in selected_criteria:
            criteria_df[c] = 0

        st.write("Please assign values for each selected criterion to each scenario. Double-click a cell to edit. For (1-10) criteria, only enter values between 1 and 10.")

        # Determine which criteria are scale-based (1-10) and which are free input
        scale_criteria = {
            "Technical Feasibility", "Supplier Reliability and Technology Readiness", "Implementation Complexity",
            "Scalability", "Maintenance Requirements", "Regulatory Compliance", "Risk for Workforce Safety",
            "Risk for Operations", "Impact on Product Quality", "Customer and Stakeholder Alignment",
            "Priority for our organisation"
        }

        # Also consider the "Other" criterion if added as scale-based (since we said 1-10 scale)
        if other_name.strip():
            scale_criteria.add(other_name.strip())

        # Automatically assign values based on scenario descriptions
        for i, row in edited_scenario_desc_df.iterrows():
            description = row["Description"]
            assigned_values = keyword_based_assignment(description)
            for crit in assigned_values:
                if crit in criteria_df.columns:
                    criteria_df.loc[criteria_df["Scenario"] == row["Scenario"], crit] = assigned_values[crit]

        # Create column configs for st.data_editor if available (Streamlit 1.22+)
        column_config = {}
        column_config["Scenario"] = st.column_config.TextColumn("Scenario", disabled=True)
        for crit in selected_criteria:
            if crit in scale_criteria:
                # Numeric column with 1-10 limits
                column_config[crit] = st.column_config.NumberColumn(label=crit, min_value=1, max_value=10, step=1)
            elif crit in ["Initial investment (£)", "Return on Investment (ROI)(years)"]:
                # Numeric column with no strict limit
                column_config[crit] = st.column_config.NumberColumn(label=crit)
            else:
                # Other criterion might not have a scale, assume free numeric input
                column_config[crit] = st.column_config.NumberColumn(label=crit)

        criteria_df.index = range(1, len(criteria_df) + 1)  # Start indexing from 1

        try:
            edited_criteria_df = st.data_editor(criteria_df, use_container_width=True, column_config=column_config)
        except AttributeError:
            # If st.data_editor not available, fallback without column_config
            edited_criteria_df = st.experimental_data_editor(criteria_df, use_container_width=True)

        # After editing, `edited_criteria_df` contains the final user inputs
        # Further calculations or displays can be done here as needed.

# Only proceed if criteria were selected and edited_criteria_df is defined
if selected_criteria and 'edited_criteria_df' in locals() and edited_criteria_df is not None and not edited_criteria_df.empty:
    if st.button("Run Model"):
        # Create a copy for scaled results
        scaled_criteria_df = edited_criteria_df.copy()

        # Define which criteria need inversion (lower is better)
        inversion_criteria = []
        if "Return on Investment (ROI)(years)" in selected_criteria:
            inversion_criteria.append("Return on Investment (ROI)(years)")
        if "Initial investment (£)" in selected_criteria:
            inversion_criteria.append("Initial investment (£)")

       # Handle the 'Other' criterion if applicable
if 'other_name' in locals() and other_name.strip():
    if 'other_scale' in locals() and other_scale == "No":
        # Add other_name to inversion criteria
        inversion_criteria.append(other_name.strip())
    else:
        # other_scale == "Yes" means higher is better, so treat it as a scale criterion
        scale_criteria.add(other_name.strip())

# Now scale each criterion
for crit in selected_criteria:
    values = scaled_criteria_df[crit].values.astype(float)
    min_val = np.min(values)
    max_val = np.max(values)

    if crit in scale_criteria:
        # Already 1-10 scale where higher is better. Just ensure values are valid.
        pass

    elif crit in inversion_criteria:
        # Invert scale: lower value -> 10, higher value -> 1
        if max_val == min_val:
            scaled_values = np.ones_like(values) * 10 if min_val != 0 else np.zeros_like(values)
        else:
            scaled_values = 10 - 9 * (values - min_val) / (max_val - min_val)
        scaled_criteria_df[crit] = scaled_values

    else:
        # For non-scale criteria that are not inverted, scale so min=1, max=10 (higher is better)
        if max_val == min_val:
            scaled_values = np.ones_like(values) * 10 if min_val != 0 else np.zeros_like(values)
        else:
            scaled_values = 1 + 9 * (values - min_val) / (max_val - min_val)
        scaled_criteria_df[crit] = scaled_values

st.write("### Normalised Results (All Criteria Scaled 1-10)")
st.dataframe(scaled_criteria_df)
else:
    st.write("No criteria selected or no data available to scale.")

if __name__ == "__main__":
    main()



            
