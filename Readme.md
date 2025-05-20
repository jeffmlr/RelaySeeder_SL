# Steiner Stars Relay Seeder

A Streamlit web application designed to streamline the generation of optimized medley relay teams for youth swim meets. The app processes swimmer times and roster data to assist coaches in identifying the best relay combinations for each age group using constraint programming.

---

## 🚀 Features

- Upload and merge best times and roster CSV files.
- Estimate missing 50-yard event times from 25-yard performances.
- Visualize best times for individual events with interactive charts.
- Filter swimmers by age group, internal notes, and roster status.
- Automatically generate optimized medley relays using Google's OR-Tools.
- Relay swimmer selections include estimated time flags and stroke breakdowns.

---

## 🛠️ Technologies Used

- [Streamlit](https://streamlit.io/) – UI framework for Python.
- [Pandas](https://pandas.pydata.org/) – Data manipulation and analysis.
- [Seaborn](https://seaborn.pydata.org/) – Statistical data visualization.
- [Matplotlib](https://matplotlib.org/) – Plotting library for Python.
- [OR-Tools (Google)](https://developers.google.com/optimization) – Solver for optimal relay assignment.

---

## 📦 Installation

### Prerequisites

Make sure you have Python 3.8+ installed. Then install the required packages:

```bash
pip install -r requirements.txt
```

### Running the App

Clone this repository and run:

```bash
streamlit run app.py
```

> Replace `app.py` with the name of your main script file if different.

---

## 📂 File Requirements

### Best Times CSV

Expected columns:
- `FirstName`, `LastName`, `AgeGroup`, `Event`, `Time`, `ConvertedHundredths`

> Each swimmer's best times should be included per event. The app will pivot and aggregate based on the fastest converted time.

### Roster CSV

Expected columns:
- `AthleteFirstName`, `AthleteLastName`, `AgeGroup`, `Roster_Status`, `InternalNotes`

> Used to determine swimmer eligibility and filter relay candidates.

---

## ⚙️ How It Works

1. **Upload Files** – Choose the Best Times and Roster CSVs.
2. **Data Cleaning** – Merges, normalizes names, and converts time formats.
3. **Estimation Logic** – Fills missing 50-yard times from 25-yard equivalents where applicable.
4. **Filtering Interface** – Choose age group, internal notes, and roster status.
5. **Relay Generation** – Solves a constraint programming model to minimize total relay time.
6. **Output** – Displays optimal swimmer-stroke combinations and marks estimated times.

---

## 📊 Example Output

- Interactive swimmer bar chart sorted by time.
- Table of swimmers selected per relay with stroke, time, and estimation flag.

---

## 🧠 Behind the Scenes

The medley relay generation uses:
- **Boolean decision variables** for swimmer-stroke assignments.
- **Constraints** ensuring each stroke is swum exactly once and no swimmer appears more than once per relay.
- **Objective function** minimizing total relay time using available swimmer data.

## 🔍 Medley Relay Optimizer Details

The optimizer follows these key rules and constraints:

### Swimmer Eligibility
- Only swimmers with a "Checked-in" roster status are considered for relay selection
- Swimmers must have valid times for their assigned stroke, or have a basis for estimation (25yd if they are 11+ to estimate 50yd)
- No restrictions on early relay participation (swimmers can be assigned to multiple relays)

### Stroke Order
- Medley relays follow the standard order: Backstroke → Breaststroke → Butterfly → Freestyle
- Each swimmer can only be assigned to one stroke per relay
- Each stroke must be assigned exactly once per relay

### Time Handling
- Uses actual times when available
- Automatically estimates missing 50-yard times from 25-yard performances
- Estimated times are clearly marked in the output
- All times are converted to a common format for comparison

### Optimization Goals
- Minimizes total relay time while respecting all constraints
- Balances speed across all four strokes
- Considers both actual and estimated times in calculations

### Output Format
- Displays complete relay lineups with stroke assignments
- Shows individual times for each swimmer
- Flags estimated times with an asterisk (*)
- Provides total relay time for each combination

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

---

## 🤝 Acknowledgements

This tool was created to support the **Steiner Stars** swim team, helping coaches make data-driven decisions with ease and precision.

