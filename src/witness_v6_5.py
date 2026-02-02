"""
LockWorks v6.5: Phase-Locked Loop (PLL)
========================================

Moves the Braid Kernel to AFTER the X-Link to protect the stabilizer.

The v6.4 Autopsy:
    Problem: Braid was applied BEFORE X-Link, leaving the entangled
    state exposed to phase drift.
    
The Fix:
    Sequence: OPEN → X-LINK → FAULT → BRAID → MEASURE
    The Braid now "heals" any phase error introduced during linking.

Key Insight:
    We're not just preventing errors - we're CORRECTING them
    by applying the topological sink AFTER the fault.
"""

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from typing import Literal


class WitnessV65:
    """
    LockWorks v6.5: Phase-Locked Loop.
    
    Moves the Braid Kernel to AFTER the X-Link to protect the stabilizer.
    Tests if the Braid can actively correct phase errors.
    """
    
    def __init__(self, complexity: int = 6):
        self.complexity = complexity
        self.q = QuantumRegister(6, 'q')
        self.c = ClassicalRegister(3, 'meas')
        self.data_indices = [1, 3, 5]
    
    def build_pll_circuit(
        self, 
        val_a: int, 
        val_b: int, 
        fault_mode: Literal['NONE', 'MID_Z', 'LATE_Z'] = 'NONE'
    ) -> QuantumCircuit:
        """
        Build Phase-Locked Loop circuit.
        
        Sequence:
            1. OPEN: Initialize |+⟩
            2. X-LINK: Establish X_P = X_A ⊕ X_B
            3. MID_FAULT (optional): Inject Z error BEFORE braid
            4. BRAID: Apply topological hardening (should heal MID fault)
            5. LATE_FAULT (optional): Inject Z error AFTER braid
            6. MEASURE: X-basis readout
        
        Args:
            val_a, val_b: Disk values (for braid theta)
            fault_mode: NONE, MID_Z (pre-braid), LATE_Z (post-braid)
        """
        qc = QuantumCircuit(self.q, self.c)
        
        # === 1. OPEN PORTAL ===
        qc.h(self.q)
        
        # === 2. X-PARITY LINK (Immediate Gearing) ===
        # Establish X-correlation FIRST, before any hardening
        qc.barrier()
        for idx in self.data_indices:
            qc.h(self.q[idx])
        
        qc.cx(self.q[5], self.q[1])  # Parity <- Disk A
        qc.cx(self.q[5], self.q[3])  # Parity <- Disk B
        
        for idx in self.data_indices:
            qc.h(self.q[idx])
        qc.barrier()
        
        # === 3. MID PHASE FAULT (Pre-Braid) ===
        # Inject Z error BEFORE the braid
        # If PLL works, the braid should "heal" this error
        if fault_mode == 'MID_Z':
            qc.barrier()
            qc.z(self.q[1])  # Phase flip on Disk A
            qc.barrier()
        
        # === 4. TOPOLOGICAL HARDENING (The Shield) ===
        # Apply Braid AFTER link AND fault to heal phase errors
        self._braid(qc, 0, val_a)
        self._braid(qc, 1, val_b)
        self._braid(qc, 2, 0)  # Parity lock at ROBUST
        
        # === 5. LATE PHASE FAULT (Post-Braid) ===
        # Inject Z error AFTER the braid
        # This should NOT be healed (manifold already complete)
        if fault_mode == 'LATE_Z':
            qc.barrier()
            qc.z(self.q[1])
            qc.barrier()
        
        # === 6. MEASURE (X-Basis) ===
        for idx in self.data_indices:
            qc.h(self.q[idx])
        
        qc.measure(self.q[1], self.c[0])
        qc.measure(self.q[3], self.c[1])
        qc.measure(self.q[5], self.c[2])
        
        return qc
    
    def _braid(self, qc: QuantumCircuit, idx: int, val: int) -> None:
        """Apply braid kernel to a disk."""
        theta = 0.196 if val == 1 else 0.0
        p = idx * 2
        d = idx * 2 + 1
        
        for _ in range(self.complexity):
            qc.cz(self.q[p], self.q[d])
            qc.rx(theta, self.q[p])
            qc.rz(theta * 2, self.q[d])
            qc.barrier([self.q[p], self.q[d]])
