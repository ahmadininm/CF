import pandas as pd
import streamlit as st
import numpy as np
import openai
import altair as alt
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize OpenAI API
try:
    from openai.error import OpenAIError
except ImportError:
    OpenAIError = Exception  # Fallback for older SDK versions

def initialize_session_state():
    """Initialize session state variables if they don't exist."""
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

def clear_cache():
    """Clear Streamlit cache and rerun the app."""
    if st.button("Clear Cache"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.experimental_rerun()

def chat_gpt(prompt):
    """Function to interact with OpenAI's ChatCompletion API."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Change to "gpt-4" if you have access
            messages=[{"role": "user", "content": prompt}]
        )
        return response['choices'][0]['message']['content'].strip()
    except OpenAIError as e:
        logger.error(f"OpenAI API Error: {e}")
        st.error(f"OpenAI API Error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        st.error(f"An unexpected error occurred: {e}")
        return None

def main():
    # Initialize session state
    initialize_session_state()
    
    # Set page configuration
    st.set_page_config(page_title="Sustainability Decision Assistant", layout="wide")

    # Main Title and Description
    st.title("Sustainability Decision Assistant")
    st.write("*A tool to prioritize scenarios for carbon savings and resource efficiency, enabling data-driven sustainable decisions.*")

    # Add Cache Clearing Button
    clear_cache()

    # Display Streamlit and OpenAI package versions for debugging
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

    # ----------------------- Process BAU Data -----------------------

    # Ensure 'Emission Factor (kg CO₂e/unit)' is float
    bau_data = st.session_state.bau_data.copy()
    bau_data['Emission Factor (kg CO₂e/unit)'] = bau_data['Item'].map(st.session_state.emission_factors).astype(float).fillna(0.0)
    st.session_state.bau_data = bau_data

    # Calculate emissions for BAU
    st.session_state.bau_data["Daily Emissions (kg CO₂e)"] = st.session_state.bau_data["Daily Usage (Units)"] * st.session_state.bau_data["Emission Factor (kg CO₂e/unit)"]
    st.session_state.bau_data["Annual Emissions (kg CO₂e)"] = st.session_state.bau_data["Daily Emissions (kg CO₂e)"] * 365

    # Reorder bau_data to ensure default items come first, followed by custom items
    default_items = [
        "Gas (kWh/day)", 
        "Electricity (kWh/day)", 
        "Nitrogen (m³/day)", 
        "Hydrogen (m³/day)", 
        "Argon (m³/day)", 
        "Helium (m³/day)"
    ]
    custom_items = st.session_state.bau_data[~st.session_state.bau_data["Item"].isin(default_items)]
    bau_data = pd.concat([st.session_state.bau_data[st.session_state.bau_data["Item"].isin(default_items)], custom_items], ignore_index=True)
    st.session_state.bau_data = bau_data

    # Display BAU summary
    st.write("### BAU Results")
    total_daily_bau = bau_data['Daily Emissions (kg CO₂e)'].sum()
    total_annual_bau = bau_data['Annual Emissions (kg CO₂e)'].sum()

    st.write(f"**Total Daily Emissions (BAU):** {total_daily_bau:.2f} kg CO₂e/day")
    st.write(f"**Total Annual Emissions (BAU):** {total_annual_bau:.2f} kg CO₂e/year")

    # Visualize BAU emissions with preserved order
    st.bar_chart(bau_data.set_index("Item")["Daily Emissions (kg CO₂e)"], use_container_width=True)

    # ----------------------- Propose Scenarios Using AI -----------------------

    st.subheader("Propose Scenarios Using AI")

    st.write("To help you generate relevant scenarios, please provide some details about your organization's activities and sustainability goals.")

    activities = st.text_area(
        "Describe your organization's key activities and sustainability goals:",
        height=150,
        key="activities_input"
    )

    if st.button("Generate Proposed Scenarios", key="generate_scenarios_button"):
        if activities.strip() == "":
            st.error("Please provide details about your organization's activities and sustainability goals.")
        else:
            prompt = f"""
You are an expert sustainability consultant. Based on the following description of an organization's activities and sustainability goals, propose three innovative scenarios to improve carbon savings and resource efficiency. Provide only the scenario names and brief descriptions in a list format.

### Description:
{activities}

### Proposed Scenarios:
1.
2.
3.
"""

            ai_output = chat_gpt(prompt)
            if ai_output:
                # Parse the AI output into a list of scenarios
                scenarios = []
                for line in ai_output.split('\n'):
                    if line.strip().startswith(('1.', '2.', '3.')):
                        scenario = line.split('.', 1)[1].strip()
                        scenarios.append(scenario)

                if len(scenarios) < 3:
                    st.warning("AI was unable to generate three distinct scenarios. Please consider providing more detailed information.")
                else:
                    st.session_state.proposed_scenarios = scenarios[:3]
                    st.session_state.ai_proposed = True
                    st.success("Proposed scenarios generated successfully!")

    # Display Proposed Scenarios
    if st.session_state.proposed_scenarios:
        st.write("### Proposed Scenarios")
        for idx, scenario in enumerate(st.session_state.proposed_scenarios, 1):
            st.write(f"**{idx}. {scenario}**")
        
        st.write("You can choose to accept these scenarios or modify them as needed.")

    # ----------------------- Scenario Planning -----------------------

    st.subheader("Scenario Planning (Editable Table)")

    # Determine default scenarios (proposed by AI) or allow user to input their own
    if st.session_state.proposed_scenarios and st.session_state.ai_proposed:
        proposed = st.radio(
            "Would you like to use the AI-proposed scenarios?",
            ("Yes", "No"),
            key="use_proposed_scenarios_radio"
        )
        if proposed == "Yes":
            num_scenarios = len(st.session_state.proposed_scenarios)
            scenario_names = [f"Scenario {i+1}" for i in range(num_scenarios)]
            scenario_descriptions = st.session_state.proposed_scenarios
            st.session_state.scenario_desc_df = pd.DataFrame({
                "Scenario": scenario_names,
                "Description": scenario_descriptions
            })
            st.session_state.ai_proposed = False  # Reset after acceptance
        else:
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
            st.session_state.scenario_desc_df = scenario_desc_df
            st.session_state.proposed_scenarios = []  # Clear proposed scenarios

    else:
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
        st.session_state.scenario_desc_df = scenario_desc_df

    st.write("Please describe each scenario. Double-click a cell to edit the description.")

    # Editable table for scenario descriptions
    try:
        edited_scenario_desc_df = st.data_editor(st.session_state.scenario_desc_df, use_container_width=True, key="scenario_desc_editor", num_rows="fixed")
    except AttributeError:
        # Fallback for older Streamlit versions
        edited_scenario_desc_df = st.experimental_data_editor(st.session_state.scenario_desc_df, use_container_width=True, key="scenario_desc_editor", num_rows="fixed")

    # Save edited scenario descriptions to session state
    st.session_state['scenario_desc_df'] = edited_scenario_desc_df

    # Create a DataFrame with one column per scenario
    scenario_columns = ["Item"] + [f"{row['Scenario']} (%)" for index, row in st.session_state.scenario_desc_df.iterrows()]
    scenario_data = [[item] + [100.0]*len(st.session_state.scenario_desc_df) for item in bau_data["Item"]]
    scenario_df = pd.DataFrame(scenario_data, columns=scenario_columns)

    st.write("Please adjust the percentages for each scenario. Double-click a cell to edit the value.")
    st.write("The percentage represents usage relative to BAU. For example, 90% means the item is at 90% of its BAU usage, thereby achieving a 10% reduction.")

    # Editable table for scenario percentages
    try:
        edited_scenario_df = st.data_editor(scenario_df, use_container_width=True, key="scenario_percent_editor", num_rows="fixed")
    except AttributeError:
        # Fallback for older Streamlit versions
        edited_scenario_df = st.experimental_data_editor(scenario_df, use_container_width=True, key="scenario_percent_editor", num_rows="fixed")

    # Update session state with edited scenario percentages
    st.session_state['scenario_percent_df'] = edited_scenario_df

    # Convert columns (except Item) to numeric
    for col in edited_scenario_df.columns[1:]:
        edited_scenario_df[col] = pd.to_numeric(edited_scenario_df[col], errors='coerce').fillna(100.0)

    # ----------------------- Additional Criteria -----------------------

    st.write("Apart from the environmental impact (e.g., CO₂ saved) calculated above, which of the following criteria are also important to your organisation? Please select all that apply and then assign values for each scenario.")

    # Define scale-based criteria globally, including 'Other - Negative Trend'
    scale_criteria = {
        "Technical Feasibility", 
        "Supplier Reliability and Technology Readiness", 
        "Implementation Complexity",
        "Scalability", 
        "Maintenance Requirements", 
        "Regulatory Compliance", 
        "Risk for Workforce Safety",
        "Risk for Operations", 
        "Impact on Product Quality", 
        "Customer and Stakeholder Alignment",
        "Priority for our organisation",
        "Other - Negative Trend"  # For inversion
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
        "Other - Positive Trend": "Enter criteria where a higher number is more beneficial.",
        "Other - Negative Trend": "Enter criteria where a higher number is less beneficial."
    }

    # Allow adding multiple "Other" criteria dynamically
    selected_other_trends = [crit for crit in st.session_state.selected_criteria if crit in ["Other - Positive Trend", "Other - Negative Trend"]]
    
    # Initialize list to keep track of dynamically added "Other" criteria
    for trend in selected_other_trends:
        st.write(f"### {trend}")
        num_other = st.number_input(
            f"How many '{trend}' criteria would you like to add?",
            min_value=1,
            step=1,
            value=1,
            key=f"num_{trend.replace(' ', '_')}_input"
        )
        for i in range(int(num_other)):
            other_crit_name = st.text_input(
                f"{trend} Criterion {i+1} Name:",
                key=f"{trend.replace(' ', '_')}_name_{i}"
            )
            other_crit_desc = st.text_input(
                f"{trend} Criterion {i+1} Description:",
                key=f"{trend.replace(' ', '_')}_desc_{i}"
            )
            if other_crit_name.strip() != "":
                full_crit_name = other_crit_name.strip()
                if full_crit_name not in criteria_options:
                    # Add the new "Other" criteria to the criteria_options
                    criteria_options[full_crit_name] = other_crit_desc.strip() if other_crit_desc.strip() != "" else "No description provided."
                    # Add to dynamic_other_criteria for persistence
                    if 'dynamic_other_criteria' not in st.session_state:
                        st.session_state.dynamic_other_criteria = []
                    st.session_state.dynamic_other_criteria.append(full_crit_name)
                else:
                    st.warning(f"Criterion '{full_crit_name}' already exists.")

    # Allow adding new "Other" criteria beyond initial selections
    st.write("### Add More 'Other' Criteria")
    add_more_other = st.checkbox("Add more 'Other' criteria", key="add_more_other_checkbox")
    if add_more_other:
        new_other_trend = st.selectbox(
            "Select trend type for the new 'Other' criterion:",
            ["Other - Positive Trend", "Other - Negative Trend"],
            key="new_other_trend_select"
        )
        new_other_name = st.text_input(
            "Enter the name for the new 'Other' criterion:",
            key="new_other_name_input"
        )
        new_other_desc = st.text_input(
            "Enter a brief description for the new 'Other' criterion:",
            key="new_other_desc_input"
        )
        if new_other_name.strip() != "":
            full_crit_name = new_other_name.strip()
            if full_crit_name not in criteria_options:
                criteria_options[full_crit_name] = new_other_desc.strip() if new_other_desc.strip() != "" else "No description provided."
                if 'dynamic_other_criteria' not in st.session_state:
                    st.session_state.dynamic_other_criteria = []
                st.session_state.dynamic_other_criteria.append(full_crit_name)
                st.success(f"Added new criterion '{full_crit_name}'.")
            else:
                st.warning(f"Criterion '{full_crit_name}' already exists.")

    # Let user select criteria
    selected_criteria = st.multiselect(
        "Select the criteria you want to consider:",
        list(criteria_options.keys()),
        key="selected_criteria_multiselect"
    )
    st.session_state.selected_criteria = selected_criteria  # Update session state

    # Show descriptions for selected criteria (with HTML enabled)
    for crit in selected_criteria:
        st.markdown(f"**{crit}:** {criteria_options[crit]}", unsafe_allow_html=True)

    # Define scale-based criteria globally, including 'Other - Negative Trend'
    scale_criteria = {
        "Technical Feasibility", 
        "Supplier Reliability and Technology Readiness", 
        "Implementation Complexity",
        "Scalability", 
        "Maintenance Requirements", 
        "Regulatory Compliance", 
        "Risk for Workforce Safety",
        "Risk for Operations", 
        "Impact on Product Quality", 
        "Customer and Stakeholder Alignment",
        "Priority for our organisation",
        "Other - Negative Trend"  # For inversion
    }

    # If criteria selected, display an editable table for scenarios vs criteria
    if selected_criteria:
        # Initialize or update criteria_df in session state
        if st.session_state.criteria_df.empty:
            criteria_df = pd.DataFrame(columns=["Scenario"] + selected_criteria)
            # Assign scenario names from scenario_desc_df
            criteria_df["Scenario"] = st.session_state.scenario_desc_df["Scenario"].tolist()
            for c in selected_criteria:
                criteria_df[c] = 1
            st.session_state.criteria_df = criteria_df
        else:
            # Update criteria_df columns based on selected_criteria
            criteria_df = st.session_state.criteria_df.copy()
            for c in selected_criteria:
                if c not in criteria_df.columns:
                    criteria_df[c] = 1
            # Remove criteria that are no longer selected
            for c in list(criteria_df.columns):
                if c not in selected_criteria and c != "Scenario":
                    criteria_df = criteria_df.drop(columns=[c])
            st.session_state.criteria_df = criteria_df

        # Define column configurations
        column_config = {
            "Scenario": st.column_config.TextColumn(
                "Scenario",
                disabled=True  # Make Scenario column read-only
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

        st.write("Please assign values for each selected criterion to each scenario. Double-click a cell to edit. For (1-10) criteria, only enter values between 1 and 10.")

        # Editable table for criteria values with input constraints
        try:
            edited_criteria_df = st.data_editor(
                st.session_state.criteria_df,
                use_container_width=True,
                key="criteria_editor",
                num_rows="dynamic",
                disabled=False,
                column_config=column_config,
                hide_index=True,
                editable=True
            )
        except AttributeError:
            # Fallback for older Streamlit versions
            edited_criteria_df = st.experimental_data_editor(
                st.session_state.criteria_df,
                use_container_width=True,
                key="criteria_editor",
                num_rows="dynamic",
                disabled=False
            )

        # Update session state with edited criteria
        st.session_state.criteria_df = edited_criteria_df

    # ----------------------- Run Model -----------------------

    # Only proceed if criteria were selected and edited_criteria_df is defined
    if selected_criteria and 'criteria_df' in st.session_state and not st.session_state.criteria_df.empty:
        if st.button("Run Model"):
            # Check if all required values are filled
            if st.session_state.criteria_df.isnull().values.any():
                st.error("Please ensure all criteria values are filled.")
            else:
                # Create a copy for scaled results
                scaled_criteria_df = st.session_state.criteria_df.copy()

                # Define specific criteria to normalize
                criteria_to_normalize = ["Return on Investment (ROI)(years)", "Initial investment (£)", "Other - Positive Trend", "Other - Negative Trend"]

                # Now scale each criterion
                for crit in selected_criteria:
                    if crit not in criteria_to_normalize:
                        continue  # Skip criteria that don't need normalization

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

                # Calculate the sum of normalized criteria for each scenario
                scaled_criteria_df['Total Score'] = scaled_criteria_df[selected_criteria].sum(axis=1)

                # Normalize the total scores between 1 and 10
                min_score = scaled_criteria_df['Total Score'].min()
                max_score = scaled_criteria_df['Total Score'].max()
                if max_score != min_score:
                    scaled_criteria_df['Normalized Score'] = 1 + 9 * (scaled_criteria_df['Total Score'] - min_score) / (max_score - min_score)
                else:
                    scaled_criteria_df['Normalized Score'] = 5  # Assign a neutral score if all scores are equal

                # Calculate CO₂ Savings
                scaled_criteria_df['CO₂ Saving (kg CO₂e/year)'] = total_annual_bau - (scaled_criteria_df['Total Score'] - scaled_criteria_df['Normalized Score'])
                scaled_criteria_df['CO₂ Saving (%)'] = (scaled_criteria_df['CO₂ Saving (kg CO₂e/year)'] / total_annual_bau * 100) if total_annual_bau != 0 else 0

                # Rank the scenarios based on Total Score
                scaled_criteria_df['Rank'] = scaled_criteria_df['Total Score'].rank(method='min', ascending=False).astype(int)

                st.write("### Scenario Results")
                st.dataframe(scaled_criteria_df.round(2))

                st.subheader("CO₂ Savings Compared to BAU (%)")
                st.bar_chart(scaled_criteria_df.set_index("Scenario")["CO₂ Saving (%)"], use_container_width=True)

                # Option to download scenario results as CSV
                st.download_button(
                    label="Download Scenario Results as CSV",
                    data=scaled_criteria_df.to_csv(index=False),
                    file_name="scenario_results.csv",
                    mime="text/csv"
                )

                # ----------------------- Enhanced Visualization -----------------------

                # Create a styled dataframe with ranking and color-coded cells
                styled_display = scaled_criteria_df[['Scenario', 'Normalized Score', 'Rank']].copy()
                styled_display = styled_display.sort_values('Rank')

                # Apply color formatting based on 'Normalized Score' using Styler.map
                styled_display_style = styled_display.style.applymap(
                    lambda x: 'background-color: green' if x >=7 else ('background-color: yellow' if x >=5 else 'background-color: red'),
                    subset=['Normalized Score']
                )

                st.write("### Ranked Scenarios with Gradient Colors")
                st.dataframe(styled_display_style)

    if __name__ == "__main__":
        main()
