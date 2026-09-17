"""
c_to_ir.py  —  C Subset to PTA-Viz Intermediate Language Converter
==================================================================
Converts common C pointer patterns into PTA-Viz IR for analysis.

Supported:
  * Struct definitions with pointer fields
  * Global pointer / scalar declarations
  * Function definitions (pointer params become scalar in IR)
  * Assignments: p=q  p=&x  p=*q  *p=q  p->f=q  p=q->f
  * malloc / calloc / realloc  (sizeof arg stripped)
  * Function calls (return values: use globals for inter-func data flow)
  * if/else, while, for  (converted to sequential IR; goto TBD)

PTA-Viz grammar constraints reflected:
  * No space between function name and '('
  * Pointer-typed params not supported -> converted to scalar
  * malloc() takes no arguments in IR
  * No return values in IR -> use global variables

Usage:
  python c_to_ir.py input.c [output.txt]
"""

import re, sys, os

# Types that map to 'scalar' in PTA-Viz
SCALAR_TYPES = {
    'int','long','short','char','float','double','void',
    'unsigned','signed','bool','_Bool','size_t','ssize_t',
    'uint8_t','uint16_t','uint32_t','uint64_t',
    'int8_t','int16_t','int32_t','int64_t',
    'ptrdiff_t','intptr_t','uintptr_t','FILE',
}

SKIP_FUNCS = {'printf','fprintf','sprintf','scanf','puts','putchar',
              'fopen','fclose','fread','fwrite','exit','abort',
              'assert','free','memset','memcpy','strlen','sizeof',
              'offsetof'}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_struct(t):
    return re.sub(r'\bstruct\b\s*', '', t).strip()

def _norm_type(base, typedefs):
    b = _strip_struct(base).strip()
    b = typedefs.get(b, b)
    return 'scalar' if b in SCALAR_TYPES else b

def _pta_type(base, is_ptr, typedefs):
    return _norm_type(base, typedefs) + ('*' if is_ptr else '')

def _clean_args(args_str):
    parts = [a.strip() for a in args_str.split(',')]
    return ', '.join(a for a in parts if re.match(r'^\w+$', a))

def find_close_brace(code, open_pos):
    depth, i = 0, open_pos
    while i < len(code):
        if code[i] == '{': depth += 1
        elif code[i] == '}':
            depth -= 1
            if depth == 0: return i
        i += 1
    return len(code)


# ── Preprocessor ─────────────────────────────────────────────────────────────

def preprocess(code):
    code = re.sub(r'/\*.*?\*/', ' ', code, flags=re.DOTALL)
    code = re.sub(r'//[^\n]*', '', code)
    code = re.sub(r'^\s*#[^\n]*', '', code, flags=re.MULTILINE)
    code = code.replace('NULL', '0').replace('nullptr', '0').replace('true','1').replace('false','0')
    return code


# ── Struct parser ─────────────────────────────────────────────────────────────

def parse_structs(code, typedefs):
    structs = {}

    def extract_ptr_fields(body):
        fields = []
        for line in body.splitlines():
            line = line.strip().rstrip(';')
            m = re.match(r'^(?:struct\s+)?(\w+)\s*\*+\s*(\w+)$', line)
            if m:
                ftype = _norm_type(m.group(1), typedefs)
                fields.append((m.group(2), ftype))
        return fields

    # struct Name { ... }
    for m in re.finditer(r'\bstruct\s+(\w+)\s*\{', code):
        name = m.group(1)
        close = find_close_brace(code, m.end() - 1)
        body = code[m.end():close]
        structs[name] = extract_ptr_fields(body)
        typedefs.setdefault(name, name)

    # typedef struct { ... } Alias;
    for m in re.finditer(r'\btypedef\s+struct\s*\w*\s*\{', code):
        brace_pos = code.index('{', m.start())
        close = find_close_brace(code, brace_pos)
        body = code[brace_pos+1:close]
        alias_m = re.match(r'\s*(\w+)\s*;', code[close+1:close+40])
        if alias_m:
            alias = alias_m.group(1)
            structs[alias] = extract_ptr_fields(body)
            typedefs[alias] = alias

    # typedef struct Name Alias;
    for m in re.finditer(r'\btypedef\s+struct\s+(\w+)\s+(\w+)\s*;', code):
        typedefs[m.group(2)] = m.group(1)

    return structs


