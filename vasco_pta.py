from pta_helper import *
import copy

def is_equal(ptr_dict1, ptr_dict2):
    if (len(ptr_dict1)!=len(ptr_dict2)) or (set(ptr_dict1.keys())!=set(ptr_dict2.keys())):
        return False
    for key, val in ptr_dict1.items():
        for key2, val2 in ptr_dict2[key].items():
            if val2!=val[key2]:
                return False
    return True

def add_ptr_dict(ptr_dict, extra_ptr_dict, f_args, a_args):
    init_len = len(extra_ptr_dict)
    for f, a in zip(f_args, a_args):
        if a in extra_ptr_dict:
            ptr_dict[f] = copy.deepcopy(extra_ptr_dict[a])
    for key, val in extra_ptr_dict.items():
        if key in ptr_dict:
            flds = ptr_dict[key]
            for key1, val1 in val.items():
                if key1 in flds:
                    flds[key1].update(val1)
        else:
            flds = {}
            for key1, val1 in val.items():
                flds[key1] = val1.copy()
            ptr_dict[key] = flds
    return init_len!=len(ptr_dict)

def merge_callee_result(caller_dict, callee_result):
    """Merge callee's result into caller's ptr_dict.
    Only updates keys that already exist in caller_dict (shared globals + caller vars).
    """
    for key in caller_dict:
        if key in callee_result:
            for fld in caller_dict[key]:
                if fld in callee_result[key]:
                    caller_dict[key][fld].update(callee_result[key][fld])

def get_updated_func_dict(struct_dict, func_dict, global_varnames=set()):
    updated_func_dict = {}
    func_val = {'main':0}
    count = 1
    for func in func_dict.keys():
        if func=='main':
            continue
        func_val[func] = count
        count += 1

    for func, (args, var_dict, stmt_lst) in func_dict.items():
        funcID = "_"+str(func_val[func])

        filtered_stmt_lst, successors, predecessors = get_fspta_stmts(struct_dict, stmt_lst, vasco=True)

        new_args = []
        for arg in args:
            if arg in global_varnames:
                new_args.append(arg)
            else:
                new_args.append(arg+funcID)

        new_var_dict = {}
        for varName, varType in var_dict.items():
            if varName in global_varnames:
                new_var_dict[varName] = varType
            else:
                new_var_dict[varName+funcID] = varType

        new_stmt_lst = []
        for stmt in filtered_stmt_lst:
            new_stmt = copy.deepcopy(stmt)
            new_stmt.add_funcID(funcID)
            new_stmt_lst.append(new_stmt)

        updated_func_dict[func] = (new_args, new_var_dict, new_stmt_lst, successors, predecessors)

    return updated_func_dict


def perform_vascopta(struct_dict, func_dict, global_vardict, result_dest):
    global_varnames = set(global_vardict.keys())
    merged_func_dict = {}
    for func_uid, func_val in func_dict.items():
        args, var_dict, stmts = func_val[0], func_val[1], func_val[2]
        merged_var_dict = {**global_vardict, **var_dict}
        merged_func_dict[func_uid] = (args, merged_var_dict, stmts)

    updated_func_dict = get_updated_func_dict(struct_dict, merged_func_dict, global_varnames)

    startedAnalysis = {}
    completedAnalysis = {}
    context_log = []

    for func in merged_func_dict.keys():
        startedAnalysis[func] = []
        completedAnalysis[func] = []

    context = ('main', {}, [])

    main_data = updated_func_dict['main']
    main_stmt_lst   = main_data[2]
    main_successors = main_data[3]
    infoDict = {'pos_dicts': get_stmt_graph(main_stmt_lst, main_successors, result_dest+'code')}

    final_ptr_dict = vasco_pta_proc(
        struct_dict, updated_func_dict, context, result_dest,
        startedAnalysis, completedAnalysis, context_log, is_top_level=True
    )

    save_dict_to_json({'log': context_log}, result_dest+'context_log.json')
    infoDict['iters'] = getattr(vasco_pta_proc, '_last_iter', 1)
    save_dict_to_json(infoDict, result_dest+'info.json')
    print("VASCO PTA complete, iters =", infoDict['iters'])
    return final_ptr_dict


