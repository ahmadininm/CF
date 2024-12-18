import pandas as pd
import streamlit as st
import numpy as np
import json
import altair as alt  # For advanced visualizations
import base64
from io import BytesIO
import openai  # For OpenAI API integration
import importlib.metadata

# Import specific exceptions from openai.error instead of openai
from openai.error import InvalidRequestError, AuthenticationError, RateLimitError, OpenAIError

# ----------------------- OpenAI Configuration -----------------------
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ----------------------- Helper Functions -----------------------
def get_openai_version_importlib():
    try:
        version = importlib.metadata.version('openai')
        return version
    except importlib.metadata.PackageNotFoundError:
        return "Package not found."
# ----------------------- Test OpenAI Linkage -----------------------
def test_openai_linkage():
    try:
        # Attempt a simple API call to test linkage
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello!"}
            ],
            max_tokens=10,
            temperature=0.7,
        )
        message = response.choices[0].message.content.strip()
        st.success(f"OpenAI API is working fine. Response: {message}")
    except InvalidRequestError as e:
        st.error(f"OpenAI API test failed: {e}")
    except AuthenticationError as e:
        st.error(f"Authentication failed: {e}")
    except RateLimitError as e:
        st.error(f"Rate limit exceeded: {e}")
    except OpenAIError as e:
        st.error(f"OpenAI API error: {e}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")
# ----------------------- Session State Management --------------------
def save_session_state():
    """
    Serializes the necessary session state variables into a JSON-compatible dictionary.
    Returns:
        dict: Serialized session state.
    """
    state = {
        'bau_data': st.session_state.get('bau_data').to_json(),
        'emission_factors': st.session_state.get('emission_factors'),
        'scenario_desc_df': st.session_state.get('edited_scenario_desc_df').to_json(),
        'selected_criteria': st.session_state.get('selected_criteria'),
        'edited_criteria_df': st.session_state.get('edited_criteria_df').to_json() if 'edited_criteria_df' in st.session_state else None
    }
    return state

def load_session_state(uploaded_file):
    """
    Deserializes the uploaded JSON file and updates the session state variables.
    Args:
        uploaded_file (BytesIO): Uploaded JSON file.
    """
    try:
        data = json.load(uploaded_file)
        
        # Load BAU Data
        bau_data_loaded = pd.read_json(data['bau_data'])
        # Ensure 'Daily Usage (Units)' is float
        bau_data_loaded['Daily Usage (Units)'] = pd.to_numeric(bau_data_loaded['Daily Usage (Units)'], errors='coerce').fillna(0.0)
        st.session_state.bau_data = bau_data_loaded
        
        # Load Emission Factors
        st.session_state.emission_factors = data['emission_factors']
        
        # Load Scenario Descriptions
        scenario_desc_loaded = pd.read_json(data['scenario_desc_df'])
        st.session_state.edited_scenario_desc_df = scenario_desc_loaded
        
        # Load Selected Criteria
        st.session_state.selected_criteria = data['selected_criteria']
        
        # Load Criteria Values if available
        if data['edited_criteria_df']:
            criteria_values_loaded = pd.read_json(data['edited_criteria_df'])
            # Ensure all numeric criteria are float
            numeric_cols = criteria_values_loaded.columns.drop('Scenario')
            criteria_values_loaded[numeric_cols] = criteria_values_loaded[numeric_cols].apply(pd.to_numeric, errors='coerce').fillna(1.0)
            st.session_state.edited_criteria_df = criteria_values_loaded
        
        st.success("Progress loaded successfully!")
    except Exception as e:
        st.error(f"Failed to load progress: {e}")
