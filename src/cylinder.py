"""
Cylindrical Topological Memory (CTM) v1.1
=========================================

The core abstraction for the SIGMA quantum storage system.

Physical Model:
    - Unit Cell (Disk): 2 physical qubits forming a rotary memory element
    - Cylinder: Linear array of N Disks (the memory bank)
    - Rotation: Continuous θ parameter controls disk position (0.0 → 0.196)

Positions:
    - Position 0 (Ground): θ = 0.0 rad → |00⟩
    - Position 1 (Excited): θ = 0.196 rad → |10⟩
    
v1.1 Upgrade:
    - Gearbox integration for protected LINK operations
    - Clutch + Idle Throttle prevents torque shatter
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum, auto
import numpy as np

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

from .isa import TopologyConstants
from .gearbox import Gearbox


# =============================================================================
# EXCEPTIONS
# =============================================================================

class GeometryError(Exception):
    """Raised when the geometry shatters (incomplete braid operation)."""
    pass


class AddressError(Exception):
    """Raised when accessing invalid memory address."""
    pass


# =============================================================================
# UNIT CELL (The "Disk")
# =============================================================================

@dataclass
class UnitCell:
    """
    A single memory disk in the Cylindrical Topological Memory.
    
    Physical Model:
        - 2 Physical Qubits: q_phase (sign) and q_data (magnitude)
        - Angle θ determines the logical state
        
    Geometry:
        Position 0: θ = 0.0 rad → Disk locks to |00⟩
        Position 1: θ = 0.196 rad → Disk locks to |10⟩
        
    Attributes:
        address: The memory address (index) of this disk
        theta: Current rotational angle
        phys_indices: Tuple of (phase_qubit, data_qubit) physical indices
    """
    address: int
    theta: float = 0.0
    phys_indices: tuple = field(default_factory=lambda: (0, 1))
    _locked: bool = field(default=False, repr=False)
    
    # Physical constants
    THETA_GROUND: float = 0.0      # Position 0
    THETA_EXCITED: float = 0.196   # Position 1
    
    @property
    def phase_qubit(self) -> int:
        """The Sign bit (q_0). Never measure this - it holds orientation."""
        return self.phys_indices[0]
    
    @property
    def data_qubit(self) -> int:
        """The Magnitude bit (q_1). This is the value bit."""
        return self.phys_indices[1]
    
    @property
    def position(self) -> int:
        """Current disk position (0 or 1)."""
        if np.isclose(self.theta, self.THETA_GROUND, atol=0.05):
            return 0
        elif np.isclose(self.theta, self.THETA_EXCITED, atol=0.05):
            return 1
        else:
            return -1  # Intermediate/transitioning
    
    def rotate_to(self, target: int) -> None:
        """
        Rotate disk to target position.
        
        Args:
            target: 0 for Ground, 1 for Excited
        """
        if self._locked:
            raise GeometryError(f"Disk {self.address} is locked during braid operation")
        
        if target == 0:
            self.theta = self.THETA_GROUND
        elif target == 1:
            self.theta = self.THETA_EXCITED
        else:
            raise ValueError(f"Invalid target position: {target}")
    
    def flip(self) -> None:
        """Flip disk position (0 ↔ 1)."""
        if self.position == 0:
            self.rotate_to(1)
        else:
            self.rotate_to(0)
    
    def lock(self) -> None:
        """Lock disk during atomic operation."""
        self._locked = True
    
    def unlock(self) -> None:
        """Unlock disk after atomic operation completes."""
        self._locked = False


# =============================================================================
# CYLINDER (The Memory Bank)
# =============================================================================

class Cylinder:
    """
    The Cylindrical Topological Memory bank.
    
    A linear array of N UnitCells (Disks) that form the quantum memory.
    
    Architecture:
        - Each disk is mechanically isolated (no inter-disk entanglement by default)
        - Addressing via integer index (0 to n_disks-1)
        - LINK operation gears two disks together
        
    Example:
        >>> mem = Cylinder(4)  # 4 disks, 8 physical qubits
        >>> mem.rotate(0, 1)   # Set disk 0 to position 1
        >>> mem.link(0, 1)     # Gear disk 0 to disk 1
        >>> mem.read(1)        # Read disk 1
    """
    
    def __init__(self, n_disks: int, complexity: int = TopologyConstants.COMPLEXITY):
        """
        Initialize a cylindrical memory bank.
        
        Args:
            n_disks: Number of memory disks (logical qubits)
            complexity: Braid complexity (C=6 is standard)
        """
        if n_disks > TopologyConstants.MAX_CORES:
            raise ValueError(
                f"Cannot allocate {n_disks} disks. "
                f"Max is {TopologyConstants.MAX_CORES}."
            )
        
        self.n_disks = n_disks
        self.complexity = complexity
        self.disks: List[UnitCell] = []
        
        # Allocate disks
        for i in range(n_disks):
            phys_idx = (2 * i, 2 * i + 1)  # Each disk = 2 physical qubits
            disk = UnitCell(address=i, theta=0.0, phys_indices=phys_idx)
            self.disks.append(disk)
        
        # Operation log for sequencing
        self._op_log: List[Dict[str, Any]] = []
    
    @property
    def n_physical_qubits(self) -> int:
        """Total physical qubits used."""
        return 2 * self.n_disks
    
    def _validate_address(self, address: int) -> None:
        """Validate memory address."""
        if not 0 <= address < self.n_disks:
            raise AddressError(
                f"Address {address} out of range [0, {self.n_disks})"
            )
    
    # =========================================================================
    # GEOMETRIC OPCODES
    # =========================================================================
    
    def alloc(self) -> None:
        """
        ALLOC(n_disks)
        
        Reset all disks to Position 0 (Ground).
        Analogous to: "Reset all tumblers to zero."
        """
        for disk in self.disks:
            disk.rotate_to(0)
        self._op_log.append({"op": "ALLOC", "n": self.n_disks})
    
    def rotate(self, address: int, target: int) -> None:
        """
        ROTATE(address, target_angle)
        
        Rotate disk at address to target position.
        
        Args:
            address: Memory address (disk index)
            target: Target position (0 or 1)
        """
        self._validate_address(address)
        
        disk = self.disks[address]
        disk.rotate_to(target)
        
        self._op_log.append({
            "op": "ROTATE",
            "addr": address,
            "target": target,
            "theta": disk.theta
        })
    
    def push(self, address: int, value: int) -> None:
        """
        PUSH(address, value)
        
        Alias for ROTATE - writes value to disk.
        
        Args:
            address: Memory address
            value: Value to write (0 or 1)
        """
        self.rotate(address, value)
    
    def read_needle(self, address: int) -> int:
        """
        READ_NEEDLE(address)
        
        Get the current position of disk at address.
        NOTE: Actual hardware read requires measurement.
        
        Returns:
            Current disk position (0 or 1)
        """
        self._validate_address(address)
        return self.disks[address].position
    
    def link(self, addr_a: int, addr_b: int) -> None:
        """
        LINK(addr_A, addr_B)
        
        Gear two disks together with a CX gate.
        If Disk A rotates, it drags Disk B.
        
        Args:
            addr_a: Control disk address
            addr_b: Target disk address
        """
        self._validate_address(addr_a)
        self._validate_address(addr_b)
        
        if addr_a == addr_b:
            raise ValueError("Cannot link a disk to itself")
        
        self._op_log.append({
            "op": "LINK",
            "control": addr_a,
            "target": addr_b
        })
    
    # =========================================================================
    # v3.2 ANCHOR SEQUENCE (Asymmetric Braiding)
    # =========================================================================
    
    def to_circuit_anchor(
        self, 
        control_addr: int, 
        control_value: int,
        target_addr: int,
        target_value: int,
        measurements: Optional[List[int]] = None
    ) -> QuantumCircuit:
        """
        Build circuit using v3.2 Anchor Sequence.
        
        Prevents Phase Kickback by hardening control before linking.
        
        Sequence:
            1. OPEN: H gates on all
            2. HARDEN CONTROL: Braid control disk only
            3. GEAR: CX from hardened control to fluid target
            4. SOFTEN TARGET: Braid target disk
            5. SEAL: H gates on all
            6. READ: Measure data bits
        
        Args:
            control_addr: Address of control disk
            control_value: Value for control (0 or 1)
            target_addr: Address of target disk
            target_value: Value for target (0 or 1)
            measurements: Disk addresses to measure (default: both)
        """
        n_phys = self.n_physical_qubits
        meas_list = measurements if measurements else [control_addr, target_addr]
        n_meas = len(meas_list)
        
        qreg = QuantumRegister(n_phys, 'q')
        creg = ClassicalRegister(n_meas, 'meas')
        qc = QuantumCircuit(qreg, creg, name="CTM_Anchor")
        
        # Get disk references
        ctrl_disk = self.disks[control_addr]
        tgt_disk = self.disks[target_addr]
        
        # Magic numbers
        theta_ctrl = 0.196 if control_value == 1 else 0.0
        theta_tgt = 0.196 if target_value == 1 else 0.0
        
        # === LAYER 1: OPEN PORTAL ===
        qc.h(qreg)
        
        # === LAYER 2: HARDEN CONTROL ===
        # Braid the control disk FIRST to lock it into its pole
        p_phase = ctrl_disk.phase_qubit
        p_data = ctrl_disk.data_qubit
        for _ in range(self.complexity):
            qc.cz(qreg[p_phase], qreg[p_data])
            qc.rx(theta_ctrl, qreg[p_phase])
            qc.rz(theta_ctrl * 2, qreg[p_data])
            qc.barrier([qreg[p_phase], qreg[p_data]])
        
        # === LAYER 3: GEAR (LINK) ===
        # CX from hardened control to fluid target
        qc.barrier()
        qc.cx(qreg[ctrl_disk.data_qubit], qreg[tgt_disk.data_qubit])
        qc.barrier()
        
        # === LAYER 4: SOFTEN TARGET ===
        # Now braid the target disk
        p_phase = tgt_disk.phase_qubit
        p_data = tgt_disk.data_qubit
        for _ in range(self.complexity):
            qc.cz(qreg[p_phase], qreg[p_data])
            qc.rx(theta_tgt, qreg[p_phase])
            qc.rz(theta_tgt * 2, qreg[p_data])
            qc.barrier([qreg[p_phase], qreg[p_data]])
        
        # === LAYER 5: SEAL ===
        qc.h(qreg)
        
        # === LAYER 6: MEASUREMENTS ===
        for i, addr in enumerate(meas_list):
            disk = self.disks[addr]
            qc.measure(qreg[disk.data_qubit], creg[i])
        
        return qc
    
    def to_circuit_anchor_inverted(
        self, 
        control_addr: int, 
        control_value: int,
        target_addr: int,
        target_value: int,
        measurements: Optional[List[int]] = None
    ) -> QuantumCircuit:
        """
        Same as to_circuit_anchor but with INVERTED CX direction.
        
        Use if hardware CX orientation is fighting logical mapping.
        CX(target, control) instead of CX(control, target).
        """
        n_phys = self.n_physical_qubits
        meas_list = measurements if measurements else [control_addr, target_addr]
        n_meas = len(meas_list)
        
        qreg = QuantumRegister(n_phys, 'q')
        creg = ClassicalRegister(n_meas, 'meas')
        qc = QuantumCircuit(qreg, creg, name="CTM_Anchor_Inv")
        
        ctrl_disk = self.disks[control_addr]
        tgt_disk = self.disks[target_addr]
        
        theta_ctrl = 0.196 if control_value == 1 else 0.0
        theta_tgt = 0.196 if target_value == 1 else 0.0
        
        # === LAYER 1: OPEN PORTAL ===
        qc.h(qreg)
        
        # === LAYER 2: HARDEN CONTROL ===
        p_phase = ctrl_disk.phase_qubit
        p_data = ctrl_disk.data_qubit
        for _ in range(self.complexity):
            qc.cz(qreg[p_phase], qreg[p_data])
            qc.rx(theta_ctrl, qreg[p_phase])
            qc.rz(theta_ctrl * 2, qreg[p_data])
            qc.barrier([qreg[p_phase], qreg[p_data]])
        
        # === LAYER 3: GEAR (INVERTED CX) ===
        # CX direction flipped: CX(target, control)
        qc.barrier()
        qc.cx(qreg[tgt_disk.data_qubit], qreg[ctrl_disk.data_qubit])
        qc.barrier()
        
        # === LAYER 4: SOFTEN TARGET ===
        p_phase = tgt_disk.phase_qubit
        p_data = tgt_disk.data_qubit
        for _ in range(self.complexity):
            qc.cz(qreg[p_phase], qreg[p_data])
            qc.rx(theta_tgt, qreg[p_phase])
            qc.rz(theta_tgt * 2, qreg[p_data])
            qc.barrier([qreg[p_phase], qreg[p_data]])
        
        # === LAYER 5: SEAL ===
        qc.h(qreg)
        
        # === LAYER 6: MEASUREMENTS ===
        for i, addr in enumerate(meas_list):
            disk = self.disks[addr]
            qc.measure(qreg[disk.data_qubit], creg[i])
        
        return qc
    
    def to_circuit(self, measurements: Optional[List[int]] = None) -> QuantumCircuit:
        """
        Convert the operation log to a Qiskit QuantumCircuit.
        
        CTM v3.1 COLD-START SEQUENCE:
            1. OPEN: Open Portal (H gates)
            2. GEAR: LINK operations (CX on stationary disks) ← COLD-START
            3. SPIN: Per-disk Braid (CZ, RX, RZ × C)
            4. SEAL: Close Portal (H gates)
            5. READ: Measurements (data bits only)
        
        Args:
            measurements: List of disk addresses to measure (default: all)
            
        Returns:
            Compiled QuantumCircuit
        """
        n_phys = self.n_physical_qubits
        n_meas = len(measurements) if measurements else self.n_disks
        
        qreg = QuantumRegister(n_phys, 'q')
        creg = ClassicalRegister(n_meas, 'meas')
        qc = QuantumCircuit(qreg, creg, name="CTM")
        
        # === LAYER 1: OPEN PORTAL ===
        qc.h(qreg)
        
        # === LAYER 2: COLD-START GEARING (v3.1) ===
        # CRITICAL: LINK happens while disks are "fluid" - BEFORE the braid!
        # This prevents Phase Kickback by letting topology form around entanglement.
        for op in self._op_log:
            if op["op"] == "LINK":
                ctrl_disk = self.disks[op["control"]]
                tgt_disk = self.disks[op["target"]]
                
                # v3.1: Cold-start engagement
                Gearbox.engage_cold_link(
                    qc, 
                    qreg[ctrl_disk.data_qubit], 
                    qreg[tgt_disk.data_qubit]
                )
        
        # === LAYER 3: PER-DISK BRAID (SPIN) ===
        for disk in self.disks:
            p_phase = disk.phase_qubit
            p_data = disk.data_qubit
            theta = disk.theta
            
            for _ in range(self.complexity):
                qc.cz(qreg[p_phase], qreg[p_data])
                qc.rx(theta, qreg[p_phase])
                qc.rz(theta * 2, qreg[p_data])
                qc.barrier([qreg[p_phase], qreg[p_data]])
        
        # === LAYER 4: CLOSE PORTAL (SEAL) ===
        qc.h(qreg)
        
        # === LAYER 5: MEASUREMENTS (READ) ===
        targets = measurements if measurements else list(range(self.n_disks))
        for i, addr in enumerate(targets):
            disk = self.disks[addr]
            # Measure DATA bit only (the Magnitude bit)
            qc.measure(qreg[disk.data_qubit], creg[i])
        
        # Validate geometry
        self._validate_geometry(qc)
        
        return qc
    
    def _validate_geometry(self, circuit: QuantumCircuit) -> None:
        """
        Validate the Phase Lock Loop requirement.
        
        The braid must complete its full complexity cycle.
        """
        # Count operations per disk
        # For now, just ensure the circuit was built correctly
        expected_depth_per_disk = self.complexity * 4  # CZ + RX + RZ + barrier
        
        # This is a simplified check - full validation would inspect the circuit
        if circuit.depth() < self.complexity:
            raise GeometryError(
                f"Circuit depth {circuit.depth()} is less than complexity {self.complexity}. "
                "The braid operation was interrupted - geometry shattered!"
            )
    
    # =========================================================================
    # UTILITY
    # =========================================================================
    
    def dump(self) -> Dict[str, Any]:
        """Dump cylinder state for debugging."""
        return {
            "n_disks": self.n_disks,
            "complexity": self.complexity,
            "disks": [
                {
                    "address": d.address,
                    "theta": d.theta,
                    "position": d.position,
                    "phys": d.phys_indices
                }
                for d in self.disks
            ],
            "op_log": self._op_log
        }
    
    def __repr__(self) -> str:
        positions = [str(d.position) for d in self.disks]
        return f"Cylinder([{', '.join(positions)}])"


# =============================================================================
# CONVENIENCE
# =============================================================================

def create_memory(n_disks: int) -> Cylinder:
    """Create a new cylindrical memory bank."""
    mem = Cylinder(n_disks)
    mem.alloc()
    return mem
