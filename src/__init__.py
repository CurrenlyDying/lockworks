"""
Project SIGMA: Schrödinger's Gambit Compute Stack
==================================================

A topological quantum computing stack based on the Schrödinger's Gambit protocol.

Core Components:
    - isa: G-ISA opcodes and instruction set
    - compiler: S-Lang → G-ISA → Qiskit transpilation
    - runtime: IBM Quantum execution manager
    - slang: S-Lang parser and program builder
    
CTM (Cylindrical Topological Memory):
    - cylinder: UnitCell (Disk) and Cylinder (Memory Bank)
    - needle: IBM hardware driver for measurement
    - sequencer: Phase Lock Loop validator

Example:
    >>> from src import Cylinder, NeedleDriver
    >>> 
    >>> mem = Cylinder(4)  # 4 disks, 8 physical qubits
    >>> mem.rotate(0, 1)   # Set disk 0 to position 1
    >>> mem.link(0, 1)     # Gear disk 0 to disk 1
    >>> 
    >>> needle = NeedleDriver()
    >>> result = needle.read(mem)
    >>> print(result.values)
"""

from .isa import (
    OpCode,
    Instruction,
    SolitonRegister,
    SolitonHeap,
    TopologyConstants,
)

from .compiler import (
    GambitCompiler,
    CircuitCompiler,
    SLangLexer,
    SLangParser,
    GISAAssembler,
    compile_slang,
    compile_gisa,
)

from .runtime import (
    GambitExecutionManager,
    GambitResult,
    run_circuit,
    verify_topology,
)

from .slang import (
    SLangProgram,
    SolitonVar,
    parse_slang,
    quick_bell_state,
    quick_soliton_roll,
)

# CTM (Cylindrical Topological Memory)
from .cylinder import (
    Cylinder,
    UnitCell,
    create_memory,
    GeometryError,
    AddressError,
)

from .needle import (
    NeedleDriver,
    NeedleResult,
    quick_read,
)

from .sequencer import (
    Sequencer,
    Operation,
    OpType,
    quick_sequence,
)

__version__ = "2.0.0"
__all__ = [
    # ISA
    "OpCode",
    "Instruction", 
    "SolitonRegister",
    "SolitonHeap",
    "TopologyConstants",
    # Compiler
    "GambitCompiler",
    "CircuitCompiler",
    "SLangLexer",
    "SLangParser",
    "GISAAssembler",
    "compile_slang",
    "compile_gisa",
    # Runtime
    "GambitExecutionManager",
    "GambitResult",
    "run_circuit",
    "verify_topology",
    # S-Lang
    "SLangProgram",
    "SolitonVar",
    "parse_slang",
    "quick_bell_state",
    "quick_soliton_roll",
    # CTM
    "Cylinder",
    "UnitCell",
    "create_memory",
    "GeometryError",
    "AddressError",
    "NeedleDriver",
    "NeedleResult",
    "quick_read",
    "Sequencer",
    "Operation",
    "OpType",
    "quick_sequence",
]

