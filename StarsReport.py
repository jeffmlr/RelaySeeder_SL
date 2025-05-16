import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from ortools.sat.python import cp_model

# Required packages: streamlit, pandas, seaborn, matplotlib, ortools

# Helper functions
def convert_time_to_numeric(time_str):
    if pd.isna(time_str):
        return None
    time_str = time_str.rstrip('Y')
    if ':' in time_str:
        minutes, seconds = map(float, time_str.split(':'))
        return minutes * 60 + seconds
    else:
        return float(time_str)

def estimate_50_time_from_25_with_flag(time_25):
    if pd.isna(time_25) or time_25 <= 0:
        return None, False
    return round(2 * time_25 + 2, 2), True

def fill_missing_50_times_with_flag(df):
    # Create age group filters
    age_filters = {
        '11-12': df['AgeGroup'].str.contains('11-12', case=False, na=False),
        '13-14': df['AgeGroup'].str.contains('13-14', case=False, na=False),
        '15-18': df['AgeGroup'].str.contains('15-18', case=False, na=False)
    }

    event_pairs = [
        ('25 Freestyle', '50 Freestyle'),
        ('25 Backstroke', '50 Backstroke'),
        ('25 Breaststroke', '50 Breaststroke'),
        ('25 Butterfly', '50 Butterfly')
    ]

    # Initialize estimation flags for all 50-yard events
    for _, long_event in event_pairs:
        df[f"{long_event} Estimated"] = False

    # Process each age group
    for age_group, age_filter in age_filters.items():
        for short_event, long_event in event_pairs:
            estimate_mask = age_filter & df[long_event].isna() & df[short_event].notna()
            estimated_values = df.loc[estimate_mask, short_event].apply(estimate_50_time_from_25_with_flag)

            df.loc[estimate_mask, long_event] = estimated_values.apply(lambda x: x[0])
            df.loc[estimate_mask, f"{long_event} Estimated"] = estimated_values.apply(lambda x: x[1])

    return df

@st.cache_data
def load_swim_data(file_path):
    swim_team_data = pd.read_csv(file_path)
    best_times = swim_team_data.loc[swim_team_data.groupby(['AgeGroup', 'FirstName', 'LastName', 'Event'])['ConvertedHundredths'].idxmin()]
    best_times_pivot = best_times.pivot_table(index=['AgeGroup', 'FirstName', 'LastName'],
                                              columns='Event',
                                              values='Time',
                                              aggfunc='first').reset_index()
    return best_times_pivot

@st.cache_data
def load_roster_data(file_path):
    return pd.read_csv(file_path)

def plot_best_times(data, event_name):
    plt.figure(figsize=(12, 6))
    event_data = data[['AgeGroup', 'FirstName', 'LastName', event_name]].dropna()
    event_data['Swimmer'] = event_data['FirstName'] + ' ' + event_data['LastName'] + ' (' + event_data['AgeGroup'] + ')'
    event_data = event_data.sort_values(by=event_name)
    plt.title(f'Best Times for {event_name}')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Swimmer')
    plt.bar_label(plt.barh(event_data['Swimmer'], event_data[event_name]))
    sns.barplot(x=event_name, y='Swimmer', data=event_data, palette='viridis')
    st.pyplot(plt)
    plt.clf()

