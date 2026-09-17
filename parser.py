import ply.yacc as yacc
from scanner import tokens
from stmt_helper import *

precedence = (
    ('left', 'NUMBER'),
    ('left', 'VARNAME'),
    ('nonassoc', 'LVL1'),
    ('nonassoc', 'LVL2'),
)

# list of statements
statements = []

flno = 0
lnomap = []
lno = 1
alno = 1

# Used for error checking
defstructlist = {'scalar'}
usedstructlist = set()
deffunclist = set()
funcdict = {}
usedfunclist = set()

# For global pointers and variables
global_varlist = set()   # Stores names of all declared global variables
global_vardict = {}      # Maps global variables to their types (e.g., 'scalar*')
is_global_scope = True   # State flag tracking whether we are currently in global block

# Used for error checking
varlist = set()
structdict = {'scalar':[{},set()]}
# Saved for each function
vardict = {}

start = "prog"

def prepare_next_function():
    global lnomap, alno
    statements.clear()
    lnomap = []
    alno = 1
    varlist.clear()
    vardict.clear()

def checkvar(var:variable):
    varName = var.get_display_value()
    if varName in vardict:
        return vardict[varName]
    elif varName in global_vardict:
        var.is_global = True  # <-- ADD THIS LINE
        return global_vardict[varName]
    else:
        raise Exception("Variable '"+ varName +"' used without initialization, at line number "+ str(lno))
    
def checktype(var:variable, typ:str):
    if checkvar(var) != typ:
        raise Exception("Type Error: Variable '"+ var.get_display_value() +"' expected to be '"+ typ +"', but got '"+ vardict[var.get_display_value()] +"' instead, at line number "+ str(lno))

def checkfield(var:variable, field:variable):
    typ = checkvar(var)
    if typ[-1] == '*':
        raise Exception("Type Error: Variable '"+ var.get_display_value() +"' expected to be a structure, but got a structure pointer ('"+ typ +"') instead, at line number "+ str(lno))
    if typ == 'scalar':
        raise Exception("Type Error: Tried to access a field of a scalar variable '"+ var.get_display_value() +"' at line number "+str(lno))
    fieldName = field.get_display_value()
    if fieldName not in structdict[typ][1]:
        raise Exception("Type Error: '"+ fieldName +"' is not a field of structure '"+ typ +"', at line number "+ str(lno))
    return structdict[typ][0][fieldName]

def checkptrfield(var:variable, field:variable):
    typ = checkvar(var)
    if typ[-1] != '*':
        raise Exception("Type Error: Variable '"+ var.get_display_value() +"' expected to be a structure pointer, but got a structure ('"+ typ +"') instead, at line number "+ str(lno))
    typ = typ[:-1]
    if typ == 'scalar':
        raise Exception("Type Error: Tried to access a field of a scalar pointer '"+ var.get_display_value() +"' at line number "+str(lno))
    fieldName = field.get_display_value()
    if fieldName not in structdict[typ][1]:
        raise Exception("Type Error: '"+ fieldName +"' is not a field of structure '"+ typ +"', at line number "+ str(lno))
    return structdict[typ][0][fieldName]
    
def param_to_string(lst):
    op = '('
    l = len(lst)
    if l>0:
        op = op + lst[0]
    for ind in range(1,l):
        op = op + ', ' + lst[ind]
    return op + ')'

def clean_statements():
    alno = 1
    lnomap.extend([lnomap[-1]+1]*(lno-flno+1-len(lnomap)))
    for s in statements:
        if s.is_stmt_type(stmt_types.IF):
            goto_lno = s.get_lno()
            if goto_lno>lno or goto_lno<flno:
                raise Exception("Target line number not in the range of function at line "+str(len(lnomap)-lnomap[::-1].index(alno)+flno-1))
            s.set_lno(lnomap[goto_lno-flno])
        elif s.is_stmt_type(stmt_types.GOT):
            goto_lno = s.get_lno()
            if goto_lno>lno or goto_lno<flno:
                raise Exception("Target line number not in the range of function at line "+str(len(lnomap)-lnomap[::-1].index(alno)+flno-1))
            s.set_lno(lnomap[goto_lno-flno])

        alno = alno+1

    return [plain_text('START')] + statements + [plain_text('END')]


def p_space(p):
    '''space : %prec LVL1
             | SPACES %prec LVL2'''
    p[0] = ''

