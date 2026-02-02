"""
LockWorks v6.4: Phase Stabilizer Audit
=======================================

Implements explicit X-basis parity constraint via H-conjugation.
This makes the X-syndrome diagnostic for phase errors.

Key Insight:
    Standard CNOT encodes Z-parity: Z_P = Z_A ⊕ Z_B
    H-conjugated CNOT encodes X-parity: X_P = X_A ⊕ X_B
    
When we measure in X-basis with X-parity encoding:
    - Baseline syndrome ≈ 0 (parity maintained)
    - Z-fault → X-basis flip → syndrome ≈ 1
    
This kills the "phase-blindness" critique.
"""

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from typing import Literal


class WitnessV64:
    """
    LockWorks v6.4: Phase Stabilizer Witness.
    
    Uses H-conjugated CNOT to encode X-parity instead of Z-parity.
    Makes phase errors (Z) visible in X-basis measurement.
    """
    
    def __init__(self, complexity: int = 6):
        self.complexity = complexity
        self.q = QuantumRegister(6, 'q')
        self.c = ClassicalRegister(3, 'meas')
        self.data_indices = [1, 3, 5]
    
    def build_phase_protected_circuit(
        self, 
        val_a: int, 
        val_b: int, 
        fault_mode: Literal['NONE', 'MID_Z', 'LATE_Z'] = 'NONE'
    ) -> QuantumCircuit:
        """
        Build circuit with X-parity encoding.
        
        Uses H-CX-H conjugation to encode X-parity instead of Z-parity.
        This makes Z-errors (phase flips) visible in X-basis.
        
        Args:
            val_a, val_b: Input values (0 = ROBUST, 1 = FISHER)
            fault_mode: NONE, MID_Z (phase fault before lock), LATE_Z (after lock)
        """
        qc = QuantumCircuit(self.q, self.c)
        
        # === 1. OPEN PORTAL - Initialize to |+⟩ ===
        qc.h(self.q)
        
        # === 2. HARDEN DATA DISKS ===
        self._braid(qc, 0, val_a)
        self._braid(qc, 1, val_b)
        
        # === 3. X-PARITY LINK (H-Conjugated) ===
        # H-CX-H transforms Z-parity CNOT into X-parity CZ-like behavior
        # This encodes: X_P = X_A ⊕ X_B
        qc.barrier()
        
        # Rotate data qubits to Z-basis
        for idx in self.data_indices:
            qc.h(self.q[idx])
        
        # Apply CNOT (now acts on Z-basis, encoding X-parity)
        qc.cx(self.q[5], self.q[1])  # Parity <- Disk A
        qc.cx(self.q[5], self.q[3])  # Parity <- Disk B
        
        # Rotate back to X-basis
        for idx in self.data_indices:
            qc.h(self.q[idx])
        
        qc.barrier()
        
        # === 4. MID PHASE FAULT (In-Manifold Z) ===
        if fault_mode == 'MID_Z':
            qc.barrier()
            qc.z(self.q[1])  # Phase flip on Disk A
            qc.barrier()
        
        # === 5. LOCK PARITY DISK ===
        self._braid(qc, 2, 0)  # Parity at ROBUST
        
        # === 6. LATE PHASE FAULT (Post-Lock Z) ===
        if fault_mode == 'LATE_Z':
            qc.barrier()
            qc.z(self.q[1])  # Phase flip after lock
            qc.barrier()
        
        # === 7. X-BASIS MEASUREMENT ===
        # Rotate to X-basis to detect phase errors as bit flips
        qc.barrier()
        for idx in self.data_indices:
            qc.h(self.q[idx])
        
        # Measure
        qc.measure(self.q[1], self.c[0])
        qc.measure(self.q[3], self.c[1])
        qc.measure(self.q[5], self.c[2])
        
        return qc
    
    def _braid(self, qc: QuantumCircuit, idx: int, val: int) -> None:
        theta = 0.196 if val == 1 else 0.0
        p = idx * 2
        d = idx * 2 + 1
        
        for _ in range(self.complexity):
            qc.cz(self.q[p], self.q[d])
            qc.rx(theta, self.q[p])
            qc.rz(theta * 2, self.q[d])
            qc.barrier([self.q[p], self.q[d]])