# ── Global declarations ───────────────────────────────────────────────────────

def parse_globals(code, typedefs, func_names):
    # Strip function bodies to avoid picking up locals
    stripped = code
    for _ in range(5):
        stripped = re.sub(r'\{[^{}]*\}', '{}', stripped)

    result, seen = [], set()
    for m in re.finditer(
        r'^(?:extern\s+|static\s+)?(?:struct\s+)?(\w+)\s*(\*+)\s*(\w+)\s*(?:=[^;]*)?\s*;',
        stripped, re.MULTILINE
    ):
        base, stars, name = m.group(1), m.group(2), m.group(3)
        if base in ('return','typedef','if','while','for','else','goto','break','do'):
            continue
        if name in func_names or name in seen:
            continue
        seen.add(name)
        result.append((name, _pta_type(base, True, typedefs)))
    return result


# ── Body converter ────────────────────────────────────────────────────────────

class BodyConverter:
    def __init__(self, typedefs, known_structs, lbl_counter=None):
        self.td = typedefs
        self.ks = known_structs
        self.lbl = lbl_counter or [0]
        self.var_decls = []
        self.stmts = []

    def _decl_exists(self, name):
        return any(d.split()[-1] == name for d in self.var_decls)

    def convert(self, lines):
        # Pre-expand semicolons so each statement is one line
        expanded = []
        for l in lines:
            for part in l.split(';'):
                p = part.strip()
                if p:
                    expanded.append(p)
        i = 0
        while i < len(expanded):
            i = self._proc(expanded, i)

    def _proc(self, lines, i):
        raw = lines[i].strip()
        if not raw or raw in ('{', '}'):
            return i + 1

        # return expr — only emit 'use' for named pointer vars, ignore 'return 0'
        if raw.startswith('return'):
            m = re.match(r'^return\s+(\w+)$', raw)
            if m and m.group(1) not in ('0', '1', 'NULL', 'null'):
                self.stmts.append('use ' + m.group(1))
            return i + 1

        # ── Declarations ────────────────────────────────────────────────────

        # Type* name [= init]
        m = re.match(r'^(?:struct\s+)?(\w+)\s*\*+\s+(\w+)\s*(?:=\s*(.+))?$', raw)
        if m and m.group(1) not in ('return','if','else','while','for','goto','break','do','typedef'):
            base, name, init = m.group(1), m.group(2), m.group(3)
            t = _pta_type(base, True, self.td)
            if not self._decl_exists(name):
                self.var_decls.append(t + ' ' + name)
            if init:
                self.stmts.extend(self._init(name, init.strip()))
            return i + 1

        # Type name [= init]  — scalar or struct-by-value
        m = re.match(r'^(?:struct\s+)?(\w+)\s+(\w+)\s*(?:=\s*(.+))?$', raw)
        if m and m.group(1) not in ('return','if','else','while','for','goto','break','do','typedef','struct'):
            base, name, init = m.group(1), m.group(2), m.group(3)
            t = _pta_type(base, False, self.td)
            if not self._decl_exists(name):
                self.var_decls.append(t + ' ' + name)
            if init:
                self.stmts.extend(self._init(name, init.strip()))
            return i + 1

        # ── Assignment forms ────────────────────────────────────────────────

        # malloc — use greedy .* to handle nested parens: malloc(sizeof(struct T))
        m = re.match(r'^(\w+)\s*=\s*(?:\([^)]*\)\s*)?(?:malloc|calloc|realloc)\s*\(.*\)$', raw)
        if m:
            self.stmts.append(m.group(1) + ' = malloc()')
            return i + 1

        # a->f = b
        m = re.match(r'^(\w+)->(\w+)\s*=\s*(\w+)$', raw)
        if m:
            self.stmts.append(f'{m.group(1)}->{m.group(2)} = {m.group(3)}')
            return i + 1

        # a = b->f
        m = re.match(r'^(\w+)\s*=\s*(\w+)->(\w+)$', raw)
        if m:
            self.stmts.append(f'{m.group(1)} = {m.group(2)}->{m.group(3)}')
            return i + 1

        # *a = b
        m = re.match(r'^\*(\w+)\s*=\s*(\w+)$', raw)
        if m:
            self.stmts.append(f'*{m.group(1)} = {m.group(2)}')
            return i + 1

        # a = *b
        m = re.match(r'^(\w+)\s*=\s*\*(\w+)$', raw)
        if m:
            self.stmts.append(f'{m.group(1)} = *{m.group(2)}')
            return i + 1

        # a = &b
        m = re.match(r'^(\w+)\s*=\s*&(\w+)$', raw)
        if m:
            self.stmts.append(f'{m.group(1)} = &{m.group(2)}')
            return i + 1

        # a = func(args)
        m = re.match(r'^(\w+)\s*=\s*(\w+)\s*\(([^)]*)\)$', raw)
        if m:
            lhs, func, args = m.group(1), m.group(2), m.group(3)
            if func not in SKIP_FUNCS:
                self.stmts.append(f'call {func}(' + _clean_args(args) + ')')
            return i + 1

        # func(args)
        m = re.match(r'^(\w+)\s*\(([^)]*)\)$', raw)
        if m:
            func, args = m.group(1), m.group(2)
            if func not in SKIP_FUNCS:
                self.stmts.append(f'call {func}(' + _clean_args(args) + ')')
            return i + 1

        # a = b
        m = re.match(r'^(\w+)\s*=\s*(\w+)$', raw)
        if m:
            self.stmts.append(f'{m.group(1)} = {m.group(2)}')
            return i + 1

        # if (...) — eat body and convert
        m = re.match(r'^if\s*\((.+)\)$', raw)
        if m:
            then_lines, else_lines, i2 = self._eat_if(lines, i + 1)
            sub = BodyConverter(self.td, self.ks, self.lbl)
            sub.convert(then_lines)
            sub2 = BodyConverter(self.td, self.ks, self.lbl)
            sub2.convert(else_lines)
            self.var_decls.extend(sub.var_decls + sub2.var_decls)
            self.stmts.extend(sub.stmts + sub2.stmts)
            return i2

        # while / for — eat body
        if re.match(r'^(?:while|for)\s*\(', raw):
            body_lines, i2 = self._eat_block(lines, i + 1)
            sub = BodyConverter(self.td, self.ks, self.lbl)
            sub.convert(body_lines)
            self.var_decls.extend(sub.var_decls)
            self.stmts.extend(sub.stmts)
            return i2

        return i + 1

    def _init(self, lhs, init):
        if not init or init in ('0', 'NULL', 'nullptr'):
            return []
        # malloc / calloc / realloc with any arg (including nested sizeof)
        if re.search(r'\b(malloc|calloc|realloc)\b', init):
            return [lhs + ' = malloc()']
        m = re.match(r'^&(\w+)$', init)
        if m: return [f'{lhs} = &{m.group(1)}']
        m = re.match(r'^\*(\w+)$', init)
        if m: return [f'{lhs} = *{m.group(1)}']
        m = re.match(r'^(\w+)->(\w+)$', init)
        if m: return [f'{lhs} = {m.group(1)}->{m.group(2)}']
        m = re.match(r'^(?:\([^)]*\)\s*)?(\w+)\s*\(([^)]*)\)$', init)
        if m and m.group(1) not in SKIP_FUNCS:
            return [f'call {m.group(1)}(' + _clean_args(m.group(2)) + ')']
        m = re.match(r'^(\w+)$', init)
        if m: return [f'{lhs} = {m.group(1)}']
        return []

    def _eat_block(self, lines, i):
        if i >= len(lines): return [], i
        if '{' in lines[i]:
            depth, j, collected = 0, i, []
            while j < len(lines):
                if '{' in lines[j]: depth += lines[j].count('{')
                if '}' in lines[j]:
                    depth -= lines[j].count('}')
                    if depth <= 0: return collected, j + 1
                if depth > 0: collected.append(lines[j])
                j += 1
            return collected, j
        else:
            return [lines[i]], i + 1

    def _eat_if(self, lines, i):
        then_lines, i2 = self._eat_block(lines, i)
        else_lines = []
        if i2 < len(lines) and re.match(r'^\s*else\b', lines[i2]):
            rest = re.sub(r'^\s*else\s*', '', lines[i2]).strip()
            if not rest or rest == '{':
                else_lines, i2 = self._eat_block(lines, i2 + 1 if not rest else i2)
            else:
                else_lines = [rest]
                i2 += 1
        return then_lines, else_lines, i2


