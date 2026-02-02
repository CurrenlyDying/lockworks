"""
GambitCompiler: S-Lang → G-ISA → Qiskit Transpilation
======================================================

The main compiler for the Schrödinger's Gambit quantum stack.

Pipeline:
    1. PARSE: S-Lang source → G-ISA Instructions
    2. COMPILE: G-ISA Instructions → Qiskit QuantumCircuit
    3. TRANSPILE: Optimize for target backend
    4. EXECUTE: Run on IBM hardware
"""

import re
import logging
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum, auto

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from .isa import (
    OpCode,
    Instruction,
    SolitonRegister,
    SolitonHeap,
    TopologyConstants,
    decode_physical_to_logical,
    calculate_dominance,
)


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# TOKENIZER (Lexer)
# =============================================================================

class TokenType(Enum):
    """Token types for S-Lang lexer."""
    PROGRAM = auto()
    SOLITON = auto()
    IDENTIFIER = auto()
    NUMBER = auto()
    ASSIGN = auto()
    SEMICOLON = auto()
    COLON = auto()
    DOT = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    ROLL = auto()
    ENTANGLE = auto()
    MEASURE = auto()
    COMMENT = auto()
    NEWLINE = auto()
    EOF = auto()
    H = auto()  # Superposition literal


@dataclass
class Token:
    """A lexer token."""
    type: TokenType
    value: Any
    line: int
    column: int


class SLangLexer:
    """
    Tokenizer for S-Lang source code.
    
    Grammar:
        program <name>:
            soliton <name> = <0|1|H>;
            <name>.roll();
            entangle(<a>, <b>);
            result = measure(<name>);
    """
    
    KEYWORDS = {
        'program': TokenType.PROGRAM,
        'soliton': TokenType.SOLITON,
        'roll': TokenType.ROLL,
        'entangle': TokenType.ENTANGLE,
        'measure': TokenType.MEASURE,
        'H': TokenType.H,
    }
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
    
    def tokenize(self) -> List[Token]:
        """Tokenize the entire source."""
        while self.pos < len(self.source):
            self._skip_whitespace()
            if self.pos >= len(self.source):
                break
            
            char = self.source[self.pos]
            
            # Comments
            if char == '#':
                self._skip_comment()
                continue
            
            # Newlines
            if char == '\n':
                self._advance()
                continue
            
            # Single-char tokens
            if char == '=':
                self._add_token(TokenType.ASSIGN, '=')
                self._advance()
            elif char == ';':
                self._add_token(TokenType.SEMICOLON, ';')
                self._advance()
            elif char == ':':
                self._add_token(TokenType.COLON, ':')
                self._advance()
            elif char == '.':
                self._add_token(TokenType.DOT, '.')
                self._advance()
            elif char == '(':
                self._add_token(TokenType.LPAREN, '(')
                self._advance()
            elif char == ')':
                self._add_token(TokenType.RPAREN, ')')
                self._advance()
            elif char == ',':
                self._add_token(TokenType.COMMA, ',')
                self._advance()
            # Numbers
            elif char.isdigit():
                self._read_number()
            # Identifiers / Keywords
            elif char.isalpha() or char == '_':
                self._read_identifier()
            else:
                self._advance()  # Skip unknown chars
        
        self._add_token(TokenType.EOF, None)
        return self.tokens
    
    def _advance(self) -> str:
        char = self.source[self.pos]
        self.pos += 1
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char
    
    def _add_token(self, type: TokenType, value: Any):
        self.tokens.append(Token(type, value, self.line, self.column))
    
    def _skip_whitespace(self):
        while self.pos < len(self.source) and self.source[self.pos] in ' \t\r':
            self._advance()
    
    def _skip_comment(self):
        while self.pos < len(self.source) and self.source[self.pos] != '\n':
            self._advance()
    
    def _read_number(self):
        start = self.pos
        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            self._advance()
        value = int(self.source[start:self.pos])
        self._add_token(TokenType.NUMBER, value)
    
    def _read_identifier(self):
        start = self.pos
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
            self._advance()
        text = self.source[start:self.pos]
        
        # Check for keywords
        if text in self.KEYWORDS:
            self._add_token(self.KEYWORDS[text], text)
        else:
            self._add_token(TokenType.IDENTIFIER, text)


# =============================================================================
# PARSER
# =============================================================================

