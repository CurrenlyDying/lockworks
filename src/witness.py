"""
LockWorks v6.0: Parity Witness
===============================

The Fault-Tolerant Proof.
Implements 3-Disk Parity with:
    - Correct CX direction (inverted per v3.2)
    - X-basis tomography support
    - Fault injection integration
"""

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from typing import Optional, Literal

from .fault_engine import FaultEngine


class ParityWitness:
    """
    LockWorks v6.0: 3-Disk Parity with Fault Detection.
    
    Architecture:
        Disk 0 (q0, q1): Data A
        Disk 1 (q2, q3): Data B
        Disk 2 (q4, q5): Parity (A XOR B)
    
    Corrected CX Direction:
        LINK uses inverted CX: CX(parity_data, source_data)
        This aligns with ibm_fez native topology.
    """
    
    def __init__(self, complexity: int = 6):
        """
        Initialize Parity Witness.
        
        Args:
            complexity: Braid layers (C parameter)
        """
        self.complexity = complexity
        self.q = QuantumRegister(6, 'q')  # 3 Disks × 2 qubits
        self.c = ClassicalRegister(3, 'meas')
        self.qc = QuantumCircuit(self.q, self.c)
        
        # Data qubit indices (odd indices per CTM spec)
        self.data_indices = [1, 3, 5]  # data_0, data_1, parity_data
    
    def build_protected_circuit(
        self, 
        val_a: int, 
        val_b: int, 
        inject_fault: bool = False,
        fault_target: int = 0,  # Which disk to fault (0, 1, or 2)
        basis: Literal['Z', 'X'] = 'Z',
        use_baseline: bool = False  # Use identity instead of braid
    ) -> QuantumCircuit:
        """
        Build the parity witness circuit.
        
        Args:
            val_a: Value for Disk 0 (0 or 1)
            val_b: Value for Disk 1 (0 or 1)
            inject_fault: Whether to inject X error
            fault_target: Which disk to inject fault into
            basis: Measurement basis ('Z' or 'X')
            use_baseline: If True, use identity gates instead of braid
            
        Returns:
            The constructed QuantumCircuit
        """
        # Reset circuit
        self.qc = QuantumCircuit(self.q, self.c)
        
        # === LAYER 1: OPEN PORTAL ===
        self.qc.h(self.q)
        
        # === LAYER 2: HARDEN DATA DISKS ===
        if use_baseline:
            # Depth-matched identity (no topology)
            FaultEngine.noise_baseline(
                self.qc, 
                [self.q[i] for i in range(4)],  # Disk 0 and 1 qubits
                self.complexity * 3  # Match gate count roughly
            )
        else:
            self._braid_disk(0, val_a)
            self._braid_disk(1, val_b)
        
        # === LAYER 3: GEAR-SYNC (Corrected Direction) ===
        # Inverted CX: CX(target=parity, control=source)
        self.qc.barrier()
        
        # LINK(0, 2): Parity <- Disk 0
        self.qc.cx(self.q[5], self.q[1])
        
        # LINK(1, 2): Parity <- Disk 1
        self.qc.cx(self.q[5], self.q[3])
        
        self.qc.barrier()
        
        # === LAYER 4: LOCK PARITY DISK ===
        if use_baseline:
            FaultEngine.noise_baseline(
                self.qc,
                [self.q[4], self.q[5]],
                self.complexity * 3
            )
        else:
            self._braid_disk(2, 0)  # Parity disk starts at ROBUST
        
        # === LAYER 5: FAULT INJECTION ===
        if inject_fault:
            target_qubit = self.data_indices[fault_target]
            FaultEngine.inject_bit_flip(self.qc, self.q[target_qubit])
        
        # === LAYER 6: SEAL & MEASURE ===
        if basis == 'X':
            # X-basis: Apply H only to data qubits before measure
            self.qc.barrier()
            for idx in self.data_indices:
                self.qc.h(self.q[idx])
        elif basis == 'Z':
            # Z-basis: Global H closure (standard CTM)
            self.qc.h(self.q)
        
        # Measure data bits
        self.qc.measure(self.q[1], self.c[0])   # Disk 0
        self.qc.measure(self.q[3], self.c[1])   # Disk 1
        self.qc.measure(self.q[5], self.c[2])   # Parity
        
        return self.qc
    
    def _braid_disk(self, disk_idx: int, value: int) -> None:
        """
        Apply braid kernel to a disk.
        
        Args:
            disk_idx: Disk index (0, 1, or 2)
            value: Target value (0 = ROBUST, 1 = FISHER)
        """
        theta = 0.196 if value == 1 else 0.0
        p = disk_idx * 2      # Phase qubit (even)
        d = disk_idx * 2 + 1  # Data qubit (odd)
        
        for _ in range(self.complexity):
            self.qc.cz(self.q[p], self.q[d])
            self.qc.rx(theta, self.q[p])
            self.qc.rz(theta * 2, self.q[d])
            self.qc.barrier([self.q[p], self.q[d]])
    
    def get_circuit(self) -> QuantumCircuit:
        """Return the current circuit."""
        return self.qc
