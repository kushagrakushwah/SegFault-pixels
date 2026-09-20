# PTA-Viz

**An Interactive Visualization Tool for Flow-Sensitive, Context-Sensitive Pointer Analysis**

Built for SegFault 2026 | IISc Bengaluru Finale | Track: Explainable compilers

---

## What is PTA-Viz?

Pointer analysis sits at the heart of every modern compiler optimizer and static analysis tool, yet it is entirely invisible to developers. When a compiler concludes that two pointers do not alias, a developer has no way to see *why* — which algorithm was used, how it propagated, or where it over-approximated.

**PTA-Viz is an interactive IDE for pointer analysis.** It accepts programs in a structured C-like intermediate language, runs four distinct pointer analysis algorithms, and produces rich step-by-step visual explanations of every analytical decision the algorithm makes.

---

## Four Algorithms

| Algorithm | Precision | What PTA-Viz Shows |
|---|---|---|
| **Andersen's** | Flow-Insensitive, Context-Insensitive | Growing inclusion-constraint sets, iteration-by-iteration graph evolution |
| **Steensgaard's** | Flow-Insensitive, Context-Insensitive | Union-Find equivalence classes being merged; final graph |
| **FS-PTA** | Flow-Sensitive, Context-Insensitive | Per-statement IN/OUT pointer graphs, fixed-point convergence |
| **VASCO** | Flow-Sensitive, Context-Sensitive | Value-sensitive context cloning, memoization cache, recursion guard |

---

## Installation

### 1. Install Python dependencies

```bash
pip install ply PyQt6 graphviz
```

### 2. Install the Graphviz application

Download and install from https://graphviz.org/download/

> Make sure dot is on your system PATH after installation.

---

## Running PTA-Viz

### GUI (recommended)

```bash
python gui.py
```

A 1800×950 window will appear with:
- **Left** — Code editor with line numbers, file open/save, font zoom, and algorithm selector buttons
- **Middle** — Control-flow graph (clickable nodes)
- **Right** — Results panel (switches based on selected algorithm)

### Command-line (backend only)

```bash
python main.py <path_to_program>
# or
python main.py          # uses test.txt
```

Results are written to ./results/ with one subdirectory per algorithm.

---

## Input Language Reference

Programs are written in a structured C-like intermediate language parsed by a custom PLY-based scanner/parser.

### Overall structure

```text
structs:
<struct declarations>

globals:
<global pointer declarations>

funcs:
<function definitions>

main:
<statements>
```

### Struct declarations

```text
structs:
Node{scalar x
    Node* next
}
```

### Global variables

```text
globals:
Node* g
scalar* ptr
```

### Function definitions

