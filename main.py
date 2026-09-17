from parser import parse_text
from fi_pta import perform_andersens_analysis, perform_steensgaards_analysis
from fs_pta import perform_fspta
from lfcpa import perform_lfcpa
from vasco_pta import perform_vascopta
import os, shutil, sys

def perform_analysis(text):
    parse_result = parse_text(text)

    if len(parse_result) == 2:
        return parse_result[0]

    struct_dict, func_dict, global_var_dict = parse_result

    if func_dict['main'] == 'error':
        return struct_dict

    results_dir = './results'
    if os.path.exists(results_dir):
        for filename in os.listdir(results_dir):
            file_path = os.path.join(results_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))
    else:
        os.mkdir(results_dir)

    # Merge globals with main's local vars for FI/FS analyses
    local_var_dict = func_dict['main'][1]
    combined_var_dict = {**global_var_dict, **local_var_dict}

    os.makedirs(results_dir+'/andersens/pta', exist_ok=True)
    perform_andersens_analysis(struct_dict, combined_var_dict, func_dict['main'][2], results_dir+'/andersens/')

    os.makedirs(results_dir+'/steensgaards/pta', exist_ok=True)
    perform_steensgaards_analysis(struct_dict, combined_var_dict, func_dict['main'][2], results_dir+'/steensgaards/')

    os.makedirs(results_dir+'/fspta/pta', exist_ok=True)
    perform_fspta(struct_dict, combined_var_dict, func_dict['main'][2], results_dir+'/fspta/')

    os.makedirs(results_dir+'/lfcpa/la', exist_ok=True)
    os.makedirs(results_dir+'/lfcpa/pta', exist_ok=True)
    perform_lfcpa(struct_dict, combined_var_dict, func_dict['main'][2], results_dir+'/lfcpa/')

    os.makedirs(results_dir+'/vasco/pta', exist_ok=True)
    perform_vascopta(struct_dict, func_dict, global_var_dict, results_dir+'/vasco/')

    return None

if __name__ == '__main__':
    if len(sys.argv)==2:
        file_name = sys.argv[1]
    else:
        file_name = "test.txt"

    with open(file_name) as f:
        err = perform_analysis(f.read())
    if err:
        print("ERROR:", err)
