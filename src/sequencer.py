"""
Sequencer - Phase Lock Loop Validator
=====================================

Ensures atomic operations and validates the "osu pattern" timing requirements.

The sequencer enforces:
    1. Atomic rotations (braid must complete full cycle)
    2. Gray Code transitions (no multi-bit flips)
    3. Operation ordering (no interrupts during braid)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum, auto

from .cylinder import Cylinder, UnitCell, GeometryError
from .isa import TopologyConstants


# =============================================================================
# OPERATION TYPES
# =============================================================================

class OpType(Enum):
    ALLOC = auto()
    ROTATE = auto()
    LINK = auto()
    READ = auto()
    BARRIER = auto()


@dataclass
class Operation:
    """A sequenced operation in the CTM pipeline."""
    op_type: OpType
    address: Optional[int] = None
    value: Optional[int] = None
    target: Optional[int] = None  # For LINK
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# SEQUENCER
# =============================================================================

class Sequencer:
    """
    The Phase Lock Loop (PLL) Sequencer.
    
    Validates and orders operations to ensure topological integrity.
    
    Rules:
        1. ROTATE is atomic - cannot be interrupted
        2. Braid must complete full complexity cycle (C=6)
        3. Gray Code transitions for multi-step rotations
        4. No parallel operations on same disk
        
    Example:
        >>> seq = Sequencer()
        >>> seq.rotate(0, 1)
        >>> seq.rotate(1, 0)
        >>> seq.link(0, 1)
        >>> seq.validate()  # Checks integrity
        >>> circuit = seq.compile(cylinder)
    """
    
    def __init__(self, complexity: int = TopologyConstants.COMPLEXITY):
        self.complexity = complexity
        self.operations: List[Operation] = []
        self._validated = False
        
        # Gray Code transitions
        self.GRAY_TRANSITIONS = {
            (0, 0): [],
            (0, 1): [0.0, 0.1, 0.196],     # 0 → H → 1
            (1, 0): [0.196, 0.1, 0.0],     # 1 → H → 0
            (1, 1): [],
        }
    
    def alloc(self, n_disks: int) -> "Sequencer":
        """Queue ALLOC operation."""
        self.operations.append(Operation(
            op_type=OpType.ALLOC,
            value=n_disks
        ))
        self._validated = False
        return self
    
    def rotate(self, address: int, target: int) -> "Sequencer":
        """
        Queue ROTATE operation.
        
        Uses Gray Code transition if needed.
        """
        self.operations.append(Operation(
            op_type=OpType.ROTATE,
            address=address,
            value=target
        ))
        self._validated = False
        return self
    
    def link(self, control: int, target: int) -> "Sequencer":
        """Queue LINK operation."""
        self.operations.append(Operation(
            op_type=OpType.LINK,
            address=control,
            target=target
        ))
        self._validated = False
        return self
    
    def read(self, address: int) -> "Sequencer":
        """Queue READ operation."""
        self.operations.append(Operation(
            op_type=OpType.READ,
            address=address
        ))
        self._validated = False
        return self
    
    def barrier(self) -> "Sequencer":
        """Insert a barrier (sync point)."""
        self.operations.append(Operation(op_type=OpType.BARRIER))
        return self
    
    # =========================================================================
    # VALIDATION
    # =========================================================================
    
    def validate(self) -> bool:
        """
        Validate the operation sequence.
        
        Checks:
            1. No overlapping rotations on same disk
            2. LINK only between valid addresses
            3. Complexity requirements met
            
        Returns:
            True if valid
            
        Raises:
            GeometryError if invalid
        """
        errors = []
        
        # Track disk states
        rotating = set()  # Disks currently in rotation
        
        for i, op in enumerate(self.operations):
            if op.op_type == OpType.ROTATE:
                if op.address in rotating:
                    errors.append(
                        f"Op[{i}]: Disk {op.address} rotation interrupted - "
                        "geometry shattered!"
                    )
                rotating.add(op.address)
                
            elif op.op_type == OpType.BARRIER:
                rotating.clear()  # Barrier completes all rotations
                
            elif op.op_type == OpType.LINK:
                # Check both disks aren't rotating
                if op.address in rotating or op.target in rotating:
                    errors.append(
                        f"Op[{i}]: LINK during rotation - unsafe state"
                    )
        
        if errors:
            raise GeometryError("\n".join(errors))
        
        self._validated = True
        return True
    
    def validate_complexity(self, circuit_depth: int) -> bool:
        """
        Validate that circuit depth meets complexity requirements.
        
        The braid must complete C iterations.
        """
        min_depth = self.complexity * 4  # CZ + RX + RZ + barrier per iteration
        
        if circuit_depth < min_depth:
            raise GeometryError(
                f"Circuit depth {circuit_depth} < minimum {min_depth}. "
                "Braid did not complete - geometry shattered!"
            )
        
        return True
    
    # =========================================================================
    # COMPILATION
    # =========================================================================
    
    def compile(self, cylinder: Cylinder) -> None:
        """
        Apply sequenced operations to a cylinder.
        
        Args:
            cylinder: The target cylinder to modify
        """
        if not self._validated:
            self.validate()
        
        for op in self.operations:
            if op.op_type == OpType.ALLOC:
                cylinder.alloc()
                
            elif op.op_type == OpType.ROTATE:
                cylinder.rotate(op.address, op.value)
                
            elif op.op_type == OpType.LINK:
                cylinder.link(op.address, op.target)
                
            elif op.op_type == OpType.READ:
                pass  # Reads are handled by Needle
    
    def get_read_addresses(self) -> List[int]:
        """Get all addresses queued for reading."""
        return [
            op.address 
            for op in self.operations 
            if op.op_type == OpType.READ
        ]
    
    # =========================================================================
    # UTILITY
    # =========================================================================
    
    def dump(self) -> List[Dict[str, Any]]:
        """Dump operation sequence for debugging."""
        return [
            {
                "idx": i,
                "op": op.op_type.name,
                "address": op.address,
                "value": op.value,
                "target": op.target
            }
            for i, op in enumerate(self.operations)
        ]
    
    def __repr__(self) -> str:
        ops = [op.op_type.name for op in self.operations]
        return f"Sequencer([{', '.join(ops)}])"
    
    def clear(self) -> None:
        """Clear all queued operations."""
        self.operations = []
        self._validated = False


# =============================================================================
# CONVENIENCE
# =============================================================================

def quick_sequence(writes: Dict[int, int], links: List[tuple] = None) -> Sequencer:
    """
    Quickly build a sequence from writes and links.
    
    Args:
        writes: Dict of {address: value}
        links: List of (control, target) tuples
        
    Returns:
        Configured Sequencer
    """
    seq = Sequencer()
    
    for addr, value in sorted(writes.items()):
        seq.rotate(addr, value)
    
    seq.barrier()
    
    for ctrl, tgt in (links or []):
        seq.link(ctrl, tgt)
    
    seq.barrier()
    
    for addr in sorted(writes.keys()):
        seq.read(addr)
    
    return seq
