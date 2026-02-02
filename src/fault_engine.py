"""
LockWorks Fault Engine
======================

Simulates environmental 'Torque' by injecting controlled bit-flips.
Used to prove the Parity Witness is not just 'shaping' but 'protecting'.
"""

from qiskit import QuantumCircuit
from typing import List, Union


class FaultEngine:
    """
    Controlled fault injection for resilience testing.
    
    Provides:
        - Single bit-flip injection
        - Depth-matched identity baseline
        - Phase-flip injection
    """
    
    @staticmethod
    def inject_bit_flip(
        qc: QuantumCircuit, 
        target_qubit: Union[int, 'Qubit'],
        barrier: bool = True
    ) -> None:
        """
        Injects an X (bit-flip) error at a specific point.
        
        Args:
            qc: The quantum circuit
            target_qubit: Qubit to flip
            barrier: Whether to add isolation barriers
        """
        if barrier:
            qc.barrier(target_qubit)
        qc.x(target_qubit)  # The Fault
        if barrier:
            qc.barrier(target_qubit)
    
    @staticmethod
    def inject_phase_flip(
        qc: QuantumCircuit, 
        target_qubit: Union[int, 'Qubit'],
        barrier: bool = True
    ) -> None:
        """
        Injects a Z (phase-flip) error.
        
        Args:
            qc: The quantum circuit
            target_qubit: Qubit to flip
            barrier: Whether to add isolation barriers
        """
        if barrier:
            qc.barrier(target_qubit)
        qc.z(target_qubit)
        if barrier:
            qc.barrier(target_qubit)
    
    @staticmethod
    def noise_baseline(
        qc: QuantumCircuit, 
        qubits: List[Union[int, 'Qubit']], 
        depth: int
    ) -> None:
        """
        Applies Identity gates instead of Braids.
        
        Provides a depth-matched 'Ohio' baseline for comparison.
        This ensures we're measuring topology benefit, not just gate count.
        
        Args:
            qc: The quantum circuit
            qubits: Qubits to apply identity to
            depth: Number of identity layers
        """
        for _ in range(depth):
            for q in qubits:
                qc.id(q)
            qc.barrier(qubits)
    
    @staticmethod
    def random_pauli(
        qc: QuantumCircuit,
        target_qubit: Union[int, 'Qubit'],
        error_type: str = 'X'
    ) -> None:
        """
        Applies a Pauli error.
        
        Args:
            qc: The quantum circuit
            target_qubit: Qubit to affect
            error_type: 'X', 'Y', or 'Z'
        """
        qc.barrier(target_qubit)
        if error_type == 'X':
            qc.x(target_qubit)
        elif error_type == 'Y':
            qc.y(target_qubit)
        elif error_type == 'Z':
            qc.z(target_qubit)
        qc.barrier(target_qubit)