def p_bool_op(p):
    '''boolop : space LTE space
              | space GTE space
              | space "<" space
              | space ">" space
              | space "=" "=" space
              | space "!" "=" space'''
    if p[2] == '=':
        p[0] = '=='
    elif p[2] == '!':
        p[0] = '!='
    else:
        p[0] = p[2]

def p_bool_exp(p):
    '''boolexp : VARNAME boolop VARNAME
               | VARNAME boolop NUMBER
               | NUMBER boolop VARNAME
               | NUMBER boolop NUMBER'''
    p[0] = boolExp(p[1], p[3], p[2])

    if p[1].is_elem_type(elem_types.VAR):
        checktype(p[1], 'scalar')
    if p[3].is_elem_type(elem_types.VAR):
        checktype(p[3], 'scalar')

def p_lhs(p):
    '''lhs : STARS VARNAME
           | VARNAME "-" ">" VARNAME
           | VARNAME "." VARNAME'''
    if isinstance(p[1], str):
        typ = checkvar(p[2])
        if p[1] != '*':
            raise Exception("A variable can be dereferenced only once in a single statement, line "+str(lno))
        if typ[-1] != '*':
            raise Exception("Tried to dereference a non pointer '"+p[2].get_display_value()+"' at line "+str(lno))
        p[0] = [typ[:-1], pointer(p[2])]
    elif p[2] == '-':
        p[0] = [checkptrfield(p[1], p[4]), fieldPointer(p[1], p[4])]
    else:
        p[0] = [checkfield(p[1], p[3]), field(p[1], p[3])]
    
def p_rhs(p):
    '''rhs : boolexp
           | lhs
           | VARNAME
           | "&" VARNAME
           | NUMBER'''
    if len(p)==3:
        p[0] = [checkvar(p[2])+'*', address(p[2])]
    elif isinstance(p[1], list):
        p[0] = p[1]
    elif p[1].is_elem_type(elem_types.VAR):
        p[0] = [checkvar(p[1]), p[1]]
    else:
        p[0] = ['scalar', p[1]]

def p_var_dec(p):
    '''vardec : VARNAME SPACES list
              | VARNAME STARS SPACES list'''
    if p[1].get_display_value() not in defstructlist:
        raise Exception("Structure '" + p[1].get_display_value() + "' used without definition at line "+str(lno))
    if len(p) == 5:
        typ = p[1].get_display_value() + p[2]
        lst = p[4]
    else:
        typ = p[1].get_display_value()
        lst = p[3]
        
    global is_global_scope
    if is_global_scope:
        if global_varlist.intersection(lst):
            raise Exception("Redeclaration of global variable/s "+str(global_varlist.intersection(lst))+" at line number "+str(lno))
        for elem in lst:
            global_vardict[elem] = typ
        global_varlist.update(lst)
    else:
        if varlist.intersection(lst).union(global_varlist.intersection(lst)):
            raise Exception("Redeclaration of variable/s "+str(lst)+" at line number "+str(lno))
        for elem in lst:
            vardict[elem] = typ
        varlist.update(lst)
        
    usedstructlist.add(p[1].get_display_value())
    p[0] = { 'type': typ, 'vars': lst }

def p_stmt(p):
    '''stmt : vardec
            | lhs space "=" space rhs
            | VARNAME space "=" space rhs
            | VARNAME space "=" space MALLOC "(" ")"
            | READ SPACES VARNAME
            | USE SPACES VARNAME
            | GOTO SPACES NUMBER
            | CALL SPACES VARNAME funcargs
            | IF SPACES boolexp SPACES GOTO SPACES NUMBER
            | IF SPACES VARNAME SPACES GOTO SPACES NUMBER'''
    if len(p) == 2:
        return
    elif p[3] == '=':
        if isinstance(p[1], variable):
            p[1] = [checkvar(p[1]), p[1]]
            if len(p) == 8:
                if p[1][0][-1] != '*':
                    raise Exception("Malloc can only be called when lhs is a pointer, at line "+str(lno))
                elem = '$o'+str(lno)
                p[5] = [p[1][0], malloc(elem)]
                
                if p[1][1].get_display_value() in global_vardict:
                    global_vardict[elem] = p[1][0][:-1]
                    global_varlist.add(elem)
                else:
                    vardict[elem] = p[1][0][:-1]
                    varlist.add(elem)
        if p[1][0] != p[5][0]:
            raise Exception("Type Mismatch: LHS type - '"+p[1][0]+"', RHS type - '"+p[5][0]+"' on assignment statement at line "+str(lno))
        elif p[1][0][-1] != '*' and p[1][0] != 'scalar':
            raise Exception("Cannot use '=' for assignment of structure. Set all the fields individually. Error at line "+str(lno))
        
        p[0] = assignment(p[1][1], p[5][1], p[1][0])
    elif p[1] == 'read':
        checktype(p[3], 'scalar')
        p[0] = input(p[3])
    elif p[1] == 'use':
        typ = checkvar(p[3])
        if typ[-1] != '*':
            raise Exception("Use statement can only be called on pointers. Error at line "+str(lno))
        p[0] = use(p[3])
    elif p[1] == 'goto':
        if p[3].is_not_int():
            raise Exception("Line numbers should be integers")
        p[0] = goto(p[3])
    elif p[1] == 'call':
        p[0] = call(p[3], param_to_string(p[4][0]), p[4][1])
        usedfunclist.add(p[0].get_uid())
    else:
        if p[7].is_not_int():
            raise Exception("Line numbers should be integers")
        if p[3].is_elem_type(elem_types.VAR):
            checktype(p[3], 'scalar')
        p[0] = cond(p[3], p[7])

    global alno
    alno += 1
    statements.append(p[0])
    