class SLangParser:
    """
    Parser for S-Lang → G-ISA Instructions.
    
    Parses the token stream into a list of G-ISA Instructions.
    """
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.instructions: List[Instruction] = []
        self.program_name: str = "Unnamed"
    
    def parse(self) -> Tuple[str, List[Instruction]]:
        """
        Parse tokens into instructions.
        
        Returns:
            Tuple of (program_name, instructions)
        """
        # Optional program declaration
        if self._check(TokenType.PROGRAM):
            self._parse_program_header()
        
        # Parse statements
        while not self._is_at_end():
            self._parse_statement()
        
        return self.program_name, self.instructions
    
    def _parse_program_header(self):
        """Parse: program <name>:"""
        self._advance()  # consume 'program'
        name_token = self._expect(TokenType.IDENTIFIER, "Expected program name")
        self.program_name = name_token.value
        self._expect(TokenType.COLON, "Expected ':' after program name")
    
    def _parse_statement(self):
        """Parse a single statement."""
        if self._check(TokenType.SOLITON):
            self._parse_soliton_declaration()
        elif self._check(TokenType.ENTANGLE):
            self._parse_entangle()
        elif self._check(TokenType.IDENTIFIER):
            # Could be: name.roll(), name = measure(...), etc.
            self._parse_identifier_statement()
        elif self._check(TokenType.EOF):
            return
        else:
            self._advance()  # Skip unknown
    
    def _parse_soliton_declaration(self):
        """Parse: soliton <name> = <value>;"""
        self._advance()  # consume 'soliton'
        name_token = self._expect(TokenType.IDENTIFIER, "Expected soliton name")
        name = name_token.value
        
        # Allocation instruction
        self.instructions.append(Instruction.alloc(name))
        
        # Check for initialization
        if self._check(TokenType.ASSIGN):
            self._advance()  # consume '='
            
            if self._check(TokenType.NUMBER):
                value = self._advance().value
                self.instructions.append(Instruction.write(name, value))
            elif self._check(TokenType.H):
                self._advance()  # consume 'H'
                # Superposition - use special metadata
                instr = Instruction(OpCode.S_WRITE, name, ["H"])
                self.instructions.append(instr)
        
        self._match(TokenType.SEMICOLON)
    
    def _parse_entangle(self):
        """Parse: entangle(<a>, <b>);"""
        self._advance()  # consume 'entangle'
        self._expect(TokenType.LPAREN, "Expected '('")
        
        control = self._expect(TokenType.IDENTIFIER, "Expected control soliton").value
        self._expect(TokenType.COMMA, "Expected ','")
        target = self._expect(TokenType.IDENTIFIER, "Expected target soliton").value
        
        self._expect(TokenType.RPAREN, "Expected ')'")
        self._match(TokenType.SEMICOLON)
        
        self.instructions.append(Instruction.cnot(control, target))
    
    def _parse_identifier_statement(self):
        """Parse statements starting with identifier."""
        name = self._advance().value
        
        if self._check(TokenType.DOT):
            # Method call: name.roll()
            self._advance()  # consume '.'
            if self._check(TokenType.ROLL):
                self._advance()  # consume 'roll'
                self._expect(TokenType.LPAREN, "Expected '('")
                self._expect(TokenType.RPAREN, "Expected ')'")
                self._match(TokenType.SEMICOLON)
                self.instructions.append(Instruction.roll(name))
        
        elif self._check(TokenType.ASSIGN):
            # Assignment: result = measure(...)
            self._advance()  # consume '='
            if self._check(TokenType.MEASURE):
                self._advance()  # consume 'measure'
                self._expect(TokenType.LPAREN, "Expected '('")
                target = self._expect(TokenType.IDENTIFIER, "Expected target").value
                self._expect(TokenType.RPAREN, "Expected ')'")
                self._match(TokenType.SEMICOLON)
                
                instr = Instruction.measure(target)
                instr.metadata['result_var'] = name
                self.instructions.append(instr)
    
    # Helper methods
    def _advance(self) -> Token:
        if not self._is_at_end():
            self.pos += 1
        return self.tokens[self.pos - 1]
    
    def _check(self, type: TokenType) -> bool:
        if self._is_at_end():
            return False
        return self.tokens[self.pos].type == type
    
    def _match(self, type: TokenType) -> bool:
        if self._check(type):
            self._advance()
            return True
        return False
    
    def _expect(self, type: TokenType, message: str) -> Token:
        if self._check(type):
            return self._advance()
        raise SyntaxError(f"Line {self.tokens[self.pos].line}: {message}")
    
    def _is_at_end(self) -> bool:
        return self.tokens[self.pos].type == TokenType.EOF


# =============================================================================
# CIRCUIT COMPILER
# =============================================================================