# ----------------------- OpenAI Scenario Generation -------------------
def generate_scenarios(description, bau_data, total_daily_bau, total_annual_bau):
    """
    Uses OpenAI's GPT model to generate scenario suggestions. Always generates 5 scenarios.
    We incorporate the BAU data and emissions to provide more context.
    The scenarios should be returned as a list of dicts with 'name' and 'description'.
    """
    
    # Extract items and usage info to provide to the model
    items_info = "\n".join([f"- {row['Item']}: {row['Daily Usage (Units)']} units/day, Emission Factor: {row['Emission Factor (kg CO₂e/unit)']:.4f}, Daily Emissions: {row['Daily Emissions (kg CO₂e)']:.2f}" for _, row in bau_data.iterrows()])
    
    prompt = (
        f"Here is information about the organisation:\n"
        f"Activities description:\n{description}\n\n"
        f"Business As Usual (BAU) data:\n"
        f"Total Daily Emissions (BAU): {total_daily_bau:.2f} kg CO₂e/day\n"
        f"Total Annual Emissions (BAU): {total_annual_bau:.2f} kg CO₂e/year\n"
        f"Items and usage:\n{items_info}\n\n"
        f"Based on the above, suggest 5 different sustainability scenario ideas focused on reducing the carbon footprint.\n"
        f"Do not number them. For each scenario, provide a short, clear title and then a detailed description of what it involves and why it helps reduce carbon emissions.\n"
        f"Format:\n\n"
        f"Title: <Scenario Title>\nDescription: <Detailed scenario description>\n\n"
        f"Title: <Another Scenario Title>\nDescription: <Detailed scenario description>\n\n"
        f"And so on for a total of 5 scenarios."
    )
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert sustainability analyst."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7,
        )
        
        scenarios_text = response.choices[0].message.content.strip().split('\n')
        
        scenarios = []
        current_title = None
        current_desc = []
        
        for line in scenarios_text:
            line_stripped = line.strip()
            if line_stripped.startswith("Title:"):
                # If we already have a current title and description, save it first
                if current_title and current_desc:
                    scenarios.append({"name": current_title, "description": " ".join(current_desc)})
                current_title = line_stripped.replace("Title:", "").strip()
                current_desc = []
            elif line_stripped.startswith("Description:"):
                desc = line_stripped.replace("Description:", "").strip()
                current_desc.append(desc)
            else:
                if current_desc is not None and line_stripped != "":
                    current_desc.append(line_stripped)
        
        # Add the last scenario if there's one pending
        if current_title and current_desc:
            scenarios.append({"name": current_title, "description": " ".join(current_desc)})
        
        return scenarios
    except OpenAIError as e:
        st.error(f"OpenAI API Error: {e}")
        return []
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return []
# ----------------------- Main Application -----------------------
def main():
    # Set page configuration
    st.set_page_config(page_title="Sustainability Decision Assistant", layout="wide")
    
    # Display OpenAI package version using importlib.metadata
    st.sidebar.write("### OpenAI Package Version (importlib.metadata)")
    openai_version = get_openai_version_importlib()
    st.sidebar.write(f"**Installed OpenAI Version:** {openai_version}")

    # Test OpenAI Linkage
    test_openai_linkage()

    # Main Title and Description
    st.title("Sustainability Decision Assistant")
    st.write("*A tool to prioritise scenarios for carbon savings and resource efficiency, enabling data-driven sustainable decisions.*")

    # ----------------------- Save and Load Progress -----------------------
    st.sidebar.header("🔄 Save and Load Progress")
    
    # Save Progress Button
    if st.sidebar.button("Save Progress"):
        session_state_serialized = save_session_state()
        json_data = json.dumps(session_state_serialized, indent=4)
        # Encode the JSON data for download
        b64 = base64.b64encode(json_data.encode()).decode()
        href = f'<a href="data:text/json;base64,{b64}" download="sustainability_progress.json">Download Progress</a>'
        st.sidebar.markdown(href, unsafe_allow_html=True)
        st.sidebar.success("Progress saved! Click the link to download.")
    
    # Load Progress Uploader
    st.sidebar.write("### Load Progress")
    uploaded_file = st.sidebar.file_uploader("Upload your saved progress JSON file:", type=["json"])
    if uploaded_file is not None:
        load_session_state(uploaded_file)

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

    if 'scenario_suggestions_df' not in st.session_state:
        st.session_state.scenario_suggestions_df = pd.DataFrame(columns=["Title", "Description"])

    # ----------------------- BAU Inputs -----------------------
    st.subheader("Enter Daily Usage for Business As Usual (BAU)")
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
            bau_data = pd.concat([bau_data, new_row], ignore_index=True)
            emission_factors[item_name] = emission_factor

    # Fill missing emission factors in the DataFrame
    bau_data["Emission Factor (kg CO₂e/unit)"] = bau_data["Item"].map(emission_factors).fillna(0)

    # Calculate emissions for BAU
    bau_data["Daily Emissions (kg CO₂e)"] = bau_data["Daily Usage (Units)"] * bau_data["Emission Factor (kg CO₂e/unit)"]
    bau_data["Annual Emissions (kg CO₂e)"] = bau_data["Daily Emissions (kg CO₂e)"] * 365

    # Ensure BAU Graph order
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
    bau_data_ordered['Item'] = pd.Categorical(bau_data_ordered['Item'], categories=bau_data_ordered['Item'], ordered=True)

    # BAU summary
    total_daily_bau = bau_data_ordered['Daily Emissions (kg CO₂e)'].sum()
    total_annual_bau = bau_data_ordered['Annual Emissions (kg CO₂e)'].sum()

    st.write("### BAU Results")
    st.write(f"**Total Daily Emissions (BAU):** {total_daily_bau:.2f} kg CO₂e/day")
    st.write(f"**Total Annual Emissions (BAU):** {total_annual_bau:.2f} kg CO₂e/year")

    st.bar_chart(bau_data_ordered.set_index("Item")["Daily Emissions (kg CO₂e)"], use_container_width=True)

    # ----------------------- Describe Activities and Suggest Scenarios -----------------------
    st.subheader("Describe Your Organization's Activities")
    st.write("Provide a brief description of your organization's key activities and sustainability goals to help propose relevant scenarios.")

    activities_description = st.text_area(
        "Describe your organization's key activities and sustainability goals:",
        height=150,
        key="activities_description_input"
    )

    st.subheader("Scenario Suggestions (AI Generated)")
    st.write("Click the button below to get suggestions for scenarios. Each click will produce 5 new suggestions. These are just suggestions and will not be included in calculations.")

    if st.button("Suggest 5 Scenarios"):
        if activities_description.strip() == "":
            st.error("Please provide an activities description first.")
        else:
            with st.spinner("Generating scenario suggestions..."):
                new_scenarios = generate_scenarios(activities_description, bau_data_ordered, total_daily_bau, total_annual_bau)
                if new_scenarios:
                    # Append to existing suggestions
                    new_df = pd.DataFrame(new_scenarios, columns=["name", "description"])
                    new_df.columns = ["Title", "Description"]
                    st.session_state.scenario_suggestions_df = pd.concat([st.session_state.scenario_suggestions_df, new_df], ignore_index=True)
                    st.success("Scenarios suggested successfully!")
                else:
                    st.error("No scenarios were generated. Please try again.")
    
    if not st.session_state.scenario_suggestions_df.empty:
        st.write("### Suggested Scenarios")
        st.dataframe(st.session_state.scenario_suggestions_df)

    # ----------------------- Scenario Planning -----------------------
    st.subheader("Scenario Planning (Editable Table)")
    if activities_description.strip() != "":
        st.success("Activities description received. You can now define your scenarios based on this information.")
    else:
        st.info("Please describe your organization's activities to proceed with scenario planning.")

    num_scenarios = st.number_input(
        "How many scenarios do you want to add?",
        min_value=1,
        step=1,
        value=1,
        key="num_scenarios_input_2"
    )

    scenario_desc_columns = ["Scenario", "Description"]
    scenario_desc_data = [[f"Scenario {i+1}", ""] for i in range(int(num_scenarios))]
    scenario_desc_df = pd.DataFrame(scenario_desc_data, columns=scenario_desc_columns)

    st.write("Please describe each scenario. Double-click a cell to edit the description.")
    try:
        edited_scenario_desc_df = st.data_editor(scenario_desc_df, use_container_width=True, key="scenario_desc_editor")
    except AttributeError:
        edited_scenario_desc_df = st.experimental_data_editor(scenario_desc_df, use_container_width=True, key="scenario_desc_editor")

    st.session_state['edited_scenario_desc_df'] = edited_scenario_desc_df

    scenario_columns = ["Item"] + [f"{row['Scenario']} (%)" for index, row in edited_scenario_desc_df.iterrows()]
    scenario_data = [[item] + [100.0]*int(num_scenarios) for item in bau_data["Item"]]
    scenario_df = pd.DataFrame(scenario_data, columns=scenario_columns)

    st.write("""
        Assign usage percentages to each scenario for each BAU item. These percentages are relative to the BAU.
        - **90%** means using **10% less** of that item compared to BAU.
        - **120%** means using **20% more** of that item compared to BAU.
    """)

    try:
        edited_scenario_df = st.data_editor(scenario_df, use_container_width=True, key="scenario_percent_editor")
    except AttributeError:
        edited_scenario_df = st.experimental_data_editor(scenario_df, use_container_width=True, key="scenario_percent_editor")

    for col in edited_scenario_df.columns[1:]:
        edited_scenario_df[col] = pd.to_numeric(edited_scenario_df[col], errors='coerce').fillna(100.0)

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
            "Scenario": col.replace(" (%)",""), 
            "Total Daily Emissions (kg CO₂e)": scenario_daily_emissions,
            "Total Annual Emissions (kg CO₂e)": scenario_annual_emissions,
            "CO₂ Saving (kg CO₂e/year)": co2_saving_kg,
            "CO₂ Saving (%)": co2_saving_percent
        })

    results_df = pd.DataFrame(results)
    results_df.index = range(1, len(results_df) + 1)

    st.write("### Scenario Results")
    st.dataframe(results_df)

    st.subheader("CO₂ Savings Compared to BAU (%)")
    st.bar_chart(results_df.set_index("Scenario")["CO₂ Saving (%)"], use_container_width=True)

    st.download_button(
        label="Download Scenario Results as CSV",
        data=results_df.to_csv(index=False),
        file_name="scenario_results.csv",
        mime="text/csv"
    )

    # ----------------------- Additional Criteria -----------------------
    st.write("Apart from the environmental impact (e.g., CO₂ saved) calculated above, which of the following criteria are also important to your organisation? Please select all that apply and then assign values for each scenario.")

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
        "Priority for our organisation"

    }

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

    selected_criteria = st.multiselect(
        "Select the criteria you want to consider:",
        list(criteria_options.keys()),
        key="selected_criteria_multiselect"
    )

    if any(crit.startswith("Other -") for crit in selected_criteria):
        other_trend_options = ["Other - Positive Trend", "Other - Negative Trend"]
        selected_other_trends = [crit for crit in selected_criteria if crit in other_trend_options]
        
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
                    criteria_options[other_crit_name.strip()] = other_crit_desc.strip() if other_crit_desc.strip() != "" else "No description provided."

    for crit in selected_criteria:
        st.markdown(f"**{crit}:** {criteria_options[crit]}", unsafe_allow_html=True)

    if selected_criteria:
        st.write("### Assign Criteria Values to Each Scenario")
        st.write("Double-click a cell to edit. For (1-10) criteria, only enter values between 1 and 10.")

        criteria_columns = ["Scenario"] + selected_criteria
        criteria_data = []
        for index, row in edited_scenario_desc_df.iterrows():
            scenario = row["Scenario"]
            criteria_values = [scenario] + [1 for _ in selected_criteria]
            criteria_data.append(criteria_values)
        criteria_df = pd.DataFrame(criteria_data, columns=criteria_columns)

        column_config = {
            "Scenario": st.column_config.TextColumn(
                "Scenario",
                disabled=True
            )
        }

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
            "Priority for our organisation"

        }

        for c in selected_criteria:
            if c in scale_criteria:
                column_config[c] = st.column_config.NumberColumn(
                    label=c,
                    format="%.0f",
                    min_value=1, 
                    max_value=10
                )
            else:
                column_config[c] = st.column_config.NumberColumn(
                    label=c
                )

        try:
            edited_criteria_df = st.data_editor(
                criteria_df,
                use_container_width=True,
                key="criteria_editor_final",
                num_rows="fixed",
                disabled=False,
                column_config=column_config,
                hide_index=True
            )
        except TypeError as e:
            st.error(f"Data Editor Error: {e}")
            st.stop()
        except AttributeError as e:
            edited_criteria_df = st.experimental_data_editor(
                criteria_df,
                use_container_width=True,
                key="criteria_editor_final",
                num_rows="fixed",
                disabled=False
            )

        for col in edited_criteria_df.columns[1:]:
            edited_criteria_df[col] = pd.to_numeric(edited_criteria_df[col], errors='coerce').fillna(1.0)
            if col in scale_criteria:
                edited_criteria_df[col] = edited_criteria_df[col].clip(lower=1.0, upper=10.0)

        st.session_state['edited_criteria_df'] = edited_criteria_df

    if selected_criteria and 'edited_criteria_df' in st.session_state and not st.session_state.edited_criteria_df.empty:
        if st.button("Run Model"):
            if st.session_state.edited_criteria_df.isnull().values.any():
                st.error("Please ensure all criteria values are filled.")
            else:
                scaled_criteria_df = st.session_state.edited_criteria_df.copy()
                criteria_to_normalize = ["Return on Investment (ROI)(years)", "Initial investment (£)", "Other - Positive Trend", "Other - Negative Trend"]

                for crit in criteria_to_normalize:
                    if crit in scaled_criteria_df.columns:
                        try:
                            values = scaled_criteria_df[crit].astype(float).values
                        except:
                            scaled_criteria_df[crit] = 5
                            values = scaled_criteria_df[crit].astype(float).values

                        min_val = np.min(values)
                        max_val = np.max(values)

                        if crit == "Other - Positive Trend":
                            if max_val == min_val:
                                scaled_values = np.ones_like(values)*10 if min_val != 0 else np.zeros_like(values)
                            else:
                                scaled_values = 1 + 9*(values - min_val)/(max_val - min_val)
                            scaled_criteria_df[crit] = scaled_values

                        elif crit == "Other - Negative Trend":
                            if max_val == min_val:
                                scaled_values = np.ones_like(values)*10 if min_val != 0 else np.zeros_like(values)
                            else:
                                scaled_values = 10 - 9*(values - min_val)/(max_val - min_val)
                            scaled_criteria_df[crit] = scaled_values

                        elif crit == "Return on Investment (ROI)(years)":
                            if max_val == min_val:
                                scaled_values = np.ones_like(values)*10 if min_val != 0 else np.zeros_like(values)
                            else:
                                scaled_values = 10 - 9*(values - min_val)/(max_val - min_val)
                            scaled_criteria_df[crit] = scaled_values

                        elif crit == "Initial investment (£)":
                            if max_val == min_val:
                                scaled_values = np.ones_like(values)*10 if min_val != 0 else np.zeros_like(values)
                            else:
                                scaled_values = 10 - 9*(values - min_val)/(max_val - min_val)
                            scaled_criteria_df[crit] = scaled_values

                scaled_criteria_df['Total Score'] = scaled_criteria_df[selected_criteria].sum(axis=1)
                min_score = scaled_criteria_df['Total Score'].min()
                max_score = scaled_criteria_df['Total Score'].max()
                if max_score != min_score:
                    scaled_criteria_df['Normalized Score'] = 1 + 9*(scaled_criteria_df['Total Score'] - min_score)/(max_score - min_score)
                else:
                    scaled_criteria_df['Normalized Score'] = 5

                def get_color(score):
                    if score >= 7:
                        return 'green'
                    elif score >= 5:
                        return 'yellow'
                    else:
                        return 'red'

                scaled_criteria_df['Color'] = scaled_criteria_df['Normalized Score'].apply(get_color)
                scaled_criteria_df['Rank'] = scaled_criteria_df['Normalized Score'].rank(method='min', ascending=False).astype(int)

                st.write("### Normalized Results (All Criteria Scaled 1-10)")
                st.dataframe(scaled_criteria_df.round(2))

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

                styled_display = scaled_criteria_df[['Scenario', 'Normalized Score', 'Rank']].copy()
                styled_display = styled_display.sort_values('Rank')

                def color_cell(score):
                    if score >= 7:
                        return 'background-color: green'
                    elif score >= 5:
                        return 'background-color: yellow'
                    else:
                        return 'background-color: red'

                styled_display_style = styled_display.style.applymap(color_cell, subset=['Normalized Score'])
                st.write("### Ranked Scenarios with Gradient Colors")
                st.dataframe(styled_display_style)

                top_scenario = scaled_criteria_df.loc[scaled_criteria_df['Rank'] == 1, 'Scenario'].values
                if len(top_scenario) > 0:
                    st.success(f"The top-ranked scenario is **{top_scenario[0]}** with the highest carbon savings.")

if __name__ == "__main__":
    main()