def vasco_pta_proc(struct_dict, func_dict, context, result_dest,
                   startedAnalysis, completedAnalysis, context_log,
                   is_top_level=False):

    args, var_dict, stmt_lst, successors, predecessors = func_dict[context[0]]

    ptr_dicts = [{}]
    set_ptr_dict(var_dict, struct_dict, ptr_dicts[0])

    temp_ptr_dict = {}
    set_ptr_dict(var_dict, struct_dict, temp_ptr_dict, False)

    for _ in range(len(stmt_lst)-1):
        ptr_dicts.append(copy.deepcopy(temp_ptr_dict))
    del temp_ptr_dict

    add_ptr_dict(ptr_dicts[0], context[1], args, context[2])

    sa_ind = len(startedAnalysis[context[0]])
    startedAnalysis[context[0]].append(copy.deepcopy(ptr_dicts[0]))
    context_log.append("START: %s (ctx #%d)" % (context[0], sa_ind))

    iter_num = 0
    change = True
    while change:
        change = False
        iter_num += 1

        stmt_no = 0
        for stmt in stmt_lst:
            ptr_dict_out = ptr_dicts[stmt_no]
            old_len = nested_len_pt(ptr_dict_out)

            pred_ptr_dicts = [ptr_dicts[pred] for pred in predecessors[stmt_no]]
            set_pin(ptr_dict_out, pred_ptr_dicts)

            if is_top_level:
                save_dict_to_json(ptr_dict_out,
                    result_dest+'pta/iter_%dstmt_%d_out.json' % (iter_num, stmt_no))

            if stmt.is_stmt_type(stmt_types.CAL):
                if not change:
                    funcID = stmt.get_uid()
                    if funcID not in startedAnalysis:
                        startedAnalysis[funcID] = []
                        completedAnalysis[funcID] = []

                    found = False
                    for sa_context in startedAnalysis[funcID]:
                        if is_equal(sa_context, ptr_dict_out):
                            found = True
                            break
                    if found:
                        stmt_no += 1
                        continue

                    found = False
                    for ca_context in completedAnalysis[funcID]:
                        if is_equal(ca_context[0], ptr_dict_out):
                            # Merge callee's result back into caller's ptr_dict
                            merge_callee_result(ptr_dict_out, ca_context[1])
                            found = True
                            break
                    if not found:
                        actual_args = [arg.varName for arg in stmt.args]
                        context_log.append("CALL: %s -> %s" % (context[0], funcID))
                        callee_result = vasco_pta_proc(
                            struct_dict, func_dict,
                            (funcID, ptr_dict_out, actual_args),
                            result_dest, startedAnalysis,
                            completedAnalysis, context_log
                        )
                        # Merge callee's result (globals) back into caller's ptr_dict
                        merge_callee_result(ptr_dict_out, callee_result)

                change = change or (old_len != nested_len_pt(ptr_dict_out))
                stmt_no += 1
                continue

            set_pout(ptr_dict_out, stmt)
            change = change or (old_len != nested_len_pt(ptr_dict_out))
            stmt_no += 1

    context_log.append("DONE: %s (ctx #%d, %d iters)" % (context[0], sa_ind, iter_num))

    # BUG B FIX
    entry = startedAnalysis[context[0]][sa_ind]
    del startedAnalysis[context[0]][sa_ind]
    completedAnalysis[context[0]].append((entry, copy.deepcopy(ptr_dicts[-1])))

    if is_top_level:
        vasco_pta_proc._last_iter = iter_num

    return ptr_dicts[-1]

vasco_pta_proc._last_iter = 1