def p_tac(p):
    '''tac : nl MAINCODE ":"
           | tac stmtnl stmt'''
    if p[3] == ':':
        global flno
        flno = lno + 1

def p_nl(p):
    r'nl : NEWLINE'
    global lno
    lno += p[1]
    p[0] = p[1]

def p_stmt_nl(p):
    r'stmtnl : NEWLINE'
    global lno
    lno += p[1]
    for _ in range(p[1]):
        lnomap.append(alno)

def p_funcbody(p):
    '''funcbody : stmt
                | funcbody stmtnl stmt'''
    if len(p) == 2:
        lnomap.extend([1]*(lno-flno+1))

def p_arg_list(p):
    '''arglist : VARNAME
               | arglist space "," space VARNAME'''
    if len(p) == 2:
        p[0] = [[checkvar(p[1])], [p[1]]]
    else:
        p[1][0].append(checkvar(p[5]))
        p[1][1].append(p[5])
        p[0] = p[1]

def p_func_args(p):
    '''funcargs : "(" space ")"
                | "(" space arglist space ")"'''
    if len(p) == 4:
        p[0] = [[], []]
    else:
        p[0] = p[3]

def p_param_list(p):
    '''paramlist : VARNAME SPACES VARNAME
                 | paramlist space "," space VARNAME SPACES VARNAME'''
    if len(p) == 4:
        varName = p[3].get_display_value()
        varType = p[1].get_display_value()
        p[0] = [[varType], {varName:varType}, [varName]]
    elif p[7].get_display_value() not in p[1][2]:
        varName = p[7].get_display_value()
        varType = p[5].get_display_value()
        p[1][0].append(varType)
        p[1][1][varName] = varType
        p[1][2].append(varName)
        p[0] = p[1]
    else:
        raise Exception("Same variable ("+p[7].get_display_value()+") occurs mulltiple times in Function Parameter List at line number "+str(lno))

def p_func_params(p):
    '''funcparams : "(" space ")"
                  | "(" space paramlist space ")"'''
    if len(p) == 4:
        p[0] = [[], []]
    else:
        p[0] = [p[3][0], p[3][2]]
        vardict.update(p[3][1])
        varlist.update(p[3][2])
    global flno
    flno = lno

def p_func(p):
    '''func : FUNCS ":"
            | func nl VARNAME funcparams spnl "{" spnl funcbody spnl "}"
            | func nl VARNAME funcparams spnl "{" spnl "}"'''
    if len(p) == 3:
        global is_global_scope
        is_global_scope = False   # Shift context out of global scope space into functions

    if len(p) != 3:
        func_uid = p[3].get_display_value()+param_to_string(p[4][0])
        if func_uid in deffunclist:
            raise Exception("Redeclaration of function '"+func_uid+"' at line number "+str(flno))
        deffunclist.add(func_uid)
        funcdict[func_uid] = [p[4][1], vardict.copy(), clean_statements()]
    elif usedstructlist - defstructlist:
        raise Exception("Structure/s " + str(usedstructlist - defstructlist) + " used without definition")
    prepare_next_function()

def p_space_nl(p):
    '''spnl : space
            | nl'''
    if p[1] == '':
        p[0] = 0
    else:
        p[0] = p[1]