class CircuitCompiler:
    """
    Compiles G-ISA Instructions to Qiskit QuantumCircuit.
    
    Implements the Schrödinger's Braid topology:
        1. Open Portal (H gates)
        2. Braid Loop (CZ, RX, RZ) × COMPLEXITY
        3. Close Portal (H gates)
        4. Measure
    """
    
    def __init__(self, complexity: int = TopologyConstants.COMPLEXITY, 
                 unsafe: bool = False):
        self.complexity = complexity
        self.unsafe = unsafe
        self.heap = SolitonHeap()
        
        # Validate complexity
        if complexity < TopologyConstants.COMPLEXITY_MIN and not unsafe:
            logger.warning(
                f"⚠️ Complexity {complexity} < {TopologyConstants.COMPLEXITY_MIN}: "
                "Geometry may break! Use unsafe=True to override."
            )
    
    def compile(self, instructions: List[Instruction]) -> QuantumCircuit:
        """
        Compile instructions to quantum circuit.
        
        Args:
            instructions: List of G-ISA instructions
            
        Returns:
            Compiled QuantumCircuit
        """
        # First pass: allocate all solitons
        for instr in instructions:
            if instr.opcode == OpCode.S_ALLOC:
                self.heap.alloc(instr.target)
        
        # Second pass: process writes
        for instr in instructions:
            if instr.opcode == OpCode.S_WRITE:
                reg = self.heap.get(instr.target)
                value = instr.operands[0]
                if value == "H":
                    reg.set_superposition()
                else:
                    reg.write(value)
            elif instr.opcode == OpCode.S_ROLL:
                reg = self.heap.get(instr.target)
                reg.roll()
        
        # Validate topology
        warnings = self.heap.validate_topology(self.complexity)
        for w in warnings:
            logger.warning(w)
        
        # Build circuit
        n_phys = self.heap.num_physical_qubits
        n_log = self.heap.num_solitons
        
        if n_phys == 0:
            raise ValueError("No solitons allocated!")
        
        qreg = QuantumRegister(n_phys, 'q')
        creg = ClassicalRegister(n_log, 'meas')
        qc = QuantumCircuit(qreg, creg)
        
        # === LAYER 1: OPEN PORTAL (Hadamard) ===
        qc.h(qreg)
        
        # === LAYER 2: BRAID TOPOLOGY ===
        for reg in self.heap.get_all():
            p_phase = reg.phase_qubit
            p_data = reg.data_qubit
            theta = reg.theta
            
            # Clamp theta if not unsafe
            if not self.unsafe:
                theta = max(TopologyConstants.THETA_MIN, 
                           min(theta, TopologyConstants.THETA_MAX))
            
            for _ in range(self.complexity):
                qc.cz(qreg[p_phase], qreg[p_data])
                qc.rx(theta, qreg[p_phase])
                qc.rz(theta * 2, qreg[p_data])
                qc.barrier([qreg[p_phase], qreg[p_data]])
        
        # === LAYER 3: APPLY OPERATIONS (CNOT etc.) ===
        for instr in instructions:
            if instr.opcode == OpCode.S_CNOT:
                control_name = instr.operands[0]
                target_name = instr.target
                
                ctrl_reg = self.heap.get(control_name)
                tgt_reg = self.heap.get(target_name)
                
                # CNOT between DATA bits only
                qc.cx(qreg[ctrl_reg.data_qubit], qreg[tgt_reg.data_qubit])
        
        # === LAYER 4: CLOSE PORTAL (Hadamard) ===
        qc.h(qreg)
        
        # === LAYER 5: MEASURE DATA BITS ===
        measure_idx = 0
        for instr in instructions:
            if instr.opcode == OpCode.S_MEASURE:
                reg = self.heap.get(instr.target)
                qc.measure(qreg[reg.data_qubit], creg[measure_idx])
                measure_idx += 1
        
        # If no explicit measure, measure all
        if measure_idx == 0:
            for i, reg in enumerate(self.heap.get_all()):
                qc.measure(qreg[reg.data_qubit], creg[i])
        
        return qc


# =============================================================================
# MAIN COMPILER CLASS
# =============================================================================