# ── Function parser ───────────────────────────────────────────────────────────

def parse_functions(code, typedefs, known_structs, global_names):
    functions = {}
    main_decls, main_stmts = [], []

    FUNC_RE = re.compile(
        r'(?:static\s+|extern\s+|inline\s+)*'
        r'(?:struct\s+)?(\w+)\s*\*?\s*(\w+)\s*\(([^)]*)\)\s*\{',
        re.MULTILINE
    )
    lbl = [0]

    for m in FUNC_RE.finditer(code):
        ret_base, fname, params_raw = m.group(1), m.group(2), m.group(3)
        if ret_base in ('typedef','else','do','return','struct','enum','union','if','while','for','switch'):
            continue
        if fname in ('if','else','while','for','switch','return'):
            continue

        body_start = m.end()
        body_end = find_close_brace(code, body_start - 1)
        body = code[body_start:body_end]

        # Parse params — all become scalar (PTA-Viz grammar limitation)
        params = []
        if params_raw.strip() and params_raw.strip() != 'void':
            for p in params_raw.split(','):
                p = p.strip()
                pm = re.match(r'^(?:struct\s+)?(\w+)\s*\*?\s*(\w+)$', p)
                if pm:
                    params.append((pm.group(2), 'scalar'))

        param_names = {p[0] for p in params}

        conv = BodyConverter(typedefs, known_structs, lbl)
        # Split on semicolons to get individual statements
        lines = [s.strip() for s in re.split(r';|\n', body) if s.strip()]
        conv.convert(lines)

        decls = [d for d in conv.var_decls if d.split()[-1] not in param_names]

        if fname == 'main':
            main_decls, main_stmts = decls, conv.stmts
        else:
            functions[fname] = (params, decls, conv.stmts)

    return functions, main_decls, main_stmts


