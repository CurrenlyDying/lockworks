"""
LockWorks v7.0: The Echo Chamber
=================================

Implements Hahn Spin Echo to cancel phase drift (Z-noise) before hardening.

Physics:
    Drift D(t) = exp(-i*E*t)
    Sequence: D(t/2) -> X -> D(t/2) -> X
    Result: The phase accumulated in the first half is inverted and cancelled
            by the second half.
            
The Echo is applied AFTER the X-Link but BEFORE the Braid, scrubbing
the topological noise generated during gearing.
"""

from qiskit import QuantumCircuit
from typing import List, Union


class EchoChamber:
    """
    Hahn Spin Echo for phase drift cancellation.
    
    The echo sequence time-reverses phase evolution, causing
    Z-errors to cancel out.
    """
    
    @staticmethod
    def apply_echo(
        qc: QuantumCircuit, 
        qubits: List, 
        delay_cycles: int = 0
    ) -> None:
        """
        Apply Time-Reversal sequence to scrub phase errors.
        
        Sequence:
            1. First Half Evolution (identity gates, phase accumulates)
            2. X-Flip (inverts phase frame)
            3. Second Half Evolution (phase unwinds)
            4. X-Flip (restore original basis)
        
        Args:
            qc: The quantum circuit
            qubits: List of qubits to echo (typically data bits)
            delay_cycles: Number of identity gates for wait duration.
                         If 0, uses minimal barrier-based echo.
        """
        # === 1. First Half Evolution (Forward) ===
        qc.barrier(qubits)
        for _ in range(delay_cycles):
            for q in qubits:
                qc.id(q)
        
        # === 2. THE FLIP (X-Pulse) ===
        # Inverts the phase frame: |0⟩ -> |1⟩, |1⟩ -> |0⟩
        # Z-errors become -Z errors relative to original frame
        for q in qubits:
            qc.x(q)
        
        # === 3. Second Half Evolution (Backward) ===
        # The drift continues, but now unwinds the error
        qc.barrier(qubits)
        for _ in range(delay_cycles):
            for q in qubits:
                qc.id(q)
        
        # === 4. RESTORE FRAME (Second X-Pulse) ===
        # Return to original basis
        # X·X = I, but the phase evolution has been time-reversed
        for q in qubits:
            qc.x(q)
        
        qc.barrier(qubits)
    
    @staticmethod
    def apply_cpmg(
        qc: QuantumCircuit, 
        qubits: List, 
        n_pulses: int = 2,
        delay_cycles: int = 0
    ) -> None:
        """
        Apply CPMG (Carr-Purcell-Meiboom-Gill) sequence.
        
        Multiple π-pulses for better noise suppression.
        
        Args:
            qc: The quantum circuit
            qubits: List of qubits
            n_pulses: Number of refocusing pulses (default 2)
            delay_cycles: Delay between pulses
        """
        qc.barrier(qubits)
        
        for i in range(n_pulses):
            # Delay
            for _ in range(delay_cycles):
                for q in qubits:
                    qc.id(q)
            
            # π-pulse (Y-rotation for CPMG, but X works too)
            for q in qubits:
                qc.x(q)
            
            qc.barrier(qubits)
        
        # Final delay
        for _ in range(delay_cycles):
            for q in qubits:
                qc.id(q)
        
        # Restore with even number of X gates (they cancel)
        if n_pulses % 2 == 1:
            for q in qubits:
                qc.x(q)
        
        qc.barrier(qubits)
