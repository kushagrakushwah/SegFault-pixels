from pta_helper import *
import copy

def perform_fspta(struct_dict, var_dict, stmt_lst, result_dest):
    new_stmt_lst, successors, predecessors = get_fspta_stmts(struct_dict, stmt_lst)

    infoDict = {'pos_dicts':get_stmt_graph(new_stmt_lst, successors, result_dest+'code')}

    ptr_dicts = [{}]
    set_ptr_dict(var_dict, struct_dict, ptr_dicts[0])

    temp_ptr_dict = {}
    set_ptr_dict(var_dict, struct_dict, temp_ptr_dict, False)

    for _ in range(len(new_stmt_lst)-1):
        ptr_dicts.append(copy.deepcopy(temp_ptr_dict))
    del temp_ptr_dict

    stmt_no = 0
    for ptr_dict in ptr_dicts:
        save_dict_to_json(ptr_dict, result_dest+'pta/iter_0stmt_'+str(stmt_no)+'_out.json')
        stmt_no += 1

    iter = 0
    change = True
    while change:
        change = False
        iter += 1

        stmt_no = 0
        for stmt in new_stmt_lst:
            ptr_dict_out = ptr_dicts[stmt_no]
            old_len = nested_len_pt(ptr_dict_out)

            pred_ptr_dicts = []
            for pred in predecessors[stmt_no]:
                pred_ptr_dicts.append(ptr_dicts[pred])

            set_pin(ptr_dict_out, pred_ptr_dicts)
            # save_points_to_graph(ptr_dict_out, result_dest+'pta/iter_'+str(iter)+'stmt_'+str(stmt_no)+'_in')
            save_dict_to_json(ptr_dict_out, result_dest+'pta/iter_'+str(iter)+'stmt_'+str(stmt_no)+'_in.json')

            set_pout(ptr_dict_out, stmt)
            # save_points_to_graph(ptr_dict_out, result_dest+'pta/iter_'+str(iter)+'stmt_'+str(stmt_no)+'_out')
            save_dict_to_json(ptr_dict_out, result_dest+'pta/iter_'+str(iter)+'stmt_'+str(stmt_no)+'_out.json')

            change = change or (old_len != nested_len_pt(ptr_dict_out))

            stmt_no += 1

    print("FSPTA Iteration -", iter, "(confirmation)")

    infoDict['iters'] = iter
    save_dict_to_json(infoDict, result_dest+'info.json')