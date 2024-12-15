import pandas as pd
import streamlit as st
import numpy as np
import openai
import json
import altair as alt  # For advanced visualizations
import base64  # For encoding download data

# For OpenAI SDK >=1.0.0
try:
    from openai.error import OpenAIError
except ImportError:
    # For older OpenAI SDK versions
    OpenAIError = Exception

# ----------------------- Helper Functions -----------------------
def generate_scenarios(description, num_scenarios):
    """
    Uses OpenAI's GPT model to generate scenario suggestions based on the activities description.

    Args:
        description (str): The activities description input by the user.
        num_scenarios (int): The number of scenarios to generate.

    Returns:
        list of dict: Generated scenarios with 'name' and 'description'.
    """
    prompt = (
        f"Based on the following description of an organization's activities and sustainability goals, "
        f"generate {num_scenarios} detailed sustainability scenarios. "
        f"Each scenario should include a name and a brief description.\n\n"
        f"Description:\n{description}\n\n"
        f"Scenarios:"
    )
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # You can choose a different model if desired
            messages=[
                {"role": "system", "content": "You are an expert sustainability analyst."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7,
        )
        scenarios_text = response.choices[0].message.content.strip()
        scenarios = []
        for line in scenarios_text.split('\n'):
            if line.strip() == "":
                continue
            # Assuming scenarios are listed as "1. Name: Description"
            if '.' in line:
                parts = line.split('.', 1)
                name_desc = parts[1].strip()
                if ':' in name_desc:
                    name, desc = name_desc.split(':', 1)
                    scenarios.append({"name": name.strip(), "description": desc.strip()})
        return scenarios
    except OpenAIError as e:
        st.error(f"OpenAI API Error: {e}")
        return []
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return []

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

    # ----------------------- Initialize Session State -----------------------

    if 'bau_data' not in st.session_state:
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
        st.session_state.bau_data = pd.DataFrame({
            "Item": default_items,
            "Daily Usage (Units)": [0.0] * len(default_items)
        })
        st.session_state.emission_factors = emission_factors.copy()
    
    if 'scenario_desc_df' not in st.session_state:
        st.session_state.scenario_desc_df = pd.DataFrame(columns=["Scenario", "Description"])
    
    if 'criteria_df' not in st.session_state:
        st.session_state.criteria_df = pd.DataFrame(columns=["Scenario"])
    
    if 'selected_criteria' not in st.session_state:
        st.session_state.selected_criteria = []
    
    if 'proposed_scenarios' not in st.session_state:
        st.session_state.proposed_scenarios = []
    
    if 'ai_proposed' not in st.session_state:
        st.session_state.ai_proposed = False

    # ----------------------- BAU Inputs -----------------------

    st.subheader("Enter Daily Usage for Business As Usual (BAU)")

    # Display BAU Inputs
    bau_data = st.session_state.bau_data
    emission_factors = st.session_state.emission_factors

    for i in range(len(bau_data)):
        bau_data.loc[i, "Daily Usage (Units)"] = st.number_input(
            f"{bau_data['Item'][i]}:",
            min_value=0.0,
            step=0.1,
            value=bau_data.loc[i, "Daily Usage (Units)"],
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
            # Add to BAU Data if item name is provided and not duplicate
            if item_name.strip() != "":
                if item_name.strip() not in bau_data["Item"].values:
                    new_row = pd.DataFrame({"Item": [item_name.strip()], "Daily Usage (Units)": [usage]})
                    st.session_state.bau_data = pd.concat([bau_data, new_row], ignore_index=True)
                    st.session_state.emission_factors[item_name.strip()] = emission_factor
                    # Update 'bau_data' variable to include new row
                    bau_data = st.session_state.bau_data
                else:
                    st.warning(f"Item '{item_name.strip()}' already exists.")

    # Fill missing emission factors in the DataFrame
    bau_data = st.session_state.bau_data.copy()
    bau_data["Emission Factor (kg CO₂e/unit)"] = bau_data["Item"].map(st.session_state.emission_factors).fillna(0.0)

    # Calculate emissions for BAU
    bau_data["Daily Emissions (kg CO₂e)"] = bau_data["Daily Usage (Units)"] * bau_data["Emission Factor (kg CO₂e/unit)"]
    bau_data["Annual Emissions (kg CO₂e)"] = bau_data["Daily Emissions (kg CO₂e)"] * 365

    # ----------------------- Ensure BAU Graph Maintains Input Order -----------------------

    # Reorder bau_data to ensure default items come first, followed by custom items
    default_items = [
        "Gas (kWh/day)", 
        "Electricity (kWh/day)", 
        "Nitrogen (m³/day)", 
        "Hydrogen (m³/day)", 
        "Argon (m³/day)", 
        "Helium (m³/day)"
    ]
    custom_items = bau_data[~bau_data["Item"].isin(default_items)]
    bau_data_ordered = pd.concat([bau_data[bau_data["Item"].isin(default_items)], custom_items], ignore_index=True)

    # Convert 'Item' to a categorical type to preserve order in the bar chart
    bau_data_ordered['Item'] = pd.Categorical(bau_data_ordered['Item'], categories=bau_data_ordered['Item'], ordered=True)

    # Display BAU summary
    st.write("### BAU Results")
    total_daily_bau = bau_data_ordered['Daily Emissions (kg CO₂e)'].sum()
    total_annual_bau = bau_data_ordered['Annual Emissions (kg CO₂e)'].sum()

    st.write(f"**Total Daily Emissions (BAU):** {total_daily_bau:.2f} kg CO₂e/day")
    st.write(f"**Total Annual Emissions (BAU):** {total_annual_bau:.2f} kg CO₂e/year")

    # Visualize BAU emissions with preserved order
    st.bar_chart(bau_data_ordered.set_index("Item")["Daily Emissions (kg CO₂e)"], use_container_width=True)

    # ----------------------- Describe Activities to Propose Scenarios -----------------------

    st.subheader("Describe Your Organization's Activities")
    st.write("Provide a brief description of your organization's key activities and sustainability goals to help propose relevant scenarios.")

    activities_description = st.text_area(
        "Describe your organization's key activities and sustainability goals:",
        height=150,
        key="activities_description_input"
    )

    # ----------------------- Optional Scenario Generation -----------------------
    st.subheader("Optional: Generate Scenarios Using OpenAI")
    generate_scenarios_toggle = st.checkbox("Generate scenarios using OpenAI", value=False, key="generate_scenarios_toggle")

    if generate_scenarios_toggle:
        if activities_description.strip() == "":
            st.warning("Please provide a description of your organization's activities to generate scenarios.")
        else:
            if st.button("Generate Scenarios"):
                num_scenarios = st.number_input(
                    "How many scenarios would you like to generate?",
                    min_value=1,
                    step=1,
                    value=3,
                    key="num_scenarios_to_generate"
                )
                with st.spinner("Generating scenarios..."):
                    generated_scenarios = generate_scenarios(activities_description, int(num_scenarios))
                    if generated_scenarios:
                        # Create a DataFrame for scenario descriptions
                        scenario_desc_columns = ["Scenario", "Description"]
                        scenario_desc_data = [[scenario['name'], scenario['description']] for scenario in generated_scenarios]
                        scenario_desc_df = pd.DataFrame(scenario_desc_data, columns=scenario_desc_columns)
                        
                        # Update the session state with generated scenarios
                        st.session_state.scenario_desc_df = scenario_desc_df
                        st.session_state.ai_proposed = True
                        st.success("Scenarios generated successfully! You can now review and edit them as needed.")
                    else:
                        st.error("No scenarios were generated. Please try again or enter a more detailed description.")

    # ----------------------- Scenario Planning -----------------------

    st.subheader("Scenario Planning (Editable Table)")

    # Let users define scenarios manually or use AI-generated scenarios
    if activities_description.strip() != "" and not generate_scenarios_toggle:
        st.success("Activities description received. You can now define your scenarios based on this information.")
    elif generate_scenarios_toggle and st.session_state.get('ai_proposed', False):
        st.success("AI-generated scenarios are available. You can review and edit them below.")

    # Number of scenarios input
    num_scenarios = st.number_input(
        "How many scenarios do you want to add?",
        min_value=1,
        step=1,
        value=1,
        key="num_scenarios_input_2"
    )

    # Create a DataFrame for scenario descriptions
    if st.session_state.scenario_desc_df.empty:
        scenario_desc_columns = ["Scenario", "Description"]
        scenario_desc_data = [[f"Scenario {i+1}", ""] for i in range(int(num_scenarios))]
    else:
        scenario_desc_columns = ["Scenario", "Description"]
        scenario_desc_data = st.session_state.scenario_desc_df.values.tolist()
        # Adjust the number of scenarios based on user input
        if int(num_scenarios) > len(scenario_desc_data):
            for i in range(int(num_scenarios) - len(scenario_desc_data)):
                scenario_desc_data.append([f"Scenario {len(scenario_desc_data)+1}", ""])
        elif int(num_scenarios) < len(scenario_desc_data):
            scenario_desc_data = scenario_desc_data[:int(num_scenarios)]

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
    scenario_columns = ["Item"] + [f"{row['Scenario']} (%)" for index, row in edited_scenario_desc_df.iterrows()]
    scenario_data = [[item] + [100.0]*int(num_scenarios) for item in bau_data_ordered["Item"]]
    scenario_df = pd.DataFrame(scenario_data, columns=scenario_columns)

    st.write("Please assign values for each selected criterion to each scenario. Double-click a cell to edit. For (1-10) criteria, only enter values between 1 and 10.")

    # Editable table for scenario percentages
    try:
        edited_scenario_df = st.data_editor(scenario_df, use_container_width=True, key="scenario_percent_editor")
    except AttributeError:
        edited_scenario_df = st.experimental_data_editor(scenario_df, use_container_width=True, key="scenario_percent_editor")

    # Convert columns (except Item) to numeric
    for col in edited_scenario_df.columns[1:]:
        edited_scenario_df[col] = pd.to_numeric(edited_scenario_df[col], errors='coerce').fillna(100.0)

    # Save edited criteria to session state
    st.session_state['edited_criteria_df'] = edited_scenario_df

    # ----------------------- Run Model -----------------------

    # Only proceed if criteria were selected and edited_criteria_df is defined
    if 'edited_criteria_df' in st.session_state and not st.session_state.edited_criteria_df.empty:
        if st.button("Run Model"):
            # Check if all required values are filled
            if st.session_state.edited_criteria_df.isnull().values.any():
                st.error("Please ensure all criteria values are filled.")
            else:
                # Create a copy for scaled results
                scaled_criteria_df = st.session_state.edited_criteria_df.copy()

                # Define specific criteria to normalize (if any)
                criteria_to_normalize = ["Return on Investment (ROI)(years)", "Initial investment (£)", "Other - Positive Trend", "Other - Negative Trend"]

                # Now scale each criterion
                for crit in criteria_to_normalize:
                    if crit in scaled_criteria_df.columns:
                        try:
                            values = scaled_criteria_df[crit].astype(float).values
                        except:
                            scaled_criteria_df[crit] = 5  # Assign neutral score if conversion fails
                            values = scaled_criteria_df[crit].astype(float).values

                        min_val = np.min(values)
                        max_val = np.max(values)

                        if crit == "Other - Positive Trend":
                            # Higher is better: scale to 10
                            if max_val == min_val:
                                scaled_values = np.ones_like(values) * 10 if min_val != 0 else np.zeros_like(values)
                            else:
                                scaled_values = 1 + 9 * (values - min_val) / (max_val - min_val)
                            scaled_criteria_df[crit] = scaled_values
                        elif crit == "Other - Negative Trend":
                            # Higher is worse: reverse scale
                            if max_val == min_val:
                                scaled_values = np.ones_like(values) * 10 if min_val != 0 else np.zeros_like(values)
                            else:
                                scaled_values = 10 - 9 * (values - min_val) / (max_val - min_val)
                            scaled_criteria_df[crit] = scaled_values
                        elif crit == "Return on Investment (ROI)(years)":
                            # Lower ROI is better: reverse scale
                            if max_val == min_val:
                                scaled_values = np.ones_like(values) * 10 if min_val != 0 else np.zeros_like(values)
                            else:
                                scaled_values = 10 - 9 * (values - min_val) / (max_val - min_val)
                            scaled_criteria_df[crit] = scaled_values
                        elif crit == "Initial investment (£)":
                            # Lower investment is better: reverse scale
                            if max_val == min_val:
                                scaled_values = np.ones_like(values) * 10 if min_val != 0 else np.zeros_like(values)
                            else:
                                scaled_values = 10 - 9 * (values - min_val) / (max_val - min_val)
                            scaled_criteria_df[crit] = scaled_values

                # Calculate the total score by summing all criteria
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

                # ----------------------- Highlight Top Scenario -----------------------

                top_scenario = scaled_criteria_df.loc[scaled_criteria_df['Rank'] == 1, 'Scenario'].values
                if len(top_scenario) > 0:
                    st.success(f"The top-ranked scenario is **{top_scenario[0]}** with the highest carbon savings.")

    if __name__ == "__main__":
        main()
