import sys

import pandas as pd

if len(sys.argv) != 2:
    raise ValueError("provide ysi_tracker path as script argument")

df = pd.read_csv(sys.argv[1])
subjects = pd.unique(df["subject_id"])

def icgm_criteria(reference, observed, passing_percentage, threshold, mode="relative"):
    assert len(reference) == len(observed), "need matching series to compare"
    assert mode in {"relative", "absolute"}, "unrecognized mode"
    
    count = 0
    total = len(reference)
    if total == 0:
        return True, 100.0
    for r, o in zip(reference, observed):

        # all values are +/- threshold, so use abs
        to_test = abs(r - o)

        if mode == "relative":
            to_test = 100 * to_test / r
        
        count = count + (1 if to_test < threshold else 0)
    result = 100 * count/total
    test_passed = result > passing_percentage

    return test_passed, result


tests_lt70 = [(87, 20, "relative")
        , (85, 15, "absolute")
        , (98, 40, "absolute")
        , ("no values >180", lambda r, o: all(x < 180 for x in o))
    ]

tests_70to180 = [(70, 15, "relative")
        , (99, 40, "relative")
    ]
tests_gt180 = [(99, 40, "relative")
        , ("no values <70", lambda r, o: all(x > 70 for x in o))
    ]

odf = df.copy()
df = odf.copy()
corpus_lt70 = "all values <70", df.where(df["reference_glucose"] < 70), tests_lt70
df = odf.copy()
corpus_70to180 = "all values 70-180", df.where(((70 <= df["reference_glucose"]) & (df["reference_glucose"] <= 180))), tests_70to180
df = odf.copy()
corpus_gt180 = "all values >180", df.where(df["reference_glucose"] > 180), tests_gt180

for corpus in [corpus_lt70, corpus_70to180, corpus_gt180]:
    description, df, tests = corpus

    df = df.dropna(subset=
            ["reference_glucose"
                , "sensor0_glucose"
                , "sensor1_glucose"
                , "sensoravg_glucose"
            ]
        ) # just get rid of unpaired values

    reference = df["reference_glucose"]
    sensors = df["sensor0_glucose"], df["sensor1_glucose"], df["sensoravg_glucose"]

    print(f"\nTesting corpus: {description}")

    for i, sensor in enumerate(sensors):
        for test in tests:
            # The lambda based tests have the second element as the test lamba
            # This is definitely hacky, should probably figure out a better way
            # had to do it this way because i wanted the lambda functions to hava
            # a description available but couldnt figure out how to implement it
            # and keep the integrity of the tuple base tests intact
            if not callable(test[1]):
                passing, threshold, mode = test

                # The following relies on icgm's function signature matching
                # the ordering of the test tuple!
                test_passed, result = icgm_criteria(reference, sensor, *test)

                suffix = "%" if mode == "relative" else " mg/dl"
                summary = f"Sensor {i} | {result}% should be > {passing}% for 'within +/-{threshold}{suffix}' to pass"
            else:
                description, checker = test
                test_passed = checker(reference, sensor)
                
                summary = f"Sensor {i} | {description}"
            if test_passed:
                print(f"[PASS] {summary}")
            else:
                print(f"[FAIL] {summary}")
