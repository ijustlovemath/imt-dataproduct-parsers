import sys
import argparse
import os
import matplotlib.pyplot as plt
from pprint import pprint
from imt_analysis import *
import pandas as pd
import numpy as np

# Trying to make it pretty
import seaborn

# This is hacky way to do this, but it should work well enough
subject_id_lookup = {
        "EM03" : "Subject 1",
        "EM02" : "Subject 2",
        "EM08" : "Subject 4",
        "EM12" : "Subject 5",
        "EM14" : "Subject 6",
        "EM17" : "Subject 7",
}


def datalog_to_datestr(filename):
    logname = os.path.basename(filename)
    logname = logname.rstrip(".csv")
    logname = logname.lstrip("IMT_data_log_")
    year, month, day, _ = logname.split("_")
    return f"{year}/{month}/{day}"


def create_plots(config, glucose_lims=(0,400), range_bars=(70, 180)):
    glucose_df, setup_info = get_data_log_df_setup(config.datalog)

    patient_id = setup_info["Subject Study ID"]
    subject_id = subject_id_lookup[patient_id] # yes, the naming is confusing. If this errors, you need to update for more patients

    study_date = datalog_to_datestr(config.datalog)

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
    
    pprint(pump_df['subject_id'].unique())
    print(patient_id)
    print(patient_id in pump_df['subject_id'].unique())
    pprint(pump_df)
    # Extract just the rates that apply to this patient
    # Support BOTH log formats (some have subject ID in quotes, others don't
    rates_forthis_pt = pump_df.where(
        (f"'{patient_id}'" == pump_df['subject_id']) 
        | (patient_id == pump_df['subject_id'])
    )
    
    '''
    Because the pump datafram contains _ALL_ pump rates, we can't
    calculate the relative timestamps UNTIL we've filtered it down
    to just one patient (who we ASSUME only comes once, this breaks
    if we have repeat patients)
    '''
    calculate_rel_time(rates_forthis_pt)
    
    needed_keys = ['subject_id', 'rel_time_min', 'substance', 'rate1_per_kg']
    rates_forthis_pt = rates_forthis_pt[needed_keys]

    # Extract substance specific rates
    insulin = rates_forthis_pt.where(rates_forthis_pt["substance"] == "Insulin").dropna()
    dextrose = rates_forthis_pt.where(rates_forthis_pt["substance"] == "Dextrose").dropna()
    
    if len(insulin["substance"]) < 5:
        pprint(insulin.head())
        raise ValueError("All data dropped for insulin!")


    # Set the font sizes (must happen before adding anything to the plot)
    fontsize=16
    plt.rc('font', size=fontsize)
    plt.rc('axes', titlesize=(fontsize + fontsize/2), labelsize=fontsize)
    plt.rc('legend', fontsize=fontsize-2)
    plt.rc('ytick', labelsize=fontsize-4)

    # Do all the plotting setup, add the axes
    fig, gluc_axis = plt.subplots()
    ins_axis = gluc_axis.twinx()
    dex_axis = gluc_axis.twinx()
    
    # Rename a commonly used piece of data; the times of glucose data
    gluc_times = glucose_df["rel_time_min"]

    # Remove excessive whitespace
    gluc_axis.set_xlim(-5, gluc_times.max() + 20)

    # Force the glucose axis to standard limits
    gluc_axis.set_ylim(*glucose_lims)

    # Make it 7.5in in x dimension, to fit in margins
#    fig.set_size_inches(7.5, 4.0)
#    fig.set_dpi(120) # works for my monitor only!
    
    # Label the axes
    gluc_axis.set_ylabel("Glucose (mg/dL)")
    gluc_axis.set_xlabel("Time (min)")
    ins_axis.set_ylabel("Insulin Rate (U/kg/hr)")
    dex_axis.set_ylabel("Dextrose Rate (mg/kg/min)")

    # Give it some breathing room, courtesy of here: https://towardsdatascience.com/adding-a-third-y-axis-to-python-combo-chart-39f60fb66708
    # They had a bug, though, its spines["right"]
    dex_axis.spines["right"].set_position(("axes", 1.08))

    # Add a title
    plt.title(f"{subject_id}")


    # Now plot the data, using the colors from the LabVIEW plot
    gluc_axis.plot(gluc_times, glucose_df["Glucose (mg/dL)"]
            , color="#0041DC"
            , marker='.'
            , label="Glucose (mg/dL)"
    )

    # Plot the efficacy range, 70-180mg/dL
    gluc_axis.plot(gluc_times, range_bars[0]*np.ones_like(gluc_times)
            , color="#00EBEF"
            , linestyle="dashed"
            , label="Efficacy Range"
    )
    gluc_axis.plot(gluc_times, range_bars[1]*np.ones_like(gluc_times)
            , color="#00EBEF"
            , linestyle="dashed"
    )
    try:
    # Insulin
        ins_axis.step(insulin["rel_time_min"], insulin["rate1_per_kg"]
            , color="#FF4242"
            , label="Insulin Rate (U/kg/hr)"
            , where="post"
        )
    except ValueError:
        pprint(insulin["rel_time_min"])
        pprint(insulin["rate1_per_kg"])
        pprint(rates_forthis_pt["rate1_per_kg"])
        raise

    # Dextrose (including boluses)
    dex_axis.step(dextrose["rel_time_min"], dextrose["rate1_per_kg"]
            , color="#0EFF00"
            , label="Dextrose Rate (mg/kg/min)"
            , where="post"
    )
    
    # Force the pump axes to start at 0
    # Do this after data has been plotted so the upper limit is set automatically
    ins_axis.set_ylim(bottom=0)
    dex_axis.set_ylim(bottom=0)
    
    # Combine the legends together into one
    h1, l1 = gluc_axis.get_legend_handles_labels()
    h2, l2 = dex_axis.get_legend_handles_labels()
    h3, l3 = ins_axis.get_legend_handles_labels()

    plt.legend(h1+h2+h3, l1+l2+l3, loc='best')

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