class GambitCompiler:
    """
    The Schrödinger's Gambit Compiler.
    
    Compiles S-Lang source code to hardware-ready quantum circuits.
    
    Example:
        >>> compiler = GambitCompiler()
        >>> circuit = compiler.compile_source('''
        ...     program Bell:
        ...         soliton a = H;
        ...         soliton b = 0;
        ...         entangle(a, b);
        ...         measure(a);
        ...         measure(b);
        ... ''')
    """
    
    def __init__(self, complexity: int = TopologyConstants.COMPLEXITY,
                 unsafe: bool = False,
                 optimization_level: int = 3):
        self.complexity = complexity
        self.unsafe = unsafe
        self.optimization_level = optimization_level
        self._circuit_compiler = None
    
    def compile_source(self, source: str) -> Tuple[str, QuantumCircuit]:
        """
        Compile S-Lang source to quantum circuit.
        
        Args:
            source: S-Lang source code
            
        Returns:
            Tuple of (program_name, QuantumCircuit)
        """
        # Tokenize
        lexer = SLangLexer(source)
        tokens = lexer.tokenize()
        
        # Parse
        parser = SLangParser(tokens)
        program_name, instructions = parser.parse()
        
        logger.info(f"📝 Parsed program: {program_name}")
        logger.info(f"   Instructions: {len(instructions)}")
        
        # Compile to circuit
        self._circuit_compiler = CircuitCompiler(
            complexity=self.complexity,
            unsafe=self.unsafe
        )
        circuit = self._circuit_compiler.compile(instructions)
        circuit.name = program_name
        
        n_phys = self._circuit_compiler.heap.num_physical_qubits
        n_log = self._circuit_compiler.heap.num_solitons
        logger.info(f"   Allocated: {n_log} logical ({n_phys} physical) qubits")
        
        return program_name, circuit
    
    def compile_file(self, filepath: str) -> Tuple[str, QuantumCircuit]:
        """Compile S-Lang file to quantum circuit."""
        with open(filepath, 'r') as f:
            source = f.read()
        return self.compile_source(source)
    
    def transpile(self, circuit: QuantumCircuit, backend) -> QuantumCircuit:
        """
        Transpile circuit for target backend.
        
        Args:
            circuit: The quantum circuit to transpile
            backend: IBM backend object
            
        Returns:
            Transpiled circuit ready for execution
        """
        logger.info(f"🔨 Transpiling for {backend.name} (opt_level={self.optimization_level})")
        
        pm = generate_preset_pass_manager(
            backend=backend, 
            optimization_level=self.optimization_level
        )
        return pm.run(circuit)
    
    @property
    def heap(self) -> Optional[SolitonHeap]:
        """Get the soliton heap from the last compilation."""
        if self._circuit_compiler:
            return self._circuit_compiler.heap
        return None


# =============================================================================
# G-ISA ASSEMBLER (Text Assembly Format)
# =============================================================================

class GISAAssembler:
    """
    Assembler for G-ISA text format.
    
    Example:
        S_ALLOC alpha
        S_WRITE alpha 0
        S_ALLOC beta
        S_WRITE beta 1
        S_CNOT alpha beta
        S_MEASURE alpha
        S_MEASURE beta
    """
    
    def assemble(self, source: str) -> List[Instruction]:
        """Assemble G-ISA text to instructions."""
        instructions = []
        
        for line_num, line in enumerate(source.strip().split('\n'), 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split()
            if not parts:
                continue
            
            opcode_str = parts[0].upper()
            
            try:
                opcode = OpCode[opcode_str]
            except KeyError:
                raise SyntaxError(f"Line {line_num}: Unknown opcode '{opcode_str}'")
            
            if opcode == OpCode.S_ALLOC:
                if len(parts) < 2:
                    raise SyntaxError(f"Line {line_num}: S_ALLOC requires name")
                instructions.append(Instruction.alloc(parts[1]))
            
            elif opcode == OpCode.S_WRITE:
                if len(parts) < 3:
                    raise SyntaxError(f"Line {line_num}: S_WRITE requires name and value")
                value = int(parts[2]) if parts[2].isdigit() else parts[2]
                if isinstance(value, int):
                    instructions.append(Instruction.write(parts[1], value))
                else:
                    instructions.append(Instruction(OpCode.S_WRITE, parts[1], [value]))
            
            elif opcode == OpCode.S_ROLL:
                if len(parts) < 2:
                    raise SyntaxError(f"Line {line_num}: S_ROLL requires name")
                instructions.append(Instruction.roll(parts[1]))
            
            elif opcode == OpCode.S_CNOT:
                if len(parts) < 3:
                    raise SyntaxError(f"Line {line_num}: S_CNOT requires control and target")
                instructions.append(Instruction.cnot(parts[1], parts[2]))
            
            elif opcode == OpCode.S_MEASURE:
                if len(parts) < 2:
                    raise SyntaxError(f"Line {line_num}: S_MEASURE requires name")
                instructions.append(Instruction.measure(parts[1]))
        
        return instructions


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def compile_slang(source: str, complexity: int = 6) -> QuantumCircuit:
    """
    Convenience function to compile S-Lang source.
    
    Args:
        source: S-Lang source code
        complexity: Braid complexity (default 6)
        
    Returns:
        Compiled QuantumCircuit
    """
    compiler = GambitCompiler(complexity=complexity)
    _, circuit = compiler.compile_source(source)
    return circuit


def compile_gisa(source: str, complexity: int = 6) -> QuantumCircuit:
    """
    Convenience function to compile G-ISA assembly.
    
    Args:
        source: G-ISA assembly source
        complexity: Braid complexity (default 6)
        
    Returns:
        Compiled QuantumCircuit
    """
    assembler = GISAAssembler()
    instructions = assembler.assemble(source)
    
    cc = CircuitCompiler(complexity=complexity)
    return cc.compile(instructions)
