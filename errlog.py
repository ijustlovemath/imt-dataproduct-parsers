import sys
from collections import defaultdict
import datetime
import json

col_delim = ';'

def load(filename):
    with open(filename, 'r') as f:
        lines = [line.rstrip('\n') for line in f.readlines()]
    return lines

def df_from(headers, lines):
    df = defaultdict(list)
    for line in lines:
        for header, cell in zip(headers, line.split(col_delim)):
            df[header].append(cell)
    return df

def err_log_dataframe(filename):
    headers = ["timestamp", "severity", "UNUSED", "message", "code", "source", "call chain"]
    return df_from(headers, load(filename))

def err_log_timestamp(time_string):
    fmt = '%Y%m%d%H%M%S.%f'
    t = (datetime.datetime.strptime(time_string, fmt))
    return t

def err_log_fractional_sec(dt):
    return dt.timestamp()

def err_log_times(err_log_df):
    ''' Compute the unix timestamp, with fractional seconds,
    for each entry in the incoming
    log dictionaries'''
    return [
        err_log_fractional_sec(
            err_log_timestamp(string)
        )
        for string in err_log_df["timestamp"]
    ]

def err_log_times_relative(err_log_df, divisor=1.0):
    '''Gives a list of relative times for each log entry, default in seconds'''
    times = err_log_times(err_log_df)
    return [(x - min(times))/divisor for x in times]

def err_log_times_ms(err_log_df):
    ''' Gives a list of relative times for each log entry, in milliseconds'''
    return err_log_times_relative(err_log_df, divisor=1.0/1000.0)

def df_filter(err_log_df, filter_key=None, filter_fn=None):
    '''Evaluates filter_fn(value) for every value of 'filter_key' in the dataframe.

    Returns a dataframe with all series truncated to only indices for which this
    filter function evaluates to True'''

    # Make a copy since modifying dictionaries affects original
    err_log_df = err_log_df.copy()

    if filter_fn is None:
        return err_log_df
    if filter_key is None:
        raise ValueError("Must provide a dataframe key whose values to which we apply the filter")

    keys = list(err_log_df.keys())
    
    include = [filter_fn(x) for x in err_log_df[filter_key]]
    for key in keys:
        kept = [x for x, keep in zip(err_log_df[key], include) if keep]
        err_log_df[key] = kept

    return err_log_df

def get_sensor_dataframes(df):
    '''Get a list of dataframes containing individual sensor data, in mg/dL

    See: Working With IMT Data Products/Glucose Parsing for a detailed explanation
    of this process.

    Each dataframe will be at the index in the list corresponding to its sensor ID,
    and will have a "timestamp" key with the list of timestamps, a "value" key with
    the list of values, and a "rel_time" key with a list of relative times, in minutes.

    Example usage can be seen in plot_sensor_data(df)
    '''

    prefix = "Sensor Data: "
    sensor_data_df = df_filter(df, "message", lambda x: prefix in x)
    assert len(sensor_data_df["message"]) > 0, "No valid sensor data found in provided dataframe"

    # We know there's only two sensors for this study
    total_sensors = 2

    # Setup one dataframe for each sensor ID
    frames = [defaultdict(list) for i in range(total_sensors)]

    # In the first pass, get values and raw timestamps
    for timestring, message in zip(sensor_data_df["timestamp"], sensor_data_df["message"]):
        _, raw_json = message.split(prefix, 1)
        data_point = json.loads(raw_json)
        sensor_id = int(data_point["Sensor ID"])
        value = float(data_point["Value (mg/dL)"])

        # Add in the values and timestamps that we have
        frames[sensor_id]["timestamp"].append(timestring)
        frames[sensor_id]["value"].append(value)

    # In the second pass, add in the relative timestamps, in minutes
    # Only once we have all timestamps can we calculate relative ones
    for sensor_id in range(total_sensors):
        frames[sensor_id]["rel_time"] = err_log_times_relative(frames[sensor_id], divisor=60.0) 

    # Sanity check because Python loves to alias objects to each other
    assert frames[0] != frames[1]

    return frames

