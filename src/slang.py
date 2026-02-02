"""
S-Lang: High-Level Soliton Language
====================================

A Pythonic/Rust-like DSL for topological quantum programming.

Syntax:
    program <name>:
        soliton <name> = <0|1|H>;
        <name>.roll();
        entangle(<a>, <b>);
        result = measure(<name>);
"""

from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum, auto

from .isa import Instruction, OpCode


# =============================================================================
# S-LANG AST NODES
# =============================================================================

class ASTNodeType(Enum):
    """Types of AST nodes."""
    PROGRAM = auto()
    SOLITON_DECL = auto()
    ROLL_CALL = auto()
    ENTANGLE_CALL = auto()
    MEASURE_CALL = auto()
    ASSIGNMENT = auto()


@dataclass
class ASTNode:
    """Base AST node."""
    type: ASTNodeType
    value: Any = None
    children: List["ASTNode"] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []


@dataclass 
class ProgramAST:
    """Complete S-Lang program AST."""
    name: str
    statements: List[ASTNode]
    
    def to_instructions(self) -> List[Instruction]:
        """Convert AST to G-ISA instructions."""
        instructions = []
        
        for stmt in self.statements:
            if stmt.type == ASTNodeType.SOLITON_DECL:
                name, value = stmt.value
                instructions.append(Instruction.alloc(name))
                if value == "H":
                    instructions.append(Instruction(OpCode.S_WRITE, name, ["H"]))
                elif isinstance(value, int):
                    instructions.append(Instruction.write(name, value))
            
            elif stmt.type == ASTNodeType.ROLL_CALL:
                name = stmt.value
                instructions.append(Instruction.roll(name))
            
            elif stmt.type == ASTNodeType.ENTANGLE_CALL:
                control, target = stmt.value
                instructions.append(Instruction.cnot(control, target))
            
            elif stmt.type == ASTNodeType.MEASURE_CALL:
                target, result_var = stmt.value
                instr = Instruction.measure(target)
                instr.metadata['result_var'] = result_var
                instructions.append(instr)
        
        return instructions


# =============================================================================
# S-LANG QUICK PARSER
# =============================================================================

def parse_slang(source: str) -> ProgramAST:
    """
    Quick parser for S-Lang source.
    
    Args:
        source: S-Lang source code
        
    Returns:
        ProgramAST
    """
    import re
    
    lines = source.strip().split('\n')
    program_name = "Unnamed"
    statements: List[ASTNode] = []
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue
        
        # Program declaration
        if line.startswith('program '):
            match = re.match(r'program\s+(\w+)\s*:', line)
            if match:
                program_name = match.group(1)
            continue
        
        # Soliton declaration: soliton name = value;
        if line.startswith('soliton '):
            match = re.match(r'soliton\s+(\w+)\s*=\s*(\w+)\s*;?', line)
            if match:
                name = match.group(1)
                value_str = match.group(2)
                if value_str == 'H':
                    value = 'H'
                else:
                    value = int(value_str)
                statements.append(ASTNode(
                    type=ASTNodeType.SOLITON_DECL,
                    value=(name, value)
                ))
            continue
        
        # Roll call: name.roll();
        if '.roll()' in line:
            match = re.match(r'(\w+)\.roll\(\)\s*;?', line)
            if match:
                statements.append(ASTNode(
                    type=ASTNodeType.ROLL_CALL,
                    value=match.group(1)
                ))
            continue
        
        # Entangle: entangle(a, b);
        if line.startswith('entangle('):
            match = re.match(r'entangle\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)\s*;?', line)
            if match:
                statements.append(ASTNode(
                    type=ASTNodeType.ENTANGLE_CALL,
                    value=(match.group(1), match.group(2))
                ))
            continue
        
        # Measure: result = measure(name);
        if 'measure(' in line:
            match = re.match(r'(\w+)\s*=\s*measure\s*\(\s*(\w+)\s*\)\s*;?', line)
            if match:
                statements.append(ASTNode(
                    type=ASTNodeType.MEASURE_CALL,
                    value=(match.group(2), match.group(1))
                ))
            continue
    
    return ProgramAST(name=program_name, statements=statements)


# =============================================================================
# S-LANG PROGRAM BUILDER (Fluent API)
# =============================================================================

class SolitonVar:
    """Represents a soliton variable for fluent API."""
    
    def __init__(self, name: str, program: "SLangProgram"):
        self.name = name
        self._program = program
    
    def roll(self) -> "SolitonVar":
        """Apply soliton roll (logical NOT)."""
        self._program._add_instruction(Instruction.roll(self.name))
        return self
    
    def measure(self) -> "SolitonVar":
        """Measure this soliton."""
        self._program._add_instruction(Instruction.measure(self.name))
        return self


