import ply.lex as lex
from stmt_helper import *
# from ply.lex import TOKEN

# Tokens
# Updated the reserved dictionary
reserved  = {
    'if' : 'IF',
    'goto' : 'GOTO',
    'read' : 'READ',
    'use' : 'USE',
    'structs' : 'STRT',
    'funcs' : 'FUNCS',
    'main' : 'MAINCODE',
    'call' : 'CALL',
    'malloc' : 'MALLOC',
    'globals' : 'GLOBALS'  #  ADDED THIS LINE
}
tokens = ['VARNAME', 'NUMBER', 'SPACES', 'NEWLINE', 'LTE', 'GTE', 'STARS'] + list(reserved.values())

literals = ['=', '!', '&', '<', '>', '{', '}', '-', '.', ':', ',', '[', ']', '(', ')']

# t_VARNAME = r'[a-zA-Z]+'
# t_TMPVARNAME = r't[0-9]+'
# t_ignore = r'#'

# comment = r'\/\/[^\n]*\n'
# nl_c = r'([\s\t]+)?(\/\/[^\n]*)?\n[\s\t\n'+comment+r']*'

lno = 1

def t_STARS(t):
    r'\*+'
    return t

def t_VARNAME(t):
    r'[a-zA-Z][a-zA-Z0-9]*'
    t.type = reserved.get(t.value,'VARNAME')
    if t.type == 'VARNAME':
        t.value = variable(str(t.value))
    return t

def t_NUMBER(t):
    r'\d+(\.[\d]+)?'
    t.value = number(float(t.value))
    return t

def t_NEWLINE(t):
    r'[\s\t]*(//[^\n]*)?\n(\s | \t | \n | //[^\n]*\n)*'
    t.value = t.value.count("\n")
    global lno
    lno += t.value
    return t

def t_SPACES(t):
    r'[\s\t]+'
    return t

t_LTE = r'<='
t_GTE = r'>='

def t_error(t):
    raise Exception("Illegal character '"+ str(t.value[0])+ "', at line number "+ str(lno))
    # print("Illegal character '%s'" % t.value[0])
    # t.lexer.skip(1)

# Build the lexer
lexer = lex.lex()