def p_list(p):
    '''list : VARNAME space
            | list "," space VARNAME space'''
    if len(p) == 3:
        p[0] = {p[1].get_display_value()}
    else:
        p[0] = p[1]
        varName = p[4].get_display_value()
        if varName in p[0]:
            raise Exception("Duplicate variable or field "+varName+" at line number "+str(lno))
        p[0].add(varName)

def p_dec_list(p):
    '''declist : VARNAME SPACES list
               | VARNAME STARS SPACES list
               | declist nl VARNAME SPACES list
               | declist nl VARNAME STARS SPACES list'''
    if len(p) < 6:
        elemtype = p[1].get_display_value()
        elemdict = {}
        elemlist = set()
        global flno
        flno = lno
    else:
        elemtype = p[3].get_display_value()
        elemdict = p[1][0]
        elemlist = p[1][1]
    usedstructlist.add(elemtype)
    if len(p)%2 == 1:
        elemtype = elemtype + p[len(p)-3]
    elif elemtype != 'scalar':
        raise Exception("Struct fields can only be pointers or scalars, at line "+str(lno))
    elemset = p[len(p)-1]
    if elemlist.intersection(elemset):
        raise Exception("Redeclaration of variable/s or field/s "+str(elemlist.intersection(elemset))+" at line number "+str(lno))
    elemlist.update(elemset)
    for elem in elemset:
        elemdict[elem] = elemtype
    p[0] = [elemdict, elemlist]
    
def p_structs(p):
    '''structs : spnl STRT ":" nl
              | structs VARNAME space "{" spnl declist spnl "}" nl
              | structs VARNAME space "{" spnl "}" nl'''
    if len(p) == 10:
        structName = p[2].get_display_value()
        if structName in defstructlist:
            raise Exception("Redectaration of structure '"+structName+"' at line number "+str(flno - p[5]))
        structdict[structName] = p[6]
        defstructlist.add(structName)
    elif len(p) == 8:
        structName = p[2].get_display_value()
        if structName in defstructlist:
            raise Exception("Redectaration of structure '"+structName+"' at line number "+str(lno - p[5] - p[7]))
        structdict[structName] = [{}, set()]
        defstructlist.add(structName)

def p_global_sec(p):
    '''global_sec : spnl GLOBALS ":" nl
                  | global_sec vardec nl
                  | global_sec nl'''
    if len(p) > 1:
        p[0] = p[1]

def p_prog(p):
    '''prog : structs global_sec func tac spnl
            | structs func tac spnl''' 

def p_error(p):
    if p:
        raise Exception("Syntax error at line " + str(lno) +" at '" + str(p.value) + "'")
    else:
        print("Syntax error at EOF")
        raise Exception("Syntax error at EOF")


parser = yacc.yacc()

def reset():
    statements.clear()

    global flno, lno, alno
    flno = 0
    lnomap.clear()
    lno = 1
    alno = 1

    defstructlist.clear()
    defstructlist.add('scalar')
    usedstructlist.clear()
    deffunclist.clear()
    funcdict.clear()
    usedfunclist.clear()
    
    # Clears global variables and pointers when parsing a new file or text
    global_varlist.clear()
    global_vardict.clear()
    
    global is_global_scope
    is_global_scope = True

    varlist.clear()
    structdict.clear()
    structdict['scalar'] = [{},set()]

    vardict.clear()
    
def parse_file(file_name):
    try:
        f = open(file_name, 'r')
        s = f.read()
    except EOFError:
        return ("Error while loading the file", {'main' : 'error'}, {})
    
    return parse_text(s)

def parse_text(s):
    reset()
    try:
        parser.parse(s)
        parser.restart()
        funcdict['main'] = [[], vardict, clean_statements()]
    except Exception as X:
        return (str(X), {'main' : 'error'}, {})
    
    if usedfunclist - deffunclist:
        return ("Function/s " + str(usedfunclist - deffunclist) + " used without definition", {'main' : 'error'}, {})
    
    # Returns global_vardict alongside structdict and funcdict
    return (structdict, funcdict, global_vardict)


if __name__ == "__main__":
    structdict, funcdict, globalvardict = parse_file("test3.txt")
    print("structdict")
    print(structdict)
    print("globalvardict")
    print(globalvardict)
    print("Stmts")
    for key, val in funcdict.items():
        print(key)
        print(val[0])
        print(val[1])
        for stmt in val[2]:
            print("\t", stmt.get_display_stmt())