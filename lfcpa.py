from pta_helper import *

def perform_lfcpa(struct_dict, var_dict, stmt_lst, result_dest):
    new_stmt_lst, successors, predecessors = get_fspta_stmts(struct_dict, stmt_lst, True)

    infoDict = {'pos_dicts':get_stmt_graph(new_stmt_lst, successors, result_dest+'code')}

    ptr_dicts = {}
    set_ptr_dict(var_dict, struct_dict, ptr_dicts)

    temp_liveness_dict = {}
    for flds in ptr_dicts.values():
        for fld in flds:
            if fld not in temp_liveness_dict:
                temp_liveness_dict[fld] = set()

    temp_liveness_dict = (temp_liveness_dict, deepcopy(temp_liveness_dict))
    liveness_dicts = [deepcopy(temp_liveness_dict)]

    temp_ptr_dict = {}
    set_ptr_dict(var_dict, struct_dict, temp_ptr_dict, False)

    ptr_dicts = [(ptr_dicts, deepcopy(temp_ptr_dict))]
    temp_ptr_dict = (temp_ptr_dict, deepcopy(temp_ptr_dict))

    for _ in range(len(new_stmt_lst)-1):
        ptr_dicts.append(deepcopy(temp_ptr_dict))
        liveness_dicts.append(deepcopy(temp_liveness_dict))
    liveness_dicts.append(liveness_dicts.pop(0))
    del temp_ptr_dict
    del temp_liveness_dict

    if new_stmt_lst[-1].get_display_stmt() == 'loop':
        liveness_dicts.append(liveness_dicts.pop(0))
        updt_stmt_list = new_stmt_lst[:-1]
    else:
        updt_stmt_list = new_stmt_lst

    iters = []
    iter = 0
    while True:
        iter += 1
        l_iter = preform_ptbla(updt_stmt_list, successors, ptr_dicts, liveness_dicts, result_dest+'la/iter_'+str(iter)+'_')
        if l_iter == 1:
            iters.append((1,0))
            break
        pt_iter = preform_lbpta(updt_stmt_list, predecessors, ptr_dicts, liveness_dicts, result_dest+'pta/iter_'+str(iter)+'_')
        iters.append((l_iter, pt_iter))
        if pt_iter == 1:
            break

    print("LFCPA Iteration -", len(iters), iters)
    infoDict['iters'] = iters
    save_dict_to_json(infoDict, result_dest+'info.json')


def preform_lbpta(new_stmt_lst, predecessors, ptr_dicts, liveness_dicts, result_dest):
    iter = 0
    change = True
    while change:
        save_in_out_dicts_to_json(ptr_dicts, result_dest+str(iter)+'stmt_')

        change = False
        iter += 1
        
        stmt_no = 1

        for stmt in new_stmt_lst[1:]:
            ptr_dict_in = ptr_dicts[stmt_no][0]
            ptr_dict_out = ptr_dicts[stmt_no][1]
            old_len = not change and nested_len_pt(ptr_dict_out) + nested_len_pt(ptr_dict_in)
            stmt_liveness_dicts = liveness_dicts[stmt_no]

            pred_ptr_dicts = []
            for pred in predecessors[stmt_no]:
                pred_ptr_dicts.append(ptr_dicts[pred][1])

            set_lb_pin(ptr_dict_in, pred_ptr_dicts, stmt_liveness_dicts[0])
            # save_points_to_graph(ptr_dict_in, result_dest+str(iter)+'stmt_'+str(stmt_no)+'_in')
            # save_dict_to_json(ptr_dict_in, result_dest+str(iter)+'stmt_'+str(stmt_no)+'_in.json')

            set_lb_pout(ptr_dict_out, stmt, stmt_liveness_dicts[1], ptr_dict_in)
            # save_points_to_graph(ptr_dict_out, result_dest+str(iter)+'stmt_'+str(stmt_no)+'_out')
            # save_dict_to_json(ptr_dict_out, result_dest+str(iter)+'stmt_'+str(stmt_no)+'_out.json')

            change = change or (old_len != (nested_len_pt(ptr_dict_out) + nested_len_pt(ptr_dict_in)))

            stmt_no += 1

    save_in_out_dicts_to_json(ptr_dicts, result_dest+str(iter)+'stmt_')

    return iter

def preform_ptbla(new_stmt_lst, successors, ptr_dicts, liveness_dicts, result_dest):
    iter = 0
    change = True
    
    while change:
        save_in_out_inverted_dicts_to_json(liveness_dicts, result_dest+str(iter)+'stmt_')

        change = False
        iter += 1

        stmt_no = len(new_stmt_lst)-2
        for stmt in new_stmt_lst[-2::-1]:
            liveness_dict_in = liveness_dicts[stmt_no][0]
            liveness_dict_out = liveness_dicts[stmt_no][1]
            old_len = not change and (nested_len_l(liveness_dict_in) + nested_len_l(liveness_dict_out))

            succ_liveness_dicts = []
            for succ in successors[stmt_no]:
                succ_liveness_dicts.append(liveness_dicts[succ][0])

            set_lout(liveness_dict_out, succ_liveness_dicts)
            # save_dict_to_json(liveness_dict_out, result_dest+str(iter)+'stmt_'+str(stmt_no)+'_out.json')
            
            set_lin(liveness_dict_in, stmt, ptr_dicts[stmt_no][0], liveness_dict_out)
            # save_dict_to_json(liveness_dict_in, result_dest+str(iter)+'stmt_'+str(stmt_no)+'_in.json')

            change = change or (old_len != (nested_len_l(liveness_dict_in) + nested_len_l(liveness_dict_out)))

            stmt_no -= 1

    save_in_out_inverted_dicts_to_json(liveness_dicts, result_dest+str(iter)+'stmt_')
    return iter