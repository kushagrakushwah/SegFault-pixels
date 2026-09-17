import graphviz
import json
from math import ceil, floor

# Datatype to store the points to pairs. The first field is the pointer and the second field is the field
PointerDict = dict[str, dict[str, set[str]]]
LivenessDict = dict[str, set[str]]

num_colors = 9
colorscheme = 'set19'

def update_count(count):
    count = 1 + (count == 5) + (count!=num_colors)*count
    return count


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

def save_dict_to_json(dict, result_dest):
    with open(result_dest, 'w') as result_file:
        json.dump(dict, result_file, cls = SetEncoder, indent='\t')

def save_in_out_dicts_to_json(in_out_dicts, result_dest):
    stmt_no = 0
    for (dict_in, dict_out) in in_out_dicts:
        save_dict_to_json(dict_in, result_dest+str(stmt_no)+'_in.json')
        save_dict_to_json(dict_out, result_dest+str(stmt_no)+'_out.json')
        stmt_no += 1

def save_in_out_inverted_dicts_to_json(in_out_dicts, result_dest):
    stmt_no = 0
    for (dict_in, dict_out) in in_out_dicts:
        save_dict_to_json(invert_dict(dict_in), result_dest+str(stmt_no)+'_in.json')
        save_dict_to_json(invert_dict(dict_out), result_dest+str(stmt_no)+'_out.json')
        stmt_no += 1

def invert_dict(dict:dict):
    inverted_dict = {}
    for key, vals in dict.items():
        for val in vals:
            if val in inverted_dict:
                inverted_dict[val].append(key)
            else:
                inverted_dict[val] = [key]
    return inverted_dict

def nested_len_pt(ptr_dict):
    return sum(sum(len(val2) for val2 in val.values()) for val in ptr_dict.values())

def nested_len_l(liveness_dict):
    return sum(len(val) for val in liveness_dict.values())
        
def get_stmt_graph(stmt_lst, successors, result_file):
    dot = graphviz.Digraph(comment="stmt_graph", node_attr={'shape':'box'}, graph_attr={'bgcolor':'transparent'}, engine='dot')
    
    i = 0
    # with dot.subgraph(name='cluster0') as c:
    for stmt in stmt_lst:
        # dot.node(str(i), format_stmt(stmt))
        dot.node(str(i), stmt.get_display_stmt())
        i += 1
        # c.attr(label = 'Hello')

    if successors:
        i = 0
        for succs in successors[:-1]:
            if succs:
                for succ in succs:
                    dot.edge(str(i), str(succ))
            i += 1
    else:
        for i in range(len(stmt_lst)-1):
            dot.edge(str(i), str(i+1), color = 'transparent')

    dot.render(result_file, format='svg', cleanup=True, engine='dot')
    # dot.render(result_file, format='json0', cleanup=True, engine='dot')

    dpi = 72

    pos_dicts = {}
    for obj in json.loads(dot.pipe(format='json0'))['objects']:
        pos_dict = {}
        pos_dict['h'] = ceil(float(obj['height'])*dpi)
        pos_dict['w'] = ceil(float(obj['width'])*dpi)
        pos = obj['pos'].split(',')
        pos_dict['x'] = floor(((float(pos[0])+4)*dpi)/72 - pos_dict['w']/2)
        pos_dict['y'] = ceil(((float(pos[1])+4)*dpi)/72 + pos_dict['h']/2)
        pos_dicts[obj['name']] = pos_dict

    return pos_dicts

#TODO check later
def contains_pointer(struct, struct_dict):
    if struct == 'scalar':
        return False
    elif struct[-1] == '*':
        return True
    else:
        for typ in struct_dict[struct][0].values():
            if typ[-1] == '*':
                return True
    return False

def get_next_counter(ind, counter_lst):
    seen = set()
    seen_size = -1
    while seen_size!=len(seen):
        if ind == counter_lst[ind]:
            break
        seen_size = len(seen)
        seen.add(ind)
        
        while counter_lst[ind] == None:
            ind += 1
            seen.add(ind)
        ind = counter_lst[ind]

    if ind != counter_lst[ind]:
        ind = counter_lst[-1]

    for seen_ind in seen:
        counter_lst[seen_ind] = ind

    return ind

# def get_color_dict(ptr_dict):
#     count = 0
#     color_dict = {}

#     for node in ptr_dict:
#         count = update_count(count)
#         color_dict[node] = str(count)

#     return color_dict

def save_points_to_graph(ptr_dict:dict, filename:str|None):
    count = 0
    dot = graphviz.Digraph(node_attr={'colorscheme':colorscheme, 'style':'filled'}, edge_attr={'colorscheme':colorscheme}, graph_attr={'rankdir':'LR', 'bgcolor':'transparent'}, engine='dot')
    color_dict = {}

    for node in ptr_dict:
        count = update_count(count)
        color_dict[node] = str(count)
        dot.node(node, color = str(count))

    for key, val in ptr_dict.items():
        for key2, val2 in val.items():
            if key2 == '*':
                key2 = '⁎'
            for v in val2:
                dot.edge(key, v, label = key2, color = color_dict[key])
    if filename:
        dot.render(filename, format='png', cleanup=True)
    else:
        return dot.pipe(format='svg')

def get_points_to_graph_from_file(input_filename:str, output_filename:str|None = None):
    with open(input_filename, 'r') as input_file:
        ptr_dict = json.load(input_file)

    return save_points_to_graph(ptr_dict, output_filename)

    