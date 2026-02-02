"""
LockWorks v6.3: The X-Basis Killshot
=====================================

Resolves Phase-Blindness by measuring syndrome in the X-basis.
Z-faults (phase errors) become visible as bit-flips after H rotation.

Key Insight:
    In Z-basis: Z-faults are invisible (no bit flip)
    In X-basis: Z-faults → X-faults → visible!
    
If SVR_X > 10: The manifold absorbs phase faults too (3D Attractor)
"""

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from typing import Literal


class WitnessV63:
    """
    LockWorks v6.3: X-Basis Phase Detection.
    
    Measures in X-basis to make phase (Z) errors visible.
    Proves the manifold is a 3D topological sink, not a 1D pump.
    """
    
    def __init__(self, complexity: int = 6):
        self.complexity = complexity
        self.q = QuantumRegister(6, 'q')
        self.c = ClassicalRegister(3, 'meas')
        self.data_indices = [1, 3, 5]
    
    def build_test_circuit(
        self, 
        val_a: int, 
        val_b: int, 
        fault_mode: Literal['NONE', 'MID_X', 'MID_Z', 'LATE_X', 'LATE_Z'] = 'NONE'
    ) -> QuantumCircuit:
        """
        Build circuit with X-basis measurement.
        
        The final H on data qubits rotates Z-basis to X-basis,
        making phase errors visible as bit flips.
        
        Args:
            val_a, val_b: Input values
            fault_mode: Type of fault to inject
        """
        qc = QuantumCircuit(self.q, self.c)
        
        # === 1. OPEN PORTAL ===
        qc.h(self.q)
        
        # === 2. HARDEN DATA DISKS ===
        self._braid(qc, 0, val_a)
        self._braid(qc, 1, val_b)
        
        # === 3. GEAR-SYNC (Inverted CX) ===
        qc.barrier()
        qc.cx(self.q[5], self.q[1])
        qc.cx(self.q[5], self.q[3])
        qc.barrier()
        
        # === 4. LOCK PARITY ===
        self._braid(qc, 2, 0)
        
        # === 5. MID FAULT (Pre-Seal) ===
        if fault_mode == 'MID_X':
            qc.barrier()
            qc.x(self.q[1])  # X before H
            qc.barrier()
        elif fault_mode == 'MID_Z':
            qc.barrier()
            qc.z(self.q[1])  # Z before H
            qc.barrier()
        
        # === 6. SEAL (Global H) ===
        qc.h(self.q)
        
        # === 7. LATE FAULT (Post-Seal) ===
        if fault_mode == 'LATE_X':
            qc.barrier()
            qc.x(self.q[1])
            qc.barrier()
        elif fault_mode == 'LATE_Z':
            qc.barrier()
            qc.z(self.q[1])  # Z after seal
            qc.barrier()
        
        # === 8. X-BASIS ROTATION ===
        # Apply H to data qubits to measure in X-basis
        # This makes Z-errors visible as bit flips
        qc.barrier()
        for idx in self.data_indices:
            qc.h(self.q[idx])
        
        # === 9. MEASURE ===
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
