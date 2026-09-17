class elem_types:
    VAR = 1
    NUM = 2
    BEX = 3
    PTR = 4
    FLD = 5
    FLP = 6
    ADR = 7
    MAL = 8

class stmt_types:
    ASG = 1
    INP = 2
    USE = 3
    GOT = 4
    CAL = 5
    IF = 6
    
class stmt:
    def __init__(self) -> None:
        self.stmtType = -1

    def get_display_stmt(self) -> str:
        return "Default statemet class"

    def is_stmt_type(self, stmtType:int) -> bool:
        return stmtType == self.stmtType
    
    def add_funcID(self, id:str) -> None:
        print("Called add_funcID from the base class")


class elem:
    def __init__(self) -> None:
        self.elemType = -1

    def get_display_value(self) -> str:
        return "[Default display Value]"
    
    def is_elem_type(self, elemType:int) -> bool:
        return elemType == self.elemType
    
    def elem_type(self) -> int:
        return self.elemType
    
    def add_funcID(self, id:str) -> None:
        print("Called add_funcID from the base class")

class number(elem):
    def __init__(self, num:float) -> None:
        self.value = num
        self.elemType = elem_types.NUM
        self.not_int = num != int(num)
        if not self.not_int:
            self.value = int(self.value)

    def get_display_value(self) -> str:
        return str(self.value)
    
    def get_number(self) -> float|int:
        return self.value
    
    def is_not_int(self) -> bool:
        return self.not_int
    
    def add_funcID(self, id:str) -> None:
        pass

# Updated the variable class
class variable(elem):
    def __init__(self, varName:str) -> None:
        self.varName = varName
        self.elemType = elem_types.VAR
        self.is_global = False # ADDED THIS FLAG TO IDENTIFY GLOBAL VARIABLES
        
    def get_display_value(self) -> str:
        return self.varName
    
    def add_funcID(self, id:str) -> None:
        #  UPDATED TO PREVENT MANGLING GLOBALS
        if not getattr(self, 'is_global', False): 
            self.varName = self.varName+id

#TODO
class boolExp(elem):
    def __init__(self, var1:variable|number, var2:variable|number, op:str) -> None:
        self.var1 = var1
        self.var2 = var2
        self.op = op
        self.elemType = elem_types.BEX
        
    def get_display_value(self) -> str:
        return self.var1.get_display_value()+' '+self.op+' '+self.var2.get_display_value()
    
    def add_funcID(self, id:str) -> None:
        self.var1.add_funcID(id)
        self.var2.add_funcID(id)

class pointer(variable):
    def __init__(self, var:variable) -> None:
        variable.__init__(self, var.varName)
        self.elemType = elem_types.PTR
        self.is_global = getattr(var, 'is_global', False) # ADDED THIS FLAG
        
    def get_display_value(self) -> str:
        return '*'+self.varName

class field(variable):
    def __init__(self, var:variable, fld:variable) -> None:
        variable.__init__(self, var.varName)
        self.fld = fld.varName
        self.elemType = elem_types.FLD
        self.is_global = getattr(var, 'is_global', False) # ADDED THIS FLAG
        
    def get_display_value(self) -> str:
        return self.varName+'.'+self.fld

class fieldPointer(field):
    def __init__(self, var:variable, fld:variable) -> None:
        field.__init__(self, var, fld)
        self.elemType = elem_types.FLP
        
    def get_display_value(self) -> str:
        return self.varName+'->'+self.fld

class address(variable):
    def __init__(self, var:variable) -> None:
        variable.__init__(self, var.varName)
        self.elemType = elem_types.ADR
        self.is_global = getattr(var, 'is_global', False) # ADDED THIS FLAG
        
    def get_display_value(self) -> str:
        return '&'+self.varName

class malloc(variable):
    def __init__(self, varName:str) -> None:
        variable.__init__(self, varName)
        self.elemType = elem_types.MAL

    def get_display_value(self) -> str:
        return 'malloc('+self.varName+')'

# Statement CLasses: -----------------------------------------------------------------------
class plain_text(stmt):
    def __init__(self, txt:str) -> None:
        self.txt = txt
        self.stmtType = -1

    def get_display_stmt(self) -> str:
        return self.txt
    
    def add_funcID(self, id:str) -> None:
        pass

class assignment(stmt):
    def __init__(self, lhs:elem, rhs:elem, type:str) -> None:
        self.lhs = lhs
        self.rhs = rhs
        self.type = type
        self.containsPointer = False
        self.stmtType = stmt_types.ASG

    def get_lhs(self) -> elem:
        return self.lhs

    def get_rhs(self) -> elem:
        return self.rhs

    def get_display_stmt(self) -> str:
        return (self.lhs.get_display_value()+' = '+self.rhs.get_display_value())
    
    def get_type(self) -> str:
        return self.type
    
    def add_funcID(self, id:str) -> None:
        self.lhs.add_funcID(id)
        self.rhs.add_funcID(id)

class input(stmt):
    def __init__(self, var:variable) -> None:
        self.var = var
        self.stmtType = stmt_types.INP

    def get_display_stmt(self) -> str:
        return ('read '+self.var.get_display_value())
    
    def add_funcID(self, id:str) -> None:
        self.var.add_funcID(id)

class use(stmt):
    def __init__(self, var:variable) -> None:
        self.varName = var.varName
        self.stmtType = stmt_types.USE
        self.is_global = getattr(var, 'is_global', False) # ADDED THIS FLAG

    def get_display_stmt(self) -> str:
        return ('use '+self.varName)
    
    def add_funcID(self, id:str) -> None:
        # Only mangle non-global variables
        if not getattr(self, 'is_global', False):
            self.varName = self.varName+id

class goto(stmt):
    def __init__(self, lno:number) -> None:
        self.lno = int(lno.get_number())
        self.stmtType = stmt_types.GOT

    def get_display_stmt(self) -> str:
        return ('goto '+str(self.lno))

    def get_lno(self) -> int:
        return self.lno
    
    def set_lno(self, lno:int) -> None:
        self.lno = lno
    
    def add_funcID(self, id:str) -> None:
        pass

class call(stmt):
    def __init__(self, funcName:variable, input_params:str, args:list[variable]) -> None:
        self.funcName = funcName.get_display_value()
        self.input_params = input_params
        self.args = args
        self.stmtType = stmt_types.CAL

    def get_display_args(self) -> str:
        args = '('
        if len(self.args)>0:
            args += self.args[0].get_display_value()
        for arg in self.args[1:]:
            args += ', '+arg.get_display_value()

        return args+')'

    def get_display_stmt(self) -> str:
        return ('call '+self.funcName+self.get_display_args())

    def get_uid(self) -> str:
        return self.funcName+self.input_params
    
    def add_funcID(self, id:str) -> None:
        for arg in self.args:
            arg.add_funcID(id)

class cond(stmt):
    def __init__(self, condition:variable|boolExp, lno:number) -> None:
        self.cond = condition
        self.lno = int(lno.get_number())
        self.stmtType = stmt_types.IF

    def get_display_stmt(self) -> str:
        return ('if '+self.cond.get_display_value()+' goto '+str(self.lno))

    def get_lno(self) -> int:
        return self.lno
    
    def set_lno(self, lno:int) -> None:
        self.lno = lno
    
    def add_funcID(self, id:str) -> None:
        self.cond.add_funcID(id)
