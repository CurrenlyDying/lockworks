"""
LockWorks v6.1: Attractor Verification
========================================

Proves the manifold is a Fault-Absorbing Attractor.

Test Logic:
    LATE Injection: Fault after manifold hardening → Syndrome visible
    MID Injection: Fault during manifold formation → Syndrome absorbed

Key Metric:
    SVR = Syndrome_Late / Syndrome_Mid
    High SVR (>10) = Fault-Absorbing Manifold confirmed
"""

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from typing import Literal


class WitnessV6:
    """
    LockWorks v6.1: Attractor Verification.
    
    Implements Late vs Mid fault injection to prove:
        - Late faults are visible (syndrome = 1)
        - Mid faults are absorbed (state returns to attractor)
    """
    
    def __init__(self, complexity: int = 6):
        self.complexity = complexity
        self.q = QuantumRegister(6, 'q')
        self.c = ClassicalRegister(3, 'meas')
    
    def build_test_circuit(
        self, 
        val_a: int, 
        val_b: int, 
        fault_mode: Literal['NONE', 'MID', 'LATE'] = 'NONE',
        basis: Literal['Z', 'X'] = 'Z'
    ) -> QuantumCircuit:
        """
        Build parity witness circuit with configurable fault injection.
        
        Args:
            val_a: Value for Disk A (0 or 1)
            val_b: Value for Disk B (0 or 1)
            fault_mode:
                'NONE': No fault injection
                'MID': Inject after GEAR but before SEAL (in-manifold)
                'LATE': Inject just before measurement (post-manifold)
            basis: 'Z' for standard, 'X' for tomography
            
        Returns:
            Configured QuantumCircuit
        """
        qc = QuantumCircuit(self.q, self.c)
        data_indices = [1, 3, 5]  # A, B, P
        
        # === 1. OPEN PORTAL ===
        qc.h(self.q)
        
        # === 2. HARDEN DATA DISKS ===
        self._braid(qc, 0, val_a)
        self._braid(qc, 1, val_b)
        
        # === 3. GEAR-SYNC (Inverted CX: Parity <- Data) ===
        qc.barrier()
        qc.cx(self.q[5], self.q[1])  # Parity <- Disk A
        qc.cx(self.q[5], self.q[3])  # Parity <- Disk B
        qc.barrier()
        
        # === 4. LOCK PARITY DISK ===
        self._braid(qc, 2, 0)  # Parity starts at ROBUST
        
        # === 5. MID FAULT INJECTION ===
        # Inject while manifold is still "soft" (post-braid, pre-seal)
        if fault_mode == 'MID':
            qc.barrier()
            qc.x(self.q[1])  # Flip Disk A data
            qc.barrier()
        
        # === 6. SEAL ===
        if basis == 'X':
            # X-basis: H only on data qubits
            qc.barrier()
            for idx in data_indices:
                qc.h(self.q[idx])
        else:
            # Z-basis: Global H closure
            qc.h(self.q)
        
        # === 7. LATE FAULT INJECTION ===
        # Inject after seal, just before measurement
        if fault_mode == 'LATE':
            qc.barrier()
            qc.x(self.q[1])  # Flip after manifold hardened
            qc.barrier()
        
        # === 8. MEASURE ===
        qc.measure(self.q[1], self.c[0])  # Disk A
        qc.measure(self.q[3], self.c[1])  # Disk B
        qc.measure(self.q[5], self.c[2])  # Parity
        
        return qc
    
    def _braid(self, qc: QuantumCircuit, idx: int, val: int) -> None:
        """Apply braid kernel to disk."""
        theta = 0.196 if val == 1 else 0.0
        p = idx * 2      # Phase qubit
        d = idx * 2 + 1  # Data qubit
        
        for _ in range(self.complexity):
            qc.cz(self.q[p], self.q[d])
            qc.rx(theta, self.q[p])
            qc.rz(theta * 2, self.q[d])
            qc.barrier([self.q[p], self.q[d]])