def get_pump_dataframe(df, substance=None):
    '''Get a dataframe containing pump rate data, and time in minutes

    See: Working With IMT Data Products/Pump Rate Parsing for 
    a detailed explanation of this process

    If you want to plot insulin rates over time, you can use it like so:
    df = get_pump_dataframe(df, 'Insulin')
    plt.plot(df["rel_time"], df["value"], label='Insulin')
    plt.show()'''
    if substance not in {"Insulin", "Dextrose"}:
        raise ValueError("Invalid substance, needs to be either 'Insulin' or 'Dextrose'")

    prefix = "changing pump rate to "

    pump_rate_df = df_filter(df, "message", lambda x: prefix in x and substance in x)

    # Messages formatted like 'changing pump rate to %f mL/hr %s, %f Secondss remaining'
    for message in pump_rate_df["message"]:
        _, contents = message.split(prefix)
        bucket = contents.split(' ')
        rate = float(bucket[0])

        # Quick sanity check
        msg_substance = bucket[2][:-1]
        assert msg_substance == substance

        # Ignore the seconds remaining

        # Add in the rate data
        pump_rate_df["value"].append(rate)

    pump_rate_df["rel_time"] = err_log_times_relative(pump_rate_df, divisor=60.0)
    return pump_rate_df

def plot_sensor_data(df):
    # Example usage of the sensor dataframes
    import matplotlib.pyplot as plt
    frames = get_sensor_dataframes(df)
    for i, frame in enumerate(frames):
        plt.plot(frame["rel_time"], frame["value"], label=f"ID {i}")
        
        import numpy as np
        print(f"\nreport for ID {i}")
    
        def analyze(name, callback):
            print(name, ":", callback(frame["value"]))
        
        analyze("mean", np.mean)
        analyze("cv", lambda x: 100.0*np.std(x)/np.mean(x))
        
        def inrange(x, lower, upper):
            return 100.0*sum(1 for val in x if lower <= val <= upper) / len(x)

        analyze("70-140", lambda x: inrange(x, 70, 140))
        analyze("0-70", lambda x: inrange(x, 0, 70))
        analyze("70-180", lambda x: inrange(x, 70, 180))
        analyze("100-140", lambda x: inrange(x, 100, 140))

    plt.legend(loc='upper right')
    plt.show()
    
base_patients = ["IMT_ERROR_LOG_20220629182758", "IMT_ERROR_LOG_20220706153403"]
root = "C:/Users/jcdej/MEGA/Dropbox/IMT-everything/Supporting documents/IMT Fusion - early human testing/Emory First Human Testing/IMT Data Export/2022_07_07_1541/Error Logs/Error Logs"
patients = [root + '/' + pt + '.log' for pt in base_patients]


def analyze_patient(filename):
    import os
    print(os.path.basename(filename))
    df = err_log_dataframe(filename)
    plot_sensor_data(df)

def plot_pump_data(df):
    import matplotlib.pyplot as plt
    substances = ["Insulin", "Dextrose"]
    frames = [get_pump_dataframe(df, substance) for substance in substances]
    for substance, frame in zip(substances, frames):
        plt.step(frame["rel_time"], frame["value"], label=substance)

    plt.legend(loc='upper right')
    plt.show()

def get_app_setup_info(df):
    '''Get dictionaries containing MR Number, weight, Initial glucose, etc.

    See: Working With IMT Data Products/Application Setup Information Parsing
    for a detailed explanation of this process

    Returns a tuple of dictionaries mapping output parameter names to "String Value" and "Double Value"

    If you want to, for example, access the weight (a floating point value), you can do it like so:
    _, info_floats = get_app_setup_info(df)
    weight = info_floats["Weight"]

    If you want to, for example, access the anonymized patient record number, aka MR Number (a string),
    you can do it like so:
    info_strings, _ = get_app_setup_info(df)
    mr_number = info_strings["MR Number"]
    '''
    app_setup_df = df_filter(df, "message", lambda x: "Output Parameters" in x)
    app_setup_json = app_setup_df["message"][0]
    app_setup_raw = json.loads(app_setup_json)
    app_setup_info_strings = {}
    app_setup_info_floats = {}

    for i in range(8):
        name_key = f"Output Parameters[{i}]:Output Parameter Name"
        string_value_key = f"Output Parameters[{i}]:String Value"
        float_value_key = f"Output Parameters[{i}]:Double Value"

        name = app_setup_raw[name_key]
        s = app_setup_raw[string_value_key]
        d = float(app_setup_raw[float_value_key])

        app_setup_info_strings[name] = s
        app_setup_info_floats[name] = d

    return app_setup_info_strings, app_setup_info_floats

def main(args):
    # A bunch of different functionality tests
    d = err_log_dataframe("IMT_ERROR_LOG_20210718014240.log")
    app_setup_info = get_app_setup_info(d)
    from pprint import pprint
    pprint(app_setup_info)
    plot_pump_data(d)
    plot_sensor_data(d)

if __name__ == '__main__':
    main(sys.argv)