def create_medley_relays(data):
    relays = {}
    age_groups = data['AgeGroup'].unique()
    strokes = {
        'Boys 7-8': ['25 Backstroke', '25 Breaststroke', '25 Butterfly', '25 Freestyle'],
        'Boys 9-10': ['25 Backstroke', '25 Breaststroke', '25 Butterfly', '25 Freestyle'],
        'Boys 11-12': ['50 Backstroke', '50 Breaststroke', '50 Butterfly', '50 Freestyle'],
        'Boys 13-14': ['50 Backstroke', '50 Breaststroke', '50 Butterfly', '50 Freestyle'],
        'Men 15-18': ['50 Backstroke', '50 Breaststroke', '50 Butterfly', '50 Freestyle'],
        'Girls 7-8': ['25 Backstroke', '25 Breaststroke', '25 Butterfly', '25 Freestyle'],
        'Girls 9-10': ['25 Backstroke', '25 Breaststroke', '25 Butterfly', '25 Freestyle'],
        'Girls 11-12': ['50 Backstroke', '50 Breaststroke', '50 Butterfly', '50 Freestyle'],
        'Girls 13-14': ['50 Backstroke', '50 Breaststroke', '50 Butterfly', '50 Freestyle'],
        'Women 15-18': ['50 Backstroke', '50 Breaststroke', '50 Butterfly', '50 Freestyle'],
    }

    for age_group in age_groups:
        if age_group not in strokes:
            continue
        group_data = data[data['AgeGroup'] == age_group].copy()  # Make a copy to avoid modifying the original
        group_data = group_data[(group_data['Roster_Status'] == 'Checked-in') &
                                (~group_data['InternalNotes'].isin(['No Relays', 'No Early Relays']))]
        if group_data.empty or len(group_data) < 4:
            continue
        events = strokes[age_group]
        for event in events:
            group_data[event].fillna(99999, inplace=True)
        max_relays = len(group_data) // 4
        num_relay_legs = 4
        for r in range(1, max_relays + 1):
            if len(group_data) < 4:  # Check if we have enough swimmers left
                break
                
            model = cp_model.CpModel()
            num_swimmers = len(group_data)
            x = [[model.NewBoolVar(f'x_{i}_{j}') for j in range(num_relay_legs)] for i in range(num_swimmers)]
            for i in range(num_swimmers):
                model.AddAtMostOne(x[i][j] for j in range(num_relay_legs))
            for j in range(num_relay_legs):
                model.AddExactlyOne(x[i][j] for i in range(num_swimmers))
            for i in range(num_swimmers):
                for j in range(4):
                    if group_data.iloc[i][events[j]] == 99999:
                        model.Add(x[i][j] == 0)
            objective_terms = [x[i][j] * group_data.iloc[i][events[j]] for i in range(num_swimmers) for j in range(num_relay_legs)]
            model.Minimize(sum(objective_terms))
            solver = cp_model.CpSolver()
            status = solver.Solve(model)
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                st.markdown(f"#### Relay {r} for age group {age_group}")
                st.markdown(f"##### Total time: {solver.ObjectiveValue():.2f} seconds")
                relay_table = pd.DataFrame(columns=['Swimmer', 'Stroke', 'Time', 'Estimated', 'Position'])
                selected_swimmers = []  # Keep track of selected swimmers
                
                for i in range(num_swimmers):
                    for j in range(num_relay_legs):
                        if solver.BooleanValue(x[i][j]):
                            stroke = ['Backstroke', 'Breaststroke', 'Butterfly', 'Freestyle'][j]
                            est_flag_col = f"{events[j]} Estimated"
                            is_estimated = group_data.iloc[i][est_flag_col] if est_flag_col in group_data.columns else False
                            relay_table.loc[len(relay_table)] = [
                                f"{group_data.iloc[i]['FirstName']} {group_data.iloc[i]['LastName']}",
                                stroke,
                                group_data.iloc[i][events[j]],
                                "✅" if is_estimated else "",
                                f"{j}"
                            ]
                            selected_swimmers.append(i)  # Add selected swimmer index
                
                relay_table = relay_table.sort_values(by=['Position'])
                st.write(relay_table.drop(columns=["Position"]))
                
                # Remove selected swimmers from group_data
                group_data = group_data.drop(group_data.index[selected_swimmers])

    return relays

def main():
    st.title("Steiner Stars Relay Seeder")
    swim_file = st.file_uploader("Choose a CSV file with best times data", type="csv")
    roster_file = st.file_uploader("Choose a CSV file with roster data", type="csv")

    if swim_file is not None and roster_file is not None:
        best_times_pivot = load_swim_data(swim_file)
        roster_data = load_roster_data(roster_file)

        roster_data.rename(columns={'AthleteFirstName': 'FirstName', 'AthleteLastName': 'LastName'}, inplace=True)

        best_times_pivot['FirstName'] = best_times_pivot['FirstName'].str.title()
        best_times_pivot['LastName'] = best_times_pivot['LastName'].str.title()
        roster_data['FirstName'] = roster_data['FirstName'].str.title()
        roster_data['LastName'] = roster_data['LastName'].str.title()

        merged_data = pd.merge(best_times_pivot, roster_data, on=['FirstName', 'LastName'], how='inner')
        if 'AgeGroup_x' in merged_data.columns:
            merged_data.rename(columns={'AgeGroup_y': 'AgeGroup'}, inplace=True)

        events = ['25 Freestyle', '50 Freestyle', '100 Freestyle', '25 Backstroke', '50 Backstroke',
                  '25 Breaststroke', '50 Breaststroke', '25 Butterfly', '50 Butterfly', '100 Individual Medley']
        best_times_pivot_clean = merged_data.copy()
        for event in events:
            best_times_pivot_clean[event] = best_times_pivot_clean[event].apply(convert_time_to_numeric)

        best_times_pivot_clean = fill_missing_50_times_with_flag(best_times_pivot_clean)

        if 'AgeGroup' in best_times_pivot_clean.columns:
            age_groups = best_times_pivot_clean['AgeGroup'].unique()
            selected_age_group = st.selectbox("Select Age Group", age_groups)
            filtered_data = best_times_pivot_clean[best_times_pivot_clean['AgeGroup'] == selected_age_group]

            if 'InternalNotes' in filtered_data.columns and 'Roster_Status' in filtered_data.columns:
                filtered_data['InternalNotes'].fillna('No Restrictions', inplace=True)
                internal_notes = filtered_data['InternalNotes'].unique()
                selected_internal_notes = st.multiselect("Select Internal Notes", internal_notes, default=internal_notes)
                filtered_data = filtered_data[filtered_data['InternalNotes'].isin(selected_internal_notes)]
                roster_statuses = filtered_data['Roster_Status'].unique()
                selected_roster_status = st.selectbox("Select Roster Status", roster_statuses)
                filtered_data = filtered_data[filtered_data['Roster_Status'] == selected_roster_status]
                edited_data = st.data_editor(filtered_data, num_rows="dynamic")
                event_name = st.selectbox("Select Event", events)
                plot_best_times(edited_data, event_name)

                if st.button("Create Medley Relays"):
                    relays = create_medley_relays(edited_data)
                    if not relays:
                        st.write("No medley relays could be created.")
        else:
            st.error("Missing 'AgeGroup' in merged data.")

if __name__ == "__main__":
    main()
