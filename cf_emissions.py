import pandas as pd
import streamlit as st
import numpy as np
import openai
import json
import altair as alt  # For advanced visualizations

def main():
    # Set page configuration
    st.set_page_config(page_title="Sustainability Decision Assistant", layout="wide")

    # Main Title and Description
    st.title("Sustainability Decision Assistant")
    st.write("*A tool to prioritize scenarios for carbon savings and resource efficiency, enabling data-driven sustainable decisions.*")

    # Debugging: Display Streamlit and OpenAI package versions
    try:
        st.write(f"**Streamlit Version:** {st.__version__}")
    except AttributeError:
        st.write("**Streamlit Version:** Not Found")
    
    try:
        st.write(f"**OpenAI Package Version:** {openai.__version__}")
    except AttributeError:
        st.write("**OpenAI Package Version:** Not Found")

    # ----------------------- OpenAI API Key Setup -----------------------

    # Retrieve OpenAI API key from Streamlit Secrets
    try:
        openai.api_key = st.secrets["OPENAI_API_KEY"]
    except KeyError:
        st.error("OpenAI API key not found. Please set it in the Streamlit Secrets.")
        st.stop()

    # ----------------------- BAU Inputs -----------------------

    st.subheader("Enter Daily Usage for Business As Usual (BAU)")

    default_items = [
        "Gas (kWh/day)", 
        "Electricity (kWh/day)", 
        "Nitrogen (m³/day)", 
        "Hydrogen (m³/day)", 
        "Argon (m³/day)", 
        "Helium (m³/day)"
    ]

    emission_factors = {
        "Gas (kWh/day)": 0.182928926,         # kg CO₂e/kWh
        "Electricity (kWh/day)": 0.207074289, # kg CO₂e/kWh
        "Nitrogen (m³/day)": 0.090638487,     # kg CO₂e/m³
        "Hydrogen (m³/day)": 1.07856,         # kg CO₂e/m³
        "Argon (m³/day)": 6.342950515,        # kg CO₂e/m³
        "Helium (m³/day)": 0.660501982        # kg CO₂e/m³
    }

    bau_data = pd.DataFrame({
        "Item": default_items,
        "Daily Usage (Units)": [0.0] * len(default_items)
    })

    for i in range(len(bau_data)):
        bau_data.loc[i, "Daily Usage (Units)"] = st.number_input(
            f"{bau_data['Item'][i]}:",
            min_value=0.0,
            step=0.1,
            value=0.0,
            key=f"bau_usage_{i}"
        )

    # Option to add custom items
    st.subheader("Add Custom Items (Optional)")
    st.write("If there are any additional sources of emissions not accounted for above, you can add them here.")
    if st.checkbox("Add custom items?", key="add_custom_items_checkbox"):
        num_custom_items = st.number_input(
            "How many custom items would you like to add?",
            min_value=1,
            step=1,
            value=1,
            key="num_custom_items_input"
        )
        for i in range(int(num_custom_items)):
            item_name = st.text_input(
                f"Custom Item {i + 1} Name:",
                key=f"custom_item_name_{i}"
            )
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
            # Add to BAU Data if item name is provided
            if item_name.strip() != "":
                new_row = pd.DataFrame({"Item": [item_name], "Daily Usage (Units)": [usage]})
                bau_data = pd.concat([bau_data, new_row], ignore_index=True)
                emission_factors[item_name] = emission_factor

    # Fill missing emission factors in the DataFrame
    bau_data["Emission Factor (kg CO₂e/unit)"] = bau_data["Item"].map(emission_factors).fillna(0)

    # Calculate emissions for BAU
    bau_data["Daily Emissions (kg CO₂e)"] = bau_data["Daily Usage (Units)"] * bau_data["Emission Factor (kg CO₂e/unit)"]
    bau_data["Annual Emissions (kg CO₂e)"] = bau_data["Daily Emissions (kg CO₂e)"] * 365

    # ----------------------- Ensure BAU Graph Maintains Input Order -----------------------

    # Reorder bau_data to ensure default items come first, followed by custom items
    custom_items = bau_data[~bau_data["Item"].isin(default_items)]
    bau_data = pd.concat([bau_data[bau_data["Item"].isin(default_items)], custom_items], ignore_index=True)

    # Convert 'Item' to a categorical type to preserve order in the bar chart
    bau_data['Item'] = pd.Categorical(bau_data['Item'], categories=bau_data['Item'], ordered=True)

    # Display BAU summary
    st.write("### BAU Results")
    total_daily_bau = bau_data['Daily Emissions (kg CO₂e)'].sum()
    total_annual_bau = bau_data['Annual Emissions (kg CO₂e)'].sum()

    st.write(f"**Total Daily Emissions (BAU):** {total_daily_bau:.2f} kg CO₂e/day")
    st.write(f"**Total Annual Emissions (BAU):** {total_annual_bau:.2f} kg CO₂e/year")

    # Visualize BAU emissions with preserved order
    st.bar_chart(bau_data.set_index("Item")["Daily Emissions (kg CO₂e)"], use_container_width=True)

    # ----------------------- Scenario Planning -----------------------

    st.subheader("Scenario Planning (Editable Table)")
    num_scenarios = st.number_input(
        "How many scenarios do you want to add?",
        min_value=1,
        step=1,
        value=1,
        key="num_scenarios_input_2"
    )

    # Create a DataFrame for scenario descriptions
    scenario_desc_columns = ["Scenario", "Description"]
    scenario_desc_data = [[f"Scenario {i+1}", ""] for i in range(int(num_scenarios))]
    scenario_desc_df = pd.DataFrame(scenario_desc_data, columns=scenario_desc_columns)

    st.write("Please describe each scenario. Double-click a cell to edit the description.")

    # Editable table for scenario descriptions
    try:
        edited_scenario_desc_df = st.data_editor(scenario_desc_df, use_container_width=True, key="scenario_desc_editor")
    except AttributeError:
        edited_scenario_desc_df = st.experimental_data_editor(scenario_desc_df, use_container_width=True, key="scenario_desc_editor")

    # Save edited scenario descriptions to session state
    st.session_state['edited_scenario_desc_df'] = edited_scenario_desc_df

    # Create a DataFrame with one column per scenario
    scenario_columns = ["Item"] + [f"Scenario {i+1} (%)" for i in range(int(num_scenarios))]
    scenario_data = [[item] + [100.0]*int(num_scenarios) for item in bau_data["Item"]]
    scenario_df = pd.DataFrame(scenario_data, columns=scenario_columns)

    st.write("Please adjust the percentages for each scenario. Double-click a cell to edit the value.")
    st.write("The percentage represents usage relative to BAU. For example, 90% means the item is at 90% of its BAU usage, thereby achieving a 10% reduction.")

    # Editable table for scenario percentages
    try:
        edited_scenario_df = st.data_editor(scenario_df, use_container_width=True, key="scenario_percent_editor")
    except AttributeError:
        edited_scenario_df = st.experimental_data_editor(scenario_df, use_container_width=True, key="scenario_percent_editor")

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

    # ----------------------- Additional Criteria -----------------------

    st.write("Apart from the environmental impact (e.g., CO₂ saved) calculated above, which of the following criteria are also important to your organisation? Please select all that apply and then assign values for each scenario.")

    # Define scale-based criteria globally
    scale_criteria = {
        "Technical Feasibility", "Supplier Reliability and Technology Readiness", "Implementation Complexity",
        "Scalability", "Maintenance Requirements", "Regulatory Compliance", "Risk for Workforce Safety",
        "Risk for Operations", "Impact on Product Quality", "Customer and Stakeholder Alignment",
        "Priority for our organisation"
    }

    # Criteria options with brief, color-coded descriptions for the 1-10 scale criteria
    criteria_options = {
        "Technical Feasibility": "<span style='color:red;'>1-4: low feasibility</span>, <span style='color:orange;'>5-6: moderate</span>, <span style='color:green;'>7-10: high feasibility</span>",
        "Supplier Reliability and Technology Readiness": "<span style='color:red;'>1-4: unreliable/immature</span>, <span style='color:orange;'>5-6: mostly reliable</span>, <span style='color:green;'>7-10: highly reliable/mature</span>",
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
        list(criteria_options.keys()),
        key="selected_criteria_multiselect"
    )

    # If user selected "Other", ask for custom criterion name and a checkbox to indicate inversion
    if "Other" in selected_criteria:
        other_name = st.text_input(
            "Enter the name for the 'Other' criterion:",
            key="other_name_input"
        )
        if other_name.strip():
            # Replace "Other" with user-defined name
            selected_criteria.remove("Other")
            selected_criteria.append(other_name.strip())
            
            # Checkbox to indicate if higher numbers are better
            is_higher_better = st.checkbox(
                f"Does a higher number represent a more beneficial outcome for '{other_name.strip()}'?",
                key="other_scale_checkbox"
            )
            
            # Update criteria options based on user input
            if is_higher_better:
                criteria_options[other_name.strip()] = "1-10 scale, higher = more beneficial"
            else:
                criteria_options[other_name.strip()] = "1-10 scale, higher = less beneficial (inverse interpretation)"
            
            # Update scale_criteria if necessary
            if not is_higher_better:
                scale_criteria.add(other_name.strip())

    # Show descriptions for selected criteria (with HTML enabled)
    for crit in selected_criteria:
        st.markdown(f"**{crit}:** {criteria_options[crit]}", unsafe_allow_html=True)

    # If criteria selected, display an editable table for scenarios vs criteria
    if selected_criteria:
        # Ensure results_df is defined before using it
        if 'results_df' not in locals():
            st.warning("Please run the model to generate scenario results first.")
        else:
            scenario_names = results_df["Scenario"].tolist()
            criteria_df = pd.DataFrame(columns=["Scenario"] + selected_criteria)
            criteria_df["Scenario"] = scenario_names

            # Initialize all values to 1 for scale-based criteria
            for c in selected_criteria:
                criteria_df[c] = 1

            st.write("Please assign values for each selected criterion to each scenario. Double-click a cell to edit. For (1-10) criteria, only enter values between 1 and 10.")

            # Define column configurations
            column_config = {
                "Scenario": st.column_config.TextColumn(
                    "Scenario"
                    # No 'read_only' or 'editable' parameter needed; TextColumn is read-only by default
                )
            }

            for c in selected_criteria:
                if c in scale_criteria:
                    column_config[c] = st.column_config.NumberColumn(
                        label=c,
                        format="%.0f",           # Ensures integer input
                        min_value=1, 
                        max_value=10
                    )
                else:
                    column_config[c] = st.column_config.NumberColumn(
                        label=c
                        # No additional constraints
                    )

            # Editable table for criteria values with input constraints
            try:
                edited_criteria_df = st.data_editor(
                    criteria_df,
                    use_container_width=True,
                    key="criteria_editor",
                    num_rows="dynamic",
                    disabled=False,
                    column_config=column_config  # Updated parameter
                )
            except AttributeError:
                edited_criteria_df = st.experimental_data_editor(
                    criteria_df,
                    use_container_width=True,
                    key="criteria_editor",
                    num_rows="dynamic",
                    disabled=False,
                    column_config=column_config  # Updated parameter
                )

        # ----------------------- AI-Based Scoring -----------------------

        # Assign default scores based on scenario descriptions using AI analysis
        scenario_desc = st.session_state.get('edited_scenario_desc_df')
        if scenario_desc is not None and not scenario_desc.empty:
            for idx, row in scenario_desc.iterrows():
                description = row["Description"].strip()
                scenario = row["Scenario"]

                if description == "":
                    continue  # Skip empty descriptions

                # Prepare the prompt for the AI model
                prompt = f"""
You are an expert sustainability analyst. Based on the following scenario description, assign a score between 1 and 10 for each of the selected sustainability criteria. Provide only the scores in JSON format.

### Scenario Description:
{description}

### Criteria to Evaluate:
{selected_criteria}

### JSON Output:
"""

                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are an expert sustainability analyst."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=150,
                        temperature=0.3,
                    )
                    ai_output = response.choices[0].message['content'].strip()
                    # Attempt to parse the JSON output
                    try:
                        scores = json.loads(ai_output)
                        if isinstance(scores, dict):
                            for crit in selected_criteria:
                                if crit in scores:
                                    score = scores[crit]
                                    # Validate score is between 1 and 10
                                    if isinstance(score, (int, float)) and 1 <= score <= 10:
                                        criteria_df.loc[criteria_df["Scenario"] == scenario, crit] = score
                                    else:
                                        criteria_df.loc[criteria_df["Scenario"] == scenario, crit] = 5  # Neutral score
                                else:
                                    # If criterion not in scores, assign neutral
                                    criteria_df.loc[criteria_df["Scenario"] == scenario, crit] = 5
                        else:
                            # If not a dict, assign neutral scores
                            for crit in selected_criteria:
                                criteria_df.loc[criteria_df["Scenario"] == scenario, crit] = 5
                    except json.JSONDecodeError:
                        # If JSON parsing fails, assign neutral scores
                        for crit in selected_criteria:
                            criteria_df.loc[criteria_df["Scenario"] == scenario, crit] = 5
                except openai.error.OpenAIError as e:
                    st.error(f"Error with OpenAI API: {e}")
                    for crit in selected_criteria:
                        criteria_df.loc[criteria_df["Scenario"] == scenario, crit] = 5
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")
                    for crit in selected_criteria:
                        criteria_df.loc[criteria_df["Scenario"] == scenario, crit] = 5

            # Update the criteria_df with assigned scores
            try:
                edited_criteria_df = st.data_editor(
                    criteria_df, 
                    use_container_width=True, 
                    key="criteria_editor_with_scores", 
                    column_config=column_config  # Updated parameter
                )
            except AttributeError:
                edited_criteria_df = st.experimental_data_editor(
                    criteria_df, 
                    use_container_width=True, 
                    key="criteria_editor_with_scores", 
                    column_config=column_config  # Updated parameter
                )

    # ----------------------- Run Model -----------------------

        # Only proceed if criteria were selected and edited_criteria_df is defined
        if selected_criteria and 'edited_criteria_df' in locals() and edited_criteria_df is not None and not edited_criteria_df.empty:
            if st.button("Run Model"):
                # Check if all required values are filled
                if edited_criteria_df.isnull().values.any():
                    st.error("Please ensure all criteria values are filled.")
                else:
                    # Create a copy for scaled results
                    scaled_criteria_df = edited_criteria_df.copy()

                    # Define which criteria need inversion (lower is better)
                    inversion_criteria = []
                    for crit in selected_criteria:
                        if crit in scale_criteria:
                            inversion_criteria.append(crit)

                    # Now scale each criterion
                    for crit in selected_criteria:
                        try:
                            values = scaled_criteria_df[crit].astype(float).values
                        except:
                            scaled_criteria_df[crit] = 5  # Assign neutral score if conversion fails
                            values = scaled_criteria_df[crit].astype(float).values

                        min_val = np.min(values)
                        max_val = np.max(values)

                        if crit in inversion_criteria:
                            # Invert scale: lower value -> 10, higher value -> 1
                            if max_val == min_val:
                                scaled_values = np.ones_like(values) * 10 if min_val != 0 else np.zeros_like(values)
                            else:
                                scaled_values = 10 - 9 * (values - min_val) / (max_val - min_val)
                            scaled_criteria_df[crit] = scaled_values

                        elif crit in scale_criteria:
                            # Already 1-10 scale where higher is better. Ensure values are within 1-10
                            scaled_values = np.clip(values, 1, 10)
                            scaled_criteria_df[crit] = scaled_values

                        else:
                            # For non-scale criteria that are not inverted, scale so min=1, max=10 (higher is better)
                            if max_val == min_val:
                                scaled_values = np.ones_like(values) * 10 if min_val != 0 else np.zeros_like(values)
                            else:
                                scaled_values = 1 + 9 * (values - min_val) / (max_val - min_val)
                            scaled_criteria_df[crit] = scaled_values

                    # Calculate the sum of criteria for each scenario
                    scaled_criteria_df['Total Score'] = scaled_criteria_df[selected_criteria].sum(axis=1)

                    # Normalize the total scores between 1 and 10
                    min_score = scaled_criteria_df['Total Score'].min()
                    max_score = scaled_criteria_df['Total Score'].max()
                    if max_score != min_score:
                        scaled_criteria_df['Normalized Score'] = 1 + 9 * (scaled_criteria_df['Total Score'] - min_score) / (max_score - min_score)
                    else:
                        scaled_criteria_df['Normalized Score'] = 5  # Assign a neutral score if all scores are equal

                    # Assign colors based on normalized scores
                    def get_color(score):
                        if score >= 7:
                            return 'green'
                        elif score >= 5:
                            return 'yellow'
                        else:
                            return 'red'

                    scaled_criteria_df['Color'] = scaled_criteria_df['Normalized Score'].apply(get_color)

                    # Rank the scenarios based on Normalized Score
                    scaled_criteria_df['Rank'] = scaled_criteria_df['Normalized Score'].rank(method='min', ascending=False).astype(int)

                    st.write("### Normalized Results (All Criteria Scaled 1-10)")
                    st.dataframe(scaled_criteria_df.round(2))

                    # Remove the redundant "Scaled Criteria Table"
                    # st.write("### Scaled Criteria Table")
                    # st.dataframe(scaled_criteria_df.round(2))

                    # Visualize the normalized scores with color gradients using Altair
                    chart = alt.Chart(scaled_criteria_df).mark_bar().encode(
                        x=alt.X('Scenario:N', sort='-y'),
                        y='Normalized Score:Q',
                        color=alt.Color('Normalized Score:Q',
                                        scale=alt.Scale(
                                            domain=[1, 5, 10],
                                            range=['red', 'yellow', 'green']
                                        ),
                                        legend=alt.Legend(title="Normalized Score"))
                    ).properties(
                        width=700,
                        height=400,
                        title="Scenario Scores (Normalized 1-10)"
                    )

                    st.altair_chart(chart, use_container_width=True)

                    # ----------------------- Enhanced Visualization -----------------------

                    # Create a styled dataframe with ranking and color-coded cells
                    styled_display = scaled_criteria_df[['Scenario', 'Normalized Score', 'Rank']].copy()
                    styled_display = styled_display.sort_values('Rank')

                    # Apply color formatting based on 'Normalized Score'
                    def color_cell(score):
                        if score >= 7:
                            return 'background-color: green'
                        elif score >= 5:
                            return 'background-color: yellow'
                        else:
                            return 'background-color: red'

                    # Style the 'Normalized Score' column
                    styled_display_style = styled_display.style.applymap(color_cell, subset=['Normalized Score'])

                    st.write("### Ranked Scenarios with Gradient Colors")
                    st.dataframe(styled_display_style)

    if __name__ == "__main__":
        main()