class SLangProgram:
    """
    Fluent API for building S-Lang programs in Python.
    
    Example:
        >>> prog = SLangProgram("Bell")
        >>> a = prog.soliton("alpha", "H")
        >>> b = prog.soliton("beta", 0)
        >>> prog.entangle(a, b)
        >>> a.measure()
        >>> b.measure()
        >>> circuit = prog.compile()
    """
    
    def __init__(self, name: str = "Program"):
        self.name = name
        self._instructions: List[Instruction] = []
        self._solitons: Dict[str, SolitonVar] = {}
    
    def soliton(self, name: str, value: int | str = 0) -> SolitonVar:
        """
        Declare a soliton variable.
        
        Args:
            name: Variable name
            value: Initial value (0, 1, or "H" for superposition)
            
        Returns:
            SolitonVar for method chaining
        """
        self._add_instruction(Instruction.alloc(name))
        
        if value == "H":
            self._add_instruction(Instruction(OpCode.S_WRITE, name, ["H"]))
        elif isinstance(value, int):
            self._add_instruction(Instruction.write(name, value))
        
        var = SolitonVar(name, self)
        self._solitons[name] = var
        return var
    
    def entangle(self, control: SolitonVar, target: SolitonVar) -> "SLangProgram":
        """
        Entangle two solitons (topological CNOT).
        
        Args:
            control: Control soliton
            target: Target soliton
            
        Returns:
            Self for chaining
        """
        self._add_instruction(Instruction.cnot(control.name, target.name))
        return self
    
    def measure(self, soliton: SolitonVar, result_var: str = None) -> "SLangProgram":
        """
        Measure a soliton.
        
        Args:
            soliton: Soliton to measure
            result_var: Optional result variable name
            
        Returns:
            Self for chaining
        """
        instr = Instruction.measure(soliton.name)
        if result_var:
            instr.metadata['result_var'] = result_var
        self._add_instruction(instr)
        return self
    
    def _add_instruction(self, instr: Instruction):
        self._instructions.append(instr)
    
    def get_instructions(self) -> List[Instruction]:
        """Get all generated instructions."""
        return self._instructions.copy()
    
    def compile(self, complexity: int = 6):
        """
        Compile to quantum circuit.
        
        Args:
            complexity: Braid complexity
            
        Returns:
            QuantumCircuit
        """
        from .compiler import CircuitCompiler
        
        cc = CircuitCompiler(complexity=complexity)
        circuit = cc.compile(self._instructions)
        circuit.name = self.name
        return circuit
    
    def to_slang(self) -> str:
        """Convert to S-Lang source code."""
        lines = [f"program {self.name}:"]
        
        for instr in self._instructions:
            if instr.opcode == OpCode.S_ALLOC:
                # Find the following WRITE to get the value
                continue
            elif instr.opcode == OpCode.S_WRITE:
                value = instr.operands[0]
                lines.append(f"    soliton {instr.target} = {value};")
            elif instr.opcode == OpCode.S_ROLL:
                lines.append(f"    {instr.target}.roll();")
            elif instr.opcode == OpCode.S_CNOT:
                control = instr.operands[0]
                lines.append(f"    entangle({control}, {instr.target});")
            elif instr.opcode == OpCode.S_MEASURE:
                result_var = instr.metadata.get('result_var', 'result')
                lines.append(f"    {result_var} = measure({instr.target});")
        
        return '\n'.join(lines)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def compile_from_source(source: str, complexity: int = 6):
    """
    Compile S-Lang source to quantum circuit.
    
    Args:
        source: S-Lang source code
        complexity: Braid complexity
        
    Returns:
        QuantumCircuit
    """
    from .compiler import GambitCompiler
    
    compiler = GambitCompiler(complexity=complexity)
    _, circuit = compiler.compile_source(source)
    return circuit


def quick_bell_state():
    """
    Create a Bell state program.
    
    Returns:
        Compiled QuantumCircuit for |00⟩ + |11⟩
    """
    prog = SLangProgram("BellState")
    alpha = prog.soliton("alpha", "H")
    beta = prog.soliton("beta", 0)
    prog.entangle(alpha, beta)
    alpha.measure()
    beta.measure()
    return prog.compile()


def quick_soliton_roll():
    """
    Create a soliton roll (NOT gate) program.
    
    Returns:
        Compiled QuantumCircuit demonstrating logical NOT
    """
    prog = SLangProgram("SolitonRoll")
    q = prog.soliton("q", 0)
    q.roll()
    q.measure()
    return prog.compile()
