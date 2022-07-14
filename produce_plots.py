import sys
import argparse
import matplotlib.pyplot as plt
from imt_analysis import get_data_log_df_setup
import pandas as pd
import numpy as np

# Trying to make it pretty
import seaborn

def create_plots(config):
    glucose_df, setup_info = get_data_log_df_setup(config.datalog)

    patient_id = setup_info["Subject Study ID"]

    pump_df = pd.read_csv(config.ratelog)

    # Convert both datetime columns to native timestamps
    def fix_datetime(df, column_name, offset_hrs=None):
        df["timestamp"] = pd.to_datetime(df[column_name])
        if offset_hrs:
            df["timestamp"] += pd.Timedelta(hours=offset_hrs)
    def calculate_rel_time(df):
        df["rel_time_min"] = pd.to_timedelta(df["timestamp"] - df["timestamp"].min()).dt.total_seconds()/60.0

    '''The "System Time" has an ISO8601 timestamp,
    but it LIES (ok, mistake on my part!), so we
    need to adjust it by 4 hours to align with 
    the _real_ UTC timestamp in the pump rates
    '''
    fix_datetime(glucose_df, "System Time", offset_hrs=0)
    calculate_rel_time(glucose_df)

    fix_datetime(pump_df, "log_timestamp")

    # Extract just the rates that apply to this patient
    rates_forthis_pt = pump_df.where(f"'{patient_id}'" == pump_df['subject_id'])
    '''
    Because the pump datafram contains _ALL_ pump rates, we can't
    calculate the relative timestamps UNTIL we've filtered it down
    to just one patient (who we ASSUME only comes once, this breaks
    if we have repeat patients)
    '''
    calculate_rel_time(rates_forthis_pt)

    # Extract substance specific rates
    insulin = rates_forthis_pt.where(rates_forthis_pt["substance"] == "Insulin")
    dextrose = rates_forthis_pt.where(rates_forthis_pt["substance"] == "Dextrose")


    # Do all the plotting setup, add the axes
    fig, gluc_axis = plt.subplots()
    ins_axis = gluc_axis.twinx()
    dex_axis = gluc_axis.twinx()

    gluc_axis.set_xlim(-5, glucose_df["rel_time_min"].max() + 20)
    
    # Label the axes
    gluc_axis.set_ylabel("Glucose (mg/dL)")
    gluc_axis.set_xlabel("Time (min)")
    ins_axis.set_ylabel("Insulin Rate (U/kg/hr)")
    dex_axis.set_ylabel("Dextrose Rate (mg/kg/min)")

    # Give it some breathing room, courtesy of here: https://towardsdatascience.com/adding-a-third-y-axis-to-python-combo-chart-39f60fb66708
    # They had a bug, though, its spines["right"]
    dex_axis.spines["right"].set_position(("axes", 1.08))


    # Now plot the data, using the colors from the LabVIEW plot
    gluc_axis.plot(glucose_df["rel_time_min"], glucose_df["Glucose (mg/dL)"]
            , color="#0041DC"
            , marker='.'
            , label="Glucose (mg/dL)"
    )

    # Control range
    gluc_axis.plot(glucose_df["rel_time_min"], 100*np.ones_like(glucose_df["rel_time_min"])
            , color="#00EBEF"
            , linestyle="dashed"
            , label="Control Range"
    )
    gluc_axis.plot(glucose_df["rel_time_min"], 140*np.ones_like(glucose_df["rel_time_min"])
            , color="#00EBEF"
            , linestyle="dashed"
    )

    # Insulin
    ins_axis.plot(insulin["rel_time_min"], insulin["rate1_per_kg"]
            , color="#FF4242"
            , label="Insulin Rate (U/kg/hr)"
    )

    # Dextrose (including boluses)
    dex_axis.plot(dextrose["rel_time_min"], dextrose["rate1_per_kg"]
            , color="#0EFF00"
            , label="Dextrose Rate (mg/kg/min)"
    )

    plt.show()


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("--datalog", help="path to IMT_data_log for aggregate sensor data")
    parser.add_argument("--ratelog", help="path to pump_rate_parsed.csv")

    parser.add_argument("--save", help="save the figures in current directory", action="store_true")

    config = parser.parse_args(args)

    create_plots(config)

if __name__ == '__main__':
    main(sys.argv[1:])
