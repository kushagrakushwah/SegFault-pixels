from pta_helper import *
import graphviz

def perform_andersens_analysis(struct_dict, var_dict, stmt_lst, result_dest):
    ptr_dict = {}
    set_ptr_dict(var_dict, struct_dict, ptr_dict, False)
    new_stmt_lst = get_pta_stmts(struct_dict, stmt_lst)
    infoDict = {'pos_dicts':get_stmt_graph(new_stmt_lst, None, result_dest+'code')}
    pta_dest = result_dest + 'pta/'
    result_dest_iter = pta_dest + 'iter_'
    count = 0
    change = True
    while change:
        save_dict_to_json(ptr_dict, result_dest_iter+str(count)+'.json')
        change = False
        for stmt in new_stmt_lst:
            lhs = stmt.get_lhs()
            rhs = stmt.get_rhs()
            pointees = get_pointees(ptr_dict, rhs)
            vars, fld = get_defs(ptr_dict, lhs)
            for var in vars:
                old_len = len(ptr_dict[var][fld])
                ptr_dict[var][fld].update(pointees)
                change = change or (old_len != len(ptr_dict[var][fld]))
        count += 1
    save_dict_to_json(ptr_dict, result_dest_iter+str(count)+'.json')
    svg_bytes = save_points_to_graph(ptr_dict, None)
    with open(pta_dest + 'final.svg', 'wb') as f:
        f.write(svg_bytes)
    print("Andersens Iteration -", count)
    infoDict['iters'] = count
    save_dict_to_json(infoDict, result_dest+'info.json')

def perform_steensgaards_analysis(struct_dict, var_dict, stmt_lst, result_dest):
    ptr_dict = {}
    isunk_ptr_dict = {}
    var_to_set_dict = {None:None}
    set_to_var_dict = {}
    for var, typ in var_dict.items():
        var_to_set_dict[var] = var
        set_to_var_dict[var] = [var]
        if contains_pointer(typ, struct_dict):
            ptr_dict[var] = {}
            isunk_ptr_dict[var] = False
            if typ[-1] == '*':
                ptr_dict[var]['*'] = None
            else:
                for field, field_typ in struct_dict[typ][0].items():
                    if field_typ[-1] == '*':
                        ptr_dict[var][field] = None
    new_stmt_lst = get_pta_stmts(struct_dict, stmt_lst)
    infoDict = {'pos_dicts':get_stmt_graph(new_stmt_lst, None, result_dest+'code')}
    count = 0
    change = True
    while change:
        change = False
        count += 1
        for stmt in new_stmt_lst:
            lhs = stmt.get_lhs()
            rhs = stmt.get_rhs()
            pointee = get_pointee(ptr_dict, rhs, var_to_set_dict)
            if pointee is None:
                continue
            var, fld = get_def(ptr_dict, lhs, var_to_set_dict)
            if var == None:
                continue
            old_var = ptr_dict[var][fld]
            if old_var is None:
                ptr_dict[var][fld] = pointee
                change = True
            else:
                sets_to_unify = [pointee, var_to_set_dict[old_var]]
                change = unify(ptr_dict, sets_to_unify, var_to_set_dict, set_to_var_dict) or change
    print("Steensgaard Iteration -", count)
    infoDict['iters'] = count
    save_dict_to_json(infoDict, result_dest+'info.json')
    pta_dest = result_dest + 'pta/'
    c = 0
    dot = graphviz.Digraph(comment="Steensgaards PTA", node_attr={'colorscheme':colorscheme,'style':'filled'}, edge_attr={'colorscheme':colorscheme}, graph_attr={'rankdir':'LR','bgcolor':'transparent'}, engine='dot')
    color_dict = {}
    for node in ptr_dict.keys():
        c = update_count(c)
        color_dict[node] = str(c)
        label = '\n'.join(set_to_var_dict[node])
        dot.node(node, label, color=str(c))
    for key, val in ptr_dict.items():
        for key2, val2 in val.items():
            if val2 is None:
                continue
            lbl = chr(8315) if key2 == '*' else key2
            dot.edge(key, var_to_set_dict[val2], label=lbl, color=color_dict[key])
    dot.render(pta_dest+'final', format='svg', cleanup=True)
