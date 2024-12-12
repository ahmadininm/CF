# Initialize other_name and other_scale to avoid NameError if "Other" not selected
other_name = ""
other_scale = ""

# Ask about additional criteria
st.write("Apart from the environmental impact (e.g., CO₂ saved) calculated above, which of the following criteria are also important to your organisation? Please select all that apply and then assign values for each scenario.")

# Criteria options with brief, colour-coded descriptions for the 1-10 scale criteria
criteria_options = {
    "Technical Feasibility": "<span style='color:red;'>1-4: low feasibility</span>, <span style='color:orange;'>5-6: moderate</span>, <span style='color:green;'>7-10: high feasibility</span>",
    "Supplier Reliability and Technology Readiness": "<span style='color:red;'>1-4: unreliable/immature</span>, <span style='color:orange;'>5-6: mostly reliable</span>, <span style='color:green;'>7-10: fully reliable & proven</span>",
    "Implementation Complexity": "<span style='color:red;'>1-4: very complex</span>, <span style='color:orange;'>5-6: moderate complexity</span>, <span style='color:green;'>7-10: easy to implement</span>",
    "Scalability": "<span style='color:red;'>1-4: hard to scale</span>, <span style='color:orange;'>5-6: moderate</span>, <span style='color:green;'>7-10: easy to scale</span>",
    "Maintenance Requirements": "<span style='color:red;'>1-4: high maintenance</span>, <span style='color:orange;'>5-6: moderate</span>, <span style='color:green;'>7-10: low maintenance</span>",
    "Regulatory Compliance": "<span style='color:red;'>1-4: risk of non-compliance</span>, <span style='color:orange;'>5-6: mostly compliant</span>, <span style='color:green;'>7-10: fully compliant or beyond</span>",
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

# Use session_state to store and persist criteria data
if "criteria_data" not in st.session_state:
    st.session_state["criteria_data"] = pd.DataFrame()
if "prev_selected_criteria" not in st.session_state:
    st.session_state["prev_selected_criteria"] = []

if selected_criteria:
    scenario_names = results_df["Scenario"].tolist()

    # If selected_criteria changed, adjust the structure of criteria_data
    if set(selected_criteria) != set(st.session_state["prev_selected_criteria"]):
        # Start from existing data
        criteria_df = st.session_state["criteria_data"].copy()
        if criteria_df.empty:
            # Create new DataFrame if empty
            criteria_df = pd.DataFrame({"Scenario": scenario_names})
        else:
            # If scenario count changed or data empty, ensure Scenario column matches scenario_names
            if list(criteria_df["Scenario"]) != scenario_names:
                # Recreate scenario column if needed
                criteria_df = pd.DataFrame({"Scenario": scenario_names})
        
        # Add missing criteria columns with 0 default
        for c in selected_criteria:
            if c not in criteria_df.columns:
                criteria_df[c] = 0
        
        # Remove columns no longer selected
        for c in criteria_df.columns:
            if c != "Scenario" and c not in selected_criteria:
                criteria_df.drop(columns=c, inplace=True)
        
        # Update session state
        st.session_state["criteria_data"] = criteria_df.copy()
        st.session_state["prev_selected_criteria"] = selected_criteria.copy()
    else:
        # No change in criteria selection, just use existing data
        criteria_df = st.session_state["criteria_data"].copy()

    criteria_df.index = range(1, len(criteria_df) + 1)  # Start indexing from 1

    st.write("Please assign values for each selected criterion to each scenario. Double-click a cell to edit. For (1-10) criteria, only enter values between 1 and 10.")

    # Determine which criteria are scale-based (1-10) and which are free input
    scale_criteria = {
        "Technical Feasibility", "Supplier Reliability and Technology Readiness", "Implementation Complexity",
        "Scalability", "Maintenance Requirements", "Regulatory Compliance", "Risk for Workforce Safety",
        "Risk for Operations", "Impact on Product Quality", "Customer and Stakeholder Alignment",
        "Priority for our organisation"
    }

    # Also consider the "Other" criterion if added as scale-based
    if other_name.strip() and other_name.strip() in selected_criteria and other_scale == "Yes":
        scale_criteria.add(other_name.strip())

    # Create column configs
    column_config = {}
    column_config["Scenario"] = st.column_config.TextColumn("Scenario", disabled=True)
    for crit in selected_criteria:
        if crit in scale_criteria:
            # Numeric column with 1-10 limits (no step, to reduce editing issues)
            column_config[crit] = st.column_config.NumberColumn(label=crit, min_value=1, max_value=10)
        elif crit in ["Initial investment (£)", "Return on Investment (ROI)(years)"]:
            # Numeric column with no strict limit
            column_config[crit] = st.column_config.NumberColumn(label=crit)
        else:
            # Other criterion might not have a scale, assume free numeric input
            column_config[crit] = st.column_config.NumberColumn(label=crit)

    try:
        edited_criteria_df = st.data_editor(criteria_df, use_container_width=True, column_config=column_config, key="criteria_editor")
    except AttributeError:
        edited_criteria_df = st.experimental_data_editor(criteria_df, use_container_width=True)

    # Store updated criteria data immediately to ensure user input persistence
    st.session_state["criteria_data"] = edited_criteria_df.copy()

else:
    # If no criteria selected, reset criteria_data
    st.session_state["criteria_data"] = pd.DataFrame()
    st.session_state["prev_selected_criteria"] = []

# Now proceed with scaling only if we have criteria and data
if selected_criteria and 'edited_criteria_df' in locals() and edited_criteria_df is not None and not edited_criteria_df.empty:
    scaled_criteria_df = edited_criteria_df.copy()

    inversion_criteria = []
    if "Return on Investment (ROI)(years)" in selected_criteria:
        inversion_criteria.append("Return on Investment (ROI)(years)")
    if "Initial investment (£)" in selected_criteria:
        inversion_criteria.append("Initial investment (£)")

    if other_name.strip():
        if other_scale == "No":
            inversion_criteria.append(other_name.strip())
        else:
            scale_criteria.add(other_name.strip())

    for crit in selected_criteria:
        values = scaled_criteria_df[crit].values.astype(float)
        min_val = np.min(values)
        max_val = np.max(values)

        if crit in scale_criteria:
            # Already 1-10 scale, do nothing
            pass
        elif crit in inversion_criteria:
            # Invert scale: lower value -> 10, higher value -> 1
            if max_val == min_val:
                scaled_values = np.ones_like(values) * 10
            else:
                scaled_values = 10 - 9 * (values - min_val) / (max_val - min_val)
            scaled_criteria_df[crit] = scaled_values
        else:
            # Scale min to 1, max to 10 (higher is better)
            if max_val == min_val:
                scaled_values = np.ones_like(values) * 10
            else:
                scaled_values = 1 + 9 * (values - min_val) / (max_val - min_val)
            scaled_criteria_df[crit] = scaled_values

    st.write("### Normalised Results (All Criteria Scaled 1-10)")
    st.dataframe(scaled_criteria_df)
else:
    st.write("No criteria selected or no data available to scale.")
