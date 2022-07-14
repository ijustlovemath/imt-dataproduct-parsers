from collections import defaultdict
import re
import os
import glob
import zipfile

'''Folders go like: Patient ID 
    -> Patient ID Data Export 
    ->  |
        | -> Data Logs.zip -> Data Logs -> IMT_data_log_$date.csv
        | -> Error Logs.zip -> Error Logs -> IMT_ERROR_LOG_$date.log
    '''
log_types = ["Data", "Error"]
log_suffix_lookup = {
        "Data": ("_data_log_", "%Y_%m_%d_%H%M", ".csv"),
        "Error": ("_ERROR_LOG_", "%Y%m%d%H%M%S", ".log")
}

patient_id_regex = "EM\d+"

def patient_root_gen(searchdir="."):
    patient_root_regex = os.path.expanduser(os.path.expandvars(searchdir + '/*' ))
    
    # We want all directories that end in the patient ID regex
    pattern = re.compile(".*" + patient_id_regex)

    for directory in glob.glob(patient_root_regex):
        if pattern.match(directory):
            yield directory, os.path.basename(directory)

def paired_log_reader_gen(patient_root_dir):
    log_collection = defaultdict(list)
    print(patient_root_dir)
    for data_export in glob.glob(patient_root_dir + "/*"):
        print(data_export)
        for export_session in glob.glob(data_export + "/*"):
            print(export_session)
            for kind in log_types:
                archive = os.path.join(export_session, f"{kind} Logs.zip")
                print(archive)
                with zipfile.ZipFile(archive) as zippy:
                    files_archived = zippy.namelist()
                    suffix, _, extension = log_suffix_lookup[kind]
                    for _ in zippy.infolist():
                        print(_)
                    
                    for name in files_archived:
                        print(name)
                        if ("IMT" + suffix) in name and name.endswith(extension):
                            log_collection[kind].append(archive, name)
                            print(archive_name)
                            yield archive, name


if __name__ == '__main__':
    from imt_config import PATIENT_DATA_ROOT
    print("foo)")
    for root, patient_id in patient_root_gen(PATIENT_DATA_ROOT):
        print("foo)")
        print(root, patient_id)
        paired_log_reader_gen(root)


