"""
LockWorks v6.2: The Geometric Gantlet
======================================

Frame-Matched Fault Injection to prove the manifold absorbs logical
faults regardless of basis transformation.

The Challenge:
    Reviewer claims: "MID-X becomes Z after H, so it's just hidden"
    
The Test:
    Case A (MID-X): Inject X before Seal → Effective Z after H
    Case B (LATE-Z): Inject Z after Seal → Effective Z directly
    
If SVR_matched = Syndrome(LATE-Z) / Syndrome(MID-X) > 10:
    The manifold actively absorbs faults, not just hides them.
"""

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from typing import Literal


class WitnessV62:
    """
    LockWorks v6.2: Frame-Matched Fault Injection.
    
    Implements MID-X vs LATE-Z comparison to defeat the HXH=Z critique.
    """
    
    def __init__(self, complexity: int = 6):
        self.complexity = complexity
        self.q = QuantumRegister(6, 'q')
        self.c = ClassicalRegister(3, 'meas')
    
    def build_test_circuit(
        self, 
        val_a: int, 
        val_b: int, 
        fault_mode: Literal['NONE', 'MID_X', 'MID_Z', 'LATE_X', 'LATE_Z'] = 'NONE',
        settle_cycles: int = 0  # Extra idle between fault and seal
    ) -> QuantumCircuit:
        """
        Build circuit with frame-matched fault injection.
        
        Args:
            val_a: Value for Disk A
            val_b: Value for Disk B
            fault_mode:
                'NONE': No fault
                'MID_X': X before Seal (becomes effective Z)
                'MID_Z': Z before Seal (becomes effective X)
                'LATE_X': X after Seal
                'LATE_Z': Z after Seal (frame-matched to MID_X)
            settle_cycles: Extra identity cycles between MID fault and seal
        """
        qc = QuantumCircuit(self.q, self.c)
        data_indices = [1, 3, 5]
        
        # === 1. OPEN PORTAL ===
        qc.h(self.q)
        
        # === 2. HARDEN DATA DISKS ===
        self._braid(qc, 0, val_a)
        self._braid(qc, 1, val_b)
        
        # === 3. GEAR-SYNC ===
        qc.barrier()
        qc.cx(self.q[5], self.q[1])
        qc.cx(self.q[5], self.q[3])
        qc.barrier()
        
        # === 4. LOCK PARITY ===
        self._braid(qc, 2, 0)
        
        # === 5. MID FAULT INJECTION ===
        if fault_mode == 'MID_X':
            qc.barrier()
            qc.x(self.q[1])  # X before H → effective Z
            qc.barrier()
        elif fault_mode == 'MID_Z':
            qc.barrier()
            qc.z(self.q[1])  # Z before H → effective X
            qc.barrier()
        
        # === 5.5. SETTLE TIME (optional) ===
        for _ in range(settle_cycles):
            qc.id(self.q[1])
            qc.barrier()
        
        # === 6. SEAL ===
        qc.h(self.q)
        
        # === 7. LATE FAULT INJECTION ===
        if fault_mode == 'LATE_X':
            qc.barrier()
            qc.x(self.q[1])
            qc.barrier()
        elif fault_mode == 'LATE_Z':
            qc.barrier()
            qc.z(self.q[1])  # Z after H → frame-matched to MID_X
            qc.barrier()
        
        # === 8. MEASURE ===
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