# ── IR Generator ─────────────────────────────────────────────────────────────

def generate_ir(structs, globals_list, functions, main_decls, main_stmts):
    out = []

    out.append('structs:')
    for sname, fields in structs.items():
        if fields:
            out.append(f'{sname}{{')
            for fname, ftype in fields:
                out.append(f'{ftype}* {fname}')
            out.append('}')

    out.append('\nglobals:')
    for gname, gtype in globals_list:
        out.append(f'{gtype} {gname}')

    out.append('\nfuncs:')
    for fname, (params, decls, stmts) in functions.items():
        param_str = ', '.join(f'{t} {n}' for n, t in params)
        out.append(f'{fname}({param_str}) {{')
        for d in decls: out.append(d)
        for s in stmts: out.append(s)
        out.append('}')

    out.append('\nmain:')
    for d in main_decls: out.append(d)
    for s in main_stmts: out.append(s)

    return '\n'.join(out) + '\n'


# ── Public API ────────────────────────────────────────────────────────────────

def convert_c_to_ir(c_code):
    """Convert C source code string to PTA-Viz IR string."""
    code = preprocess(c_code)
    typedefs = {}
    structs = parse_structs(code, typedefs)
    known_structs = set(structs.keys())

    func_names = set(re.findall(r'\b(\w+)\s*\([^;{(]*\)\s*\{', code))
    globals_list = parse_globals(code, typedefs, func_names)

    functions, main_decls, main_stmts = parse_functions(
        code, typedefs, known_structs, {g[0] for g in globals_list}
    )

    return generate_ir(structs, globals_list, functions, main_decls, main_stmts)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python c_to_ir.py input.c [output.txt]')
        print()
        print('Converts C pointer programs to PTA-Viz Intermediate Language.')
        sys.exit(1)

    inp  = sys.argv[1]
    base = os.path.splitext(inp)[0]
    out  = sys.argv[2] if len(sys.argv) > 2 else base + '_ir.txt'

    with open(inp) as f:
        c_code = f.read()

    ir = convert_c_to_ir(c_code)

    with open(out, 'w', newline='\n') as f:
        f.write(ir)

    print(f'Converted: {inp}  ->  {out}')
    print()
    print('-' * 50)
    print(ir)
    print('-' * 50)
