"""
G-ISA: Gray Code Protected Instruction Set Architecture
========================================================

The core instruction set for the Schrödinger's Gambit topological quantum protocol.

Key Concepts:
    - Each Logical Qubit (Soliton) = 2 Physical Qubits (phase + data)
    - State 0 (ROBUST): θ = 0.0 rad → ~93% dominance on |00⟩
    - State 1 (FISHER): θ = 0.196 rad → ~90% dominance on |10⟩
    - Transitions use "Soliton Roll" - continuous θ rotation
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
import numpy as np


# =============================================================================
# TOPOLOGY CONSTANTS (The Magic Numbers)
# =============================================================================

class TopologyConstants:
    """
    Verified topological parameters from IBM Fez benchmarks.
    
    v2.0 MODULAR ARCHITECTURE:
        - Each Soliton Core = 2 Physical Qubits (CORE_SIZE = 2)
        - Scale OUT: Network multiple cores via CX
        - Do NOT scale UP: Larger braids fail (tested on IBM Fez)
        
    Experimental Results (2026-01-31):
        - 2-Qubit: 93% purity ✅
        - 3-Qubit Chain: 53% ⚠️
        - 4-Qubit Chain: 4.6% ❌
    """
    
    # Modular Architecture (v2.0)
    CORE_SIZE: int = 2           # Physical qubits per logical qubit (FIXED)
    MAX_CORES: int = 16          # Max logical qubits (32 physical max)
    
    # Circuit complexity (6 = 12-slice Moiré geometry)
    COMPLEXITY: int = 6
    COMPLEXITY_MIN: int = 4  # Minimum before geometry breaks
    
    # Shot count (statistical sweet spot)
    SHOTS: int = 4096
    
    # Topological Poles (verified angles)
    THETA_ROBUST: float = 0.0       # |0⟩_L - 93% purity
    THETA_EDGE: float = 0.1         # Superposition - ~50%
    THETA_FISHER: float = 0.196     # |1⟩_L - 90% purity
    THETA_MAX_INFO: float = 0.4     # Return pole - ~89%
    
    # Safe operating range
    THETA_MIN: float = 0.0
    THETA_MAX: float = 0.4
    
    # Quality thresholds
    DOMINANCE_THRESHOLD: float = 0.85  # Below = DECOHERED
    Z_SCORE_THRESHOLD: float = 14.0    # Above = ULTRA-TRIVIAL confirmed
    
    # Gray Code sequence for safe transitions
    GRAY_CODE_SEQUENCE = [0b00, 0b01, 0b11, 0b10]  # 0 → 1 → 3 → 2
    GRAY_CODE_THETAS = [0.0, 0.1, 0.196, 0.4]


# =============================================================================
# OPCODES (G-ISA Instruction Set)
# =============================================================================

class OpCode(Enum):
    """
    G-ISA OpCodes - The Quantum Instruction Set.
    
    Each operation maps to specific topological transformations:
        S_ALLOC: Reserve 2 physical qubits for a logical soliton
        S_WRITE: Set the topological angle (snap to pole)
        S_ROLL: Soliton flip (logical NOT via continuous θ rotation)
        S_CNOT: Topological entanglement between solitons
        S_MEASURE: Close interferometer and read logical state
    """
    S_ALLOC = auto()    # Allocate soliton (2 physical qubits)
    S_WRITE = auto()    # Set topological pole
    S_ROLL = auto()     # Soliton flip (logical NOT)
    S_CNOT = auto()     # Topological CNOT
    S_MEASURE = auto()  # Measure (close portal)
    
    # Extended opcodes (future)
    S_HADAMARD = auto()  # Superposition (θ = 0.1)
    S_BARRIER = auto()   # Circuit barrier
    S_RESET = auto()     # Reset to ROBUST


# =============================================================================
# INSTRUCTION CLASS
# =============================================================================

@dataclass
class Instruction:
    """
    A single G-ISA instruction with operands.
    
    Attributes:
        opcode: The operation to perform
        target: Target soliton name
        operands: Additional operands (value for WRITE, control for CNOT)
        metadata: Optional metadata for debugging
    """
    opcode: OpCode
    target: str
    operands: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        ops_str = " ".join(str(o) for o in self.operands)
        return f"{self.opcode.name} {self.target} {ops_str}".strip()
    
    @classmethod
    def alloc(cls, name: str) -> "Instruction":
        """Create S_ALLOC instruction."""
        return cls(OpCode.S_ALLOC, name)
    
    @classmethod
    def write(cls, target: str, value: int) -> "Instruction":
        """Create S_WRITE instruction."""
        if value not in (0, 1):
            raise ValueError(f"S_WRITE value must be 0 or 1, got {value}")
        return cls(OpCode.S_WRITE, target, [value])
    
    @classmethod
    def roll(cls, target: str) -> "Instruction":
        """Create S_ROLL instruction (logical NOT)."""
        return cls(OpCode.S_ROLL, target)
    
    @classmethod
    def cnot(cls, control: str, target: str) -> "Instruction":
        """Create S_CNOT instruction."""
        return cls(OpCode.S_CNOT, target, [control])
    
    @classmethod
    def measure(cls, target: str) -> "Instruction":
        """Create S_MEASURE instruction."""
        return cls(OpCode.S_MEASURE, target)


# =============================================================================
# SOLITON REGISTER (Logical Qubit)
# =============================================================================

@dataclass
class SolitonRegister:
    """
    A Logical Qubit (Soliton) in the Gambit architecture.
    
    Each soliton is made of 2 physical qubits:
        - q_phase (index 0): Phase bit for topology
        - q_data (index 1): Data bit that "flips"
    
    Attributes:
        name: Unique identifier for this soliton
        theta: Current topological angle (determines logical state)
        phys_indices: Tuple of (phase_qubit_idx, data_qubit_idx)
    """
    name: str
    theta: float = 0.0  # Default to ROBUST
    phys_indices: tuple = field(default_factory=lambda: (0, 1))
    
    def __post_init__(self):
        self._validate_theta()
    
    def _validate_theta(self, warn: bool = True) -> None:
        """Validate theta is in safe range."""
        if not TopologyConstants.THETA_MIN <= self.theta <= TopologyConstants.THETA_MAX:
            if warn:
                import warnings
                warnings.warn(
                    f"Theta {self.theta} outside safe range "
                    f"[{TopologyConstants.THETA_MIN}, {TopologyConstants.THETA_MAX}]"
                )
    
    @property
    def phase_qubit(self) -> int:
        """Physical index of phase qubit."""
        return self.phys_indices[0]
    
    @property
    def data_qubit(self) -> int:
        """Physical index of data qubit (the one that flips)."""
        return self.phys_indices[1]
    
    @property
    def logical_state(self) -> int:
        """Expected logical state based on current theta."""
        if np.isclose(self.theta, TopologyConstants.THETA_ROBUST, atol=0.05):
            return 0
        elif np.isclose(self.theta, TopologyConstants.THETA_FISHER, atol=0.05):
            return 1
        else:
            return -1  # Superposition or intermediate
    
    def write(self, value: int) -> None:
        """
        S_WRITE: Snap to a topological pole.
        
        Args:
            value: 0 for ROBUST, 1 for FISHER
        """
        if value == 0:
            self.theta = TopologyConstants.THETA_ROBUST
        elif value == 1:
            self.theta = TopologyConstants.THETA_FISHER
        else:
            raise ValueError(f"Invalid logical value: {value}")
    
    def roll(self) -> None:
        """
        S_ROLL: The Soliton Roll (logical NOT).
        
        Continuously rotates θ across the phase transition.
        """
        if np.isclose(self.theta, TopologyConstants.THETA_ROBUST, atol=0.05):
            self.theta = TopologyConstants.THETA_FISHER
        else:
            self.theta = TopologyConstants.THETA_ROBUST
    
    def set_superposition(self) -> None:
        """Set to edge/superposition state (θ = 0.1)."""
        self.theta = TopologyConstants.THETA_EDGE
    
    def to_gray_level(self) -> int:
        """Convert current theta to Gray Code level (0-3)."""
        thetas = TopologyConstants.GRAY_CODE_THETAS
        distances = [abs(self.theta - t) for t in thetas]
        return distances.index(min(distances))


# =============================================================================
# SOLITON HEAP (Quantum Memory Manager)
# =============================================================================

class SolitonHeap:
    """
    Quantum Memory Manager for Soliton registers.
    
    Manages allocation and addressing of logical qubits:
        - Logical Index i → Physical Indices [2i, 2i+1]
        - Tracks all allocated solitons
        - Validates topology integrity
    """
    
    def __init__(self):
        self._heap: Dict[str, SolitonRegister] = {}
        self._next_phys_idx: int = 0
    
    def alloc(self, name: str, initial_value: int = 0) -> SolitonRegister:
        """
        S_ALLOC: Allocate a new soliton.
        
        Args:
            name: Unique identifier for the soliton
            initial_value: 0 (ROBUST) or 1 (FISHER)
            
        Returns:
            The allocated SolitonRegister
        """
        if name in self._heap:
            raise ValueError(f"Soliton '{name}' already allocated")
        
        # Allocate 2 physical qubits
        phys_indices = (self._next_phys_idx, self._next_phys_idx + 1)
        self._next_phys_idx += 2
        
        # Create register with initial state
        theta = (TopologyConstants.THETA_ROBUST if initial_value == 0 
                 else TopologyConstants.THETA_FISHER)
        
        reg = SolitonRegister(name=name, theta=theta, phys_indices=phys_indices)
        self._heap[name] = reg
        
        return reg
    
    def get(self, name: str) -> SolitonRegister:
        """Get a soliton by name."""
        if name not in self._heap:
            raise KeyError(f"Soliton '{name}' not found")
        return self._heap[name]
    
    def get_all(self) -> List[SolitonRegister]:
        """Get all allocated solitons."""
        return list(self._heap.values())
    
    @property
    def num_solitons(self) -> int:
        """Number of logical qubits."""
        return len(self._heap)
    
    @property
    def num_physical_qubits(self) -> int:
        """Number of physical qubits used."""
        return self._next_phys_idx
    
    def validate_topology(self, complexity: int) -> List[str]:
        """
        Validate topological integrity.
        
        Returns:
            List of warning messages
        """
        warnings = []
        
        if complexity < TopologyConstants.COMPLEXITY_MIN:
            warnings.append(
                f"⚠️ Complexity {complexity} < {TopologyConstants.COMPLEXITY_MIN}: "
                "Geometry may break!"
            )
        
        for name, reg in self._heap.items():
            if not (TopologyConstants.THETA_MIN <= reg.theta <= TopologyConstants.THETA_MAX):
                warnings.append(
                    f"⚠️ Soliton '{name}' theta={reg.theta:.3f} outside safe range"
                )
        
        return warnings
    
    def __contains__(self, name: str) -> bool:
        return name in self._heap
    
    def __len__(self) -> int:
        return len(self._heap)


# =============================================================================
# GREY CODE UTILITIES
# =============================================================================

def to_gray(n: int) -> int:
    """Convert integer to Gray Code."""
    return n ^ (n >> 1)


def from_gray(gray: int) -> int:
    """Convert Gray Code to integer."""
    n = gray
    mask = gray >> 1
    while mask:
        n ^= mask
        mask >>= 1
    return n


def gray_code_transition(from_level: int, to_level: int) -> List[int]:
    """
    Get the safe Gray Code transition path between two levels.
    
    Args:
        from_level: Starting level (0-3)
        to_level: Target level (0-3)
        
    Returns:
        List of intermediate levels to traverse
    """
    if from_level == to_level:
        return [from_level]
    
    # Gray code ensures only 1 bit changes per step
    # Sequence: 0 (00) → 1 (01) → 3 (11) → 2 (10)
    sequence = [0, 1, 3, 2]
    
    from_idx = sequence.index(from_level)
    to_idx = sequence.index(to_level)
    
    if from_idx <= to_idx:
        return sequence[from_idx:to_idx + 1]
    else:
        return sequence[from_idx:] + sequence[:to_idx + 1]


# =============================================================================
# RESULT DECODING
# =============================================================================

def decode_physical_to_logical(physical_state: str) -> int:
    """
    Decode physical measurement to logical state.
    
    Mapping:
        '00', '01' → Logical 0 (ROBUST)
        '10', '11' → Logical 1 (FISHER)
        
    Args:
        physical_state: 2-bit string from measurement
        
    Returns:
        Logical bit value (0 or 1)
    """
    if len(physical_state) != 2:
        raise ValueError(f"Expected 2-bit state, got '{physical_state}'")
    
    # The data bit (second position when reading left-to-right) determines logic
    # But Qiskit uses little-endian, so we check the first character
    return 1 if physical_state[0] == '1' else 0


def calculate_dominance(counts: Dict[str, int]) -> tuple:
    """
    Calculate dominance score from measurement counts.
    
    Args:
        counts: Dictionary of {state: count}
        
    Returns:
        Tuple of (dominance_score, top_state, is_decohered)
    """
    total = sum(counts.values())
    if total == 0:
        return 0.0, "??", True
    
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    top_state, top_count = sorted_counts[0]
    dominance = top_count / total
    
    is_decohered = dominance < TopologyConstants.DOMINANCE_THRESHOLD
    
    return dominance, top_state, is_decohered


def hellinger_distance(p: np.ndarray, q: np.ndarray) -> float:
    """Calculate Hellinger distance between two probability distributions."""
    return (1 / np.sqrt(2)) * np.linalg.norm(np.sqrt(p) - np.sqrt(q))
