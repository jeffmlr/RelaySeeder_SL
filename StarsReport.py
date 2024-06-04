import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from ortools.sat.python import cp_model

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
    # Include times for the selected event and swimmer information
    plt.figure(figsize=(12, 6))
    event_data = data[['AgeGroup', 'FirstName', 'LastName', event_name]].dropna()
    event_data['Swimmer'] = event_data['FirstName'] + ' ' + event_data['LastName'] + ' (' + event_data['AgeGroup'] + ')'
    event_data = event_data.sort_values(by=event_name)  # Sort by the selected event times
    plt.title(f'Best Times for {event_name}')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Swimmer')
    # Add data points on each bar
    plt.bar_label(plt.barh(event_data['Swimmer'], event_data[event_name]))
    sns.barplot(x=event_name, y='Swimmer', data=event_data, palette='viridis')
    st.pyplot(plt)
    plt.clf()

# Function to create freestyle relays
def create_freestyle_relays(data, event_name):
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

# Function to create medley relays using OR-Tools
def create_medley_relays(data):
    relays = {}
    age_groups = data['AgeGroup'].unique()
    st.write("Detected Age Groups: ", age_groups)  # Debugging line to print detected age groups
    strokes = {
        'Boys 7-8': ['25 Butterfly', '25 Backstroke', '25 Breaststroke', '25 Freestyle'],
        'Boys 9-10': ['25 Butterfly', '25 Backstroke', '25 Breaststroke', '25 Freestyle'],
        'Boys 11-12': ['25 Butterfly', '25 Backstroke', '25 Breaststroke', '25 Freestyle'],
        'Boys 13-14': ['50 Butterfly', '50 Backstroke', '50 Breaststroke', '50 Freestyle'],
        'Men 15-18': ['50 Butterfly', '50 Backstroke', '50 Breaststroke', '50 Freestyle'],
        'Girls 7-8': ['25 Butterfly', '25 Backstroke', '25 Breaststroke', '25 Freestyle'],
        'Girls 9-10': ['25 Butterfly', '25 Backstroke', '25 Breaststroke', '25 Freestyle'],
        'Girls 11-12': ['25 Butterfly', '25 Backstroke', '25 Breaststroke', '25 Freestyle'],
        'Girls 13-14': ['50 Butterfly', '50 Backstroke', '50 Breaststroke', '50 Freestyle'],
        'Women 15-18': ['50 Butterfly', '50 Backstroke', '50 Breaststroke', '50 Freestyle'],
    }

    for age_group in age_groups:
        if age_group not in strokes:
            st.write(f"Skipping age group {age_group} because it is not in the specified stroke categories.")
            continue
        
        group_data = data[data['AgeGroup'] == age_group]
        group_data = group_data[(group_data['Roster_Status'] == 'Checked-in') & 
                                (~group_data['InternalNotes'].isin(['No Relays']))]
        
        if group_data.empty:
            st.write(f"No eligible swimmers for age group {age_group}.")
            continue

        #st.write(f"Eligible swimmers for age group {age_group}:")
        #st.write(group_data)  # Debugging line to print the eligible swimmers for the age group

        events = strokes[age_group]

        # Replace NaN with 99999 for events
        for event in events:
            group_data[event].fillna(99999, inplace=True)

        st.write(f"Swimmers with valid times for age group {age_group}:")
        st.write(group_data)  # Debugging line to print the swimmers with valid times for the age group
        
        if len(group_data) < 4:
            st.write(f"Not enough swimmers with valid times for age group {age_group}.")
            continue
        
        # Determine the maximum number of relays that can be created
        max_relays = len(group_data) // 4
        st.write(f"Maximum number of relays for age group {age_group}: {max_relays}")

        num_relay_legs = 4

        for r in range(1, max_relays + 1):
            # Create the model
            model = cp_model.CpModel()

            # Create or reset the variables
            num_swimmers = len(group_data)

            x = []
            for i in range(num_swimmers):
                t = []
                for j in range(num_relay_legs):
                    t.append(model.NewBoolVar(f'x_{i}_{j}'))
                x.append(t)

            # Create the constraints
            for i in range(num_swimmers):
                model.AddAtMostOne(x[i][j] for j in range(num_relay_legs))

            for j in range(num_relay_legs):
                model.AddExactlyOne(x[i][j] for i in range(num_swimmers))

            for i in range(num_swimmers):
                for j in range(4):
                    if group_data.iloc[i][events[j]] == 99999:
                        model.Add(x[i][j] == 0)

            objective_terms = []
            for i in range(num_swimmers):
                for j in range(num_relay_legs):
                    objective_terms.append(x[i][j] * group_data.iloc[i][events[j]])
            model.Minimize(sum(objective_terms))

            solver = cp_model.CpSolver()
            status = solver.Solve(model)

            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                # st.write(f"Optimal solution found for age group {age_group} and relay {r}.")
                # Print the total time in MM:SS format

                # Write the relay number and total time to the streamlit app formatted as a header to a table
                st.markdown(f"#### Relay {r} for age group {age_group}:")
                st.markdown(f"##### Total time for relay {r}: {solver.ObjectiveValue():.2f} seconds")

                # st.write(f"Relay {r} for age group {age_group}:")
                # st.write(f"Total time for relay {r}: {solver.ObjectiveValue():.2f} seconds")

                relay_swimmers = []
                relay_table = pd.DataFrame(columns=['Swimmer', 'Stroke', 'Time', 'Position'])

                for i in range(num_swimmers):
                    for j in range(num_relay_legs):
                        if solver.BooleanValue(x[i][j]):
                            relay_swimmers.append(group_data.index[i])
                            
                            if j == 0:
                                stroke = "Backstroke"
                            elif j == 1:
                                stroke = "Breaststroke"
                            elif j == 2:
                                stroke = "Butterfly"
                            elif j == 3:
                                stroke = "Freestyle"

                            # Add the swimmer to the relay table dataframe (do not use append)
                            relay_table.loc[len(relay_table)] = [f"{group_data.iloc[i]['FirstName']} {group_data.iloc[i]['LastName']}",
                                                                stroke, group_data.iloc[i][events[j]], f"{j}"]

                # Write the relay swimmers to a table

                # Sort the relay table by position
                relay_table = relay_table.sort_values(by=['Position'])

                # Write the relaty table to the streamlit app (but do not render the index or the position)
                relay_table_html = relay_table.to_html(index=False)
                st.write(relay_table_html, unsafe_allow_html=True)

                # Remove assigned swimmers from the group_data
                group_data = group_data.drop(relay_swimmers)

    return relays

# Streamlit app
def main():
    st.title("Steiner Stars Relay Seeder")

    st.markdown("""
    ### Upload Files
    Please upload the best times data and roster data files in CSV format.
    """)

    # File upload for swim team data
    swim_file = st.file_uploader("Choose a CSV file with best times data", type="csv")
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
                        relays = create_freestyle_relays(edited_data, event_name)
                        for age_group, relay_teams in relays.items():
                            st.markdown(f"#### {age_group} Freestyle Relays")
                            for idx, relay in enumerate(relay_teams, start=1):
                                st.markdown(f"**Relay {idx}**")
                                relay_html = relay.to_html(index=False, justify="left", border=0)
                                st.markdown(relay_html, unsafe_allow_html=True)

                    # Create Medley Relays Button
                    if st.button("Create Medley Relays"):
                        st.write("Medley Relays Button Clicked")
                        relays = create_medley_relays(edited_data)
                        if not relays:
                            st.write("No medley relays could be created.")
                        for age_group, relay_teams in relays.items():
                            st.markdown(f"#### {age_group} Medley Relays")
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
