import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Function to load and preprocess swim team data
@st.cache_data
def load_swim_data(file_path):
    swim_team_data = pd.read_csv(file_path)
    best_times = swim_team_data.loc[swim_team_data.groupby(['AgeGroup', 'FirstName', 'LastName', 'Event'])['ConvertedHundredths'].idxmin()]
    best_times_pivot = best_times.pivot_table(index=['AgeGroup', 'FirstName', 'LastName'],
                                              columns='Event',
                                              values='Time',
                                              aggfunc='first').reset_index()
    return best_times_pivot

# Function to load and preprocess roster data
@st.cache_data
def load_roster_data(file_path):
    return pd.read_csv(file_path)

# Function to convert time strings to numeric
def convert_time_to_numeric(time_str):
    if pd.isna(time_str):
        return None
    time_str = time_str.rstrip('Y')
    if ':' in time_str:
        minutes, seconds = map(float, time_str.split(':'))
        return minutes * 60 + seconds
    else:
        return float(time_str)

# Function to create bar plots for each event
def plot_best_times(data, event_name):
    plt.figure(figsize=(12, 6))
    event_data = data[['AgeGroup', 'FirstName', 'LastName', event_name]].dropna()
    event_data['Swimmer'] = event_data['FirstName'] + ' ' + event_data['LastName'] + ' (' + event_data['AgeGroup'] + ')'
    event_data = event_data.sort_values(by=event_name)  # Sort by the selected event times
    sns.barplot(x=event_name, y='Swimmer', data=event_data, palette='viridis')
    plt.title(f'Best Times for {event_name}')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Swimmer')
    st.pyplot(plt)
    plt.clf()

# Function to create relays
def create_relays(data, event_name):
    relays = {}
    age_groups = data['AgeGroup'].unique()
    for age_group in age_groups:
        group_data = data[data['AgeGroup'] == age_group].dropna(subset=[event_name])
        group_data = group_data[(group_data['Roster_Status'] == 'Checked-in') & 
                                (~group_data['InternalNotes'].isin(['No Relays', 'No Late Relays']))]
        if not group_data.empty:
            group_data = group_data.sort_values(by=event_name)
            relays[age_group] = []
            for i in range(0, len(group_data), 4):
                relay = group_data.iloc[i:i+4]
                if len(relay) == 4:
                    # Assign swimmers to positions in the relay
                    relay_order = [relay.iloc[1], relay.iloc[2], relay.iloc[3], relay.iloc[0]]
                    relay_positions = ['First', 'Second', 'Third', 'Fourth']
                    relay_df = pd.DataFrame({
                        'Position': relay_positions,
                        'Swimmer': [f"{row['FirstName']} {row['LastName']}" for row in relay_order],
                        'Time': [row[event_name] for row in relay_order]
                    })
                    relays[age_group].append(relay_df)
    return relays

# Streamlit app
def main():
    st.title("Swim Team Best Times")

    st.markdown("""
    ### Upload Files
    Please upload the swim team data and roster data files in CSV format.
    """)

    # File upload for swim team data
    swim_file = st.file_uploader("Choose a CSV file with swim team data", type="csv")
    # File upload for roster data
    roster_file = st.file_uploader("Choose a CSV file with roster data", type="csv")
    
    if swim_file is not None and roster_file is not None:
        best_times_pivot = load_swim_data(swim_file)
        roster_data = load_roster_data(roster_file)

        # Rename roster columns to match swim team data for merging
        roster_data.rename(columns={'AthleteFirstName': 'FirstName', 'AthleteLastName': 'LastName'}, inplace=True)

        # Ensure the columns exist before merging
        if 'FirstName' in best_times_pivot.columns and 'LastName' in best_times_pivot.columns \
           and 'FirstName' in roster_data.columns and 'LastName' in roster_data.columns:
            merged_data = pd.merge(best_times_pivot, roster_data, on=['FirstName', 'LastName'], how='inner')
            
            # Rename columns to handle '_x' and '_y' suffixes
            if 'AgeGroup_x' in merged_data.columns:
                merged_data.rename(columns={'AgeGroup_x': 'AgeGroup'}, inplace=True)
            
            # Preprocess the times
            events = ['25 Freestyle', '50 Freestyle', '100 Freestyle', '25 Backstroke', '50 Backstroke', 
                      '25 Breaststroke', '50 Breaststroke', '25 Butterfly', '50 Butterfly', '100 Individual Medley']
            best_times_pivot_clean = merged_data.copy()
            for event in events:
                best_times_pivot_clean[event] = best_times_pivot_clean[event].apply(convert_time_to_numeric)

            # Select age group
            if 'AgeGroup' in best_times_pivot_clean.columns:
                age_groups = best_times_pivot_clean['AgeGroup'].unique()
                selected_age_group = st.selectbox("Select Age Group", age_groups)
                filtered_data = best_times_pivot_clean[best_times_pivot_clean['AgeGroup'] == selected_age_group]

                # Check if InternalNotes and Roster_Status columns exist
                if 'InternalNotes' in filtered_data.columns and 'Roster_Status' in filtered_data.columns:
                    # Replace NaN in InternalNotes with 'No Restrictions'
                    filtered_data['InternalNotes'].fillna('No Restrictions', inplace=True)
                    
                    st.markdown("### Filter Internal Notes and Roster Status")

                    # Multi-select for InternalNotes
                    internal_notes = filtered_data['InternalNotes'].unique()
                    selected_internal_notes = st.multiselect("Select Internal Notes", internal_notes, default=internal_notes)
                    filtered_data = filtered_data[filtered_data['InternalNotes'].isin(selected_internal_notes)]

                    # Select for Roster_Status
                    roster_statuses = filtered_data['Roster_Status'].unique()
                    selected_roster_status = st.selectbox("Select Roster Status", roster_statuses)
                    filtered_data = filtered_data[filtered_data['Roster_Status'] == selected_roster_status]

                    st.markdown("### Edit Internal Notes and Roster Status")

                    # Editable table
                    edited_data = st.data_editor(filtered_data, num_rows="dynamic")

                    # Select event
                    event_name = st.selectbox("Select Event", events)
                    plot_best_times(edited_data, event_name)

                    # Create Free Relays Button
                    if st.button("Create Free Relays"):
                        relays = create_relays(edited_data, event_name)
                        for age_group, relay_teams in relays.items():
                            st.markdown(f"#### {age_group} Relays")
                            for idx, relay in enumerate(relay_teams, start=1):
                                st.markdown(f"**Relay {idx}**")
                                relay_html = relay.to_html(index=False, justify="left", border=0)
                                st.markdown(relay_html, unsafe_allow_html=True)
                else:
                    st.error("The required columns 'InternalNotes' and/or 'Roster_Status' are not present in the merged data.")
            else:
                st.error("The required column 'AgeGroup' is not present in the merged data.")
        else:
            st.error("The required columns 'FirstName' and 'LastName' are not present in one or both of the uploaded files.")

if __name__ == "__main__":
    main()