> **Important:** No space between function name and (. Parameters are scalar-typed only.

```text
funcs:
myFunc(scalar x, scalar y) {
scalar* p
p = malloc()
}
```

### Statements (in function bodies and main)

| Syntax | Meaning |
|---|---|
| Type* p | Declare pointer p |
| p = malloc() | Heap allocate; p must be a pointer |
| p = &x | Address-of |
| p = q | Pointer copy |
| *p = q | Store through pointer |
| p = *q | Load through pointer |
| p->field = q | Store to struct field pointer |
| p = q->field | Load struct field pointer |
| use p | Mark pointer as used (liveness) |
| call f(a, b) | Call function |
| if a < b goto N | Conditional branch to statement N |
| goto N | Unconditional branch |
| read x | Read scalar input |

### Example programs

See the examples/ directory:

| File | Demonstrates |
|---|---|
| 01_simple_alias.txt | Basic aliasing; ideal for Andersen's/Steensgaard's |
| 02_flow_sensitive.txt | Precision gain from flow-sensitivity |
| 03_interprocedural_global.txt | Global pointer flows across functions (VASCO) |
| 04_linked_list.txt | Struct field pointer analysis |
| 05_context_sensitivity.txt | Context sensitivity: two calls to same function |

---

## Using the GUI

1. **Write or open a program** in the left editor panel.
2. **Click Analyze** — all five analyses run and results are saved to ./results/.
3. **Select an algorithm** using the buttons (Andersen's / Steensgaard's / FS-PTA / VASCO / LFCPA).
4. **Click CFG nodes** in the middle panel — the results panel updates to show the PTA state at that statement.
5. **Step through iterations** using the Iteration spinner.

---

## Architecture

```text
PTA-Viz
├── scanner.py          — PLY lexer for the PTA-Viz IL
├── parser.py           — PLY Yacc parser; produces struct_dict, func_dict, global_vardict
├── stmt_helper.py      — AST node classes (statements, elements, types)
├── pta_helper.py       — Shared analysis utilities (CFG construction, set_pin, set_pout)
├── helper.py           — Graphviz rendering and JSON I/O utilities
│
├── fi_pta.py           — Andersen's + Steensgaard's (Flow-Insensitive)
├── fs_pta.py           — FS-PTA (Flow-Sensitive, Context-Insensitive)
├── lfcpa.py            — LFCPA (Liveness-Filtered Context PTA)
├── vasco_pta.py        — VASCO (Flow-Sensitive, Context-Sensitive)
│
├── main.py             — Backend driver: runs all 5 analyses and writes results/
│
├── gui.py              — Main window (algorithm switcher, splitter layout)
├── gui_editor.py       — Code editor panel + algorithm buttons
├── gui_imageViewer.py  — All result widgets (per-algorithm viewers)
├── guiHelper.py        — Qt widget wrappers (QPushButton, QSpinBox, QSplitter...)
│
├── examples/           — 5 annotated example programs
└── results/            — Analysis output (auto-created by Analyze)
    ├── andersens/      — code.svg, info.json, pta/iter_N.json, pta/final.svg
    ├── steensgaards/   — code.svg, info.json, pta/final.svg
    ├── fspta/          — code.svg, info.json, pta/iter_Xstmt_Y_{in,out}.json
    ├── vasco/          — code.svg, info.json, context_log.json, pta/iter_Xstmt_Y_out.json
    └── lfcpa/          — code.svg, info.json, pta/..., la/...
```

---

## Key Technical Contributions

### 1. Global Variable Support
We extended the language (adding a globals: section) and all five analysis engines to handle globally shared pointer state across function boundaries. Global variables bypass name mangling in the VASCO engine, ensuring they correctly refer to the same allocation across all function contexts.

### 2. VASCO Context-Sensitivity Visualization
No existing open-source tool visualizes Flow-Sensitive Context-Sensitive analysis step-by-step. VASCO's startedAnalysis / completedAnalysis memoization dictionaries guarantee termination even under recursion. The GUI exposes the full context log, showing which function contexts were created, which were memoized, and which triggered the recursion guard.

### 3. Bugs Fixed in VASCO Engine
- **Bug 1 (Method Typo):** stmt.is_is_stmt_type() → stmt.is_stmt_type()
- **Bug 2 (Argument Extraction):** Malformed stmt. replaced with [arg.varName for arg in stmt.args]
- **Bug 3 (Memoization Index):** del + pop(sa_ind) double-removal replaced with pop(sa_ind) once
- **Bug 4 (CFG Mismatch):** get_updated_func_dict was building stmt list from unfiltered stmts but successors/predecessors from filtered stmts — causing index mismatches
- **Bug 5 (Global Mangling):** Global variable names in new_var_dict were mangled with function ID — now globals retain their original names

---

## Team

| Name | Email | Institute |
|---|---|---|
| Kushagra Singh Kushwah | kushagrasinghkushwah46@gmail.com | VNIT Nagpur |
| Raj Patil | rajpatil280906@gmail.com | VNIT Nagpur |
| Kartik Agrawal | kartikagrawalvnit@gmail.com | VNIT Nagpur |

SegFault 2026 · Compiler Frameworks and Tools · IISc Bengaluru Finale
