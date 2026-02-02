"""
Quantum Gearbox v3.1 - Cold-Start Gearing
==========================================

CTM v3.1: Fixes Phase Kickback by linking BEFORE the braid.

Problem (v3.0):
    Phase Bias created a gradient that caused 92% leakage into |01⟩.
    Both disks flipped due to kickback during the "hot" braid phase.

Solution (v3.1):
    Cold-Start Gearing: LINK while disks are stationary (after H, before braid).
    The topological lock forms around the entanglement, not the other way around.

OSU Pattern v3.1:
    1. OPEN: ALLOC (H-gates on all)
    2. GEAR: LINK (CX on stationary disks) ← MOVED HERE
    3. SPIN: ROTATE (Apply braids to both)
    4. SEAL: SEAL (H-gates to close portal)
    5. READ: READ_NEEDLE

Mechanical Model:
    - engage_cold_link: Clean CX with barriers, no phase bias
    - Link happens in "fluid" state before topology hardens
"""

import numpy as np
from qiskit import QuantumCircuit
from typing import Sequence, Union


class Gearbox:
    """
    Manages mechanical coupling between topological disks.
    
    v3.1 COLD-START GEARING:
        - LINK occurs AFTER open-portal but BEFORE braid
        - No phase bias - clean CX only
        - Disks are "fluid" during link, then harden together
    
    Bit Mapping (CRITICAL):
        - Phase Bit = q_2k (even indices) - NEVER measured
        - Data Bit = q_2k+1 (odd indices) - The Needle readout
    """
    
    # =========================================================================
    # v3.1 COLD-START METHODS
    # =========================================================================
    
    @staticmethod
    def engage_cold_link(qc: QuantumCircuit, control_q, target_q) -> None:
        """
        Cold-Start Gear Engagement (v3.1).
        
        Engages the gear BEFORE the braid begins.
        Uses the initial 'Open Portal' energy to lock the disks.
        
        No phase bias - just clean barriers and CX.
        
        Args:
            qc: The quantum circuit
            control_q: Control DATA qubit (q_2k+1)
            target_q: Target DATA qubit (q_2j+1)
        """
        qc.barrier(control_q, target_q)
        qc.cx(control_q, target_q)
        qc.barrier(control_q, target_q)
    
    @staticmethod
    def engage_cold_symmetric(qc: QuantumCircuit, control_q, target_q) -> None:
        """
        Symmetric Cold-Start with bidirectional CX.
        
        Use for maximum entanglement strength.
        """
        qc.barrier(control_q, target_q)
        qc.cx(control_q, target_q)
        qc.cx(target_q, control_q)
        qc.cx(control_q, target_q)
        qc.barrier(control_q, target_q)
    
    # =========================================================================
    # LEGACY METHODS (for backward compatibility)
    # =========================================================================
    
    @staticmethod
    def sync_clutch(qc: QuantumCircuit, *qubits) -> None:
        """Isolates the LINK from braid pulses."""
        if qubits:
            qc.barrier(*qubits)
        else:
            qc.barrier()
    
    @staticmethod
    def shift_gear(qc: QuantumCircuit, control_qubit, target_qubit) -> None:
        """Legacy: Now uses Cold-Start."""
        Gearbox.engage_cold_link(qc, control_qubit, target_qubit)
    
    @staticmethod
    def engage_internal_gear(qc: QuantumCircuit, control_q, target_q) -> None:
        """Legacy: Now uses Cold-Start."""
        Gearbox.engage_cold_link(qc, control_q, target_q)
    
    # =========================================================================
    # v1.2 INTERNAL SYNCHRONIZATION (preserved for compatibility)
    # =========================================================================
    
    @staticmethod
    def sync_clutch(qc: QuantumCircuit, *qubits) -> None:
        """Isolates the LINK from braid pulses."""
        if qubits:
            qc.barrier(*qubits)
        else:
            qc.barrier()
    
    @staticmethod
    def rev_match(qc: QuantumCircuit, *qubits) -> None:
        """Identity sequence to stabilize phase before engagement."""
        for q in qubits:
            qc.x(q)
            qc.x(q)
    
    @staticmethod
    def engage_internal_gear(qc: QuantumCircuit, control_q, target_q) -> None:
        """
        v3.0: Uses phase-biased gearing.
        """
        Gearbox.shift_biased_gear(qc, control_q, target_q)
    
    @staticmethod
    def engage_symmetric_gear(qc: QuantumCircuit, control_q, target_q) -> None:
        """v3.0: Symmetric gear with bias on both qubits."""
        Gearbox.shift_double_biased(qc, control_q, target_q)
    
    # =========================================================================
    # LEGACY v1.1 METHODS (for backward compatibility)
    # =========================================================================
    
    @staticmethod
    def clutch_in(qc: QuantumCircuit, *qubits) -> None:
        """Legacy: Disengages compiler optimization (Barrier)."""
        Gearbox.sync_clutch(qc, *qubits)
    
    @staticmethod
    def idle_throttle(qc: QuantumCircuit, *qubits) -> None:
        """Legacy: Dynamical Decoupling (X-X)."""
        Gearbox.rev_match(qc, *qubits)
    
    @staticmethod
    def shift_gear(qc: QuantumCircuit, control_qubit, target_qubit) -> None:
        """Legacy v1.1: Now uses v3.0 phase bias."""
        Gearbox.shift_biased_gear(qc, control_qubit, target_qubit)
    
    @staticmethod
    def double_shift(qc: QuantumCircuit, control_qubit, target_qubit) -> None:
        """Legacy: Now uses v3.0 double bias."""
        Gearbox.shift_double_biased(qc, control_qubit, target_qubit)
    
    @staticmethod
    def echo_shift(qc: QuantumCircuit, control_qubit, target_qubit) -> None:
        """Spin Echo protected shift with phase bias."""
        Gearbox.sync_clutch(qc, control_qubit, target_qubit)
        Gearbox.apply_phase_bias(qc, target_qubit, direction=1)
        qc.x(control_qubit)
        qc.cx(control_qubit, target_qubit)
        qc.x(control_qubit)
        Gearbox.apply_phase_bias(qc, target_qubit, direction=-1)
        Gearbox.sync_clutch(qc, control_qubit, target_qubit)
    
    @staticmethod
    def double_idle(qc: QuantumCircuit, *qubits) -> None:
        """Extended Dynamical Decoupling (DD-4)."""
        for q in qubits:
            qc.x(q)
            qc.x(q)
            qc.x(q)
            qc.x(q)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def protected_cnot(qc: QuantumCircuit, ctrl, tgt) -> None:
    """Apply a Zeta-regularized CNOT (v1.3)."""
    Gearbox.shift_regularized_gear(qc, ctrl, tgt)


def protected_cx_chain(qc: QuantumCircuit, qubits: Sequence) -> None:
    """Apply a chain of regularized CNOTs: q0 → q1 → q2 → ..."""
    for i in range(len(qubits) - 1):
        Gearbox.shift_regularized_gear(qc, qubits[i], qubits[i + 1])


