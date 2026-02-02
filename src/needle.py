"""
Needle Driver - IBM Quantum Runtime Interface
==============================================

The hardware interface for reading/writing to the Cylindrical Topological Memory.

The "Needle" is the measurement probe that reads disk positions.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from .cylinder import Cylinder, UnitCell
from .isa import TopologyConstants


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# NEEDLE RESULT
# =============================================================================

@dataclass
class NeedleResult:
    """
    Result from a needle read operation.
    
    Attributes:
        addresses: Disk addresses that were read
        values: Measured values for each disk
        raw_counts: Raw measurement count distribution
        fidelity: Confidence in the read values
        job_id: IBM job identifier
    """
    addresses: List[int]
    values: List[int]
    raw_counts: Dict[str, int]
    fidelity: float
    job_id: str = ""
    
    def __str__(self) -> str:
        pairs = [f"D{a}={v}" for a, v in zip(self.addresses, self.values)]
        return f"NeedleResult({', '.join(pairs)}) @ {self.fidelity:.1%}"


# =============================================================================
# NEEDLE DRIVER
# =============================================================================

class NeedleDriver:
    """
    The hardware interface for CTM operations.
    
    Handles:
        - IBM Quantum connection
        - Circuit transpilation for target hardware
        - Measurement and result interpretation
        - Qubit mapping to hardware topology
        
    Example:
        >>> needle = NeedleDriver()
        >>> needle.connect()
        >>> mem = Cylinder(4)
        >>> mem.push(0, 1)  # Write 1 to disk 0
        >>> result = needle.read(mem, [0])  # Read disk 0
        >>> print(result.values[0])  # Should be 1
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 backend_name: Optional[str] = None,
                 shots: int = TopologyConstants.SHOTS):
        self.api_key = api_key
        self.backend_name = backend_name
        self.shots = shots
        
        self.service: Optional[QiskitRuntimeService] = None
        self.backend = None
        self._connected = False
    
    def connect(self) -> None:
        """Connect to IBM Quantum service."""
        if self._connected:
            return
        
        # Load credentials
        import os
        import json
        
        token = self.api_key or os.environ.get("QISKIT_IBM_TOKEN")
        
        if not token:
            # Try apikey.json
            for path in ["apikey.json", "../apikey.json"]:
                if os.path.exists(path):
                    with open(path) as f:
                        data = json.load(f)
                        token = data.get("apikey")
                        break
        
        if not token:
            raise ValueError("No IBM credentials found")
        
        logger.info("🔌 Connecting needle to IBM Quantum...")
        self.service = QiskitRuntimeService(token=token)
        
        if self.backend_name:
            self.backend = self.service.backend(self.backend_name)
        else:
            self.backend = self.service.least_busy(operational=True, simulator=False)
        
        logger.info(f"   Needle connected to: {self.backend.name}")
        self._connected = True
    
    def read(self, 
             cylinder: Cylinder, 
             addresses: Optional[List[int]] = None) -> NeedleResult:
        """
        Read disk positions from the cylinder.
        
        Args:
            cylinder: The memory cylinder to read from
            addresses: Disk addresses to read (default: all)
            
        Returns:
            NeedleResult with measured values
        """
        if not self._connected:
            self.connect()
        
        addresses = addresses or list(range(cylinder.n_disks))
        
        # Generate circuit
        circuit = cylinder.to_circuit(measurements=addresses)
        
        # Transpile for hardware
        logger.info(f"🔨 Transpiling for {self.backend.name}...")
        pm = generate_preset_pass_manager(
            backend=self.backend,
            optimization_level=3
        )
        isa_circuit = pm.run(circuit)
        
        # Execute
        logger.info(f"📖 Reading {len(addresses)} disk(s)...")
        sampler = Sampler(mode=self.backend)
        pub = (isa_circuit, None, self.shots)
        
        job = sampler.run([pub])
        job_id = job.job_id()
        logger.info(f"   Job ID: {job_id}")
        
        logger.info("   ... Waiting for needle read ...")
        result = job.result()
        
        # Extract counts
        pub_result = result[0]
        try:
            counts = pub_result.data.meas.get_counts()
        except:
            counts = {}
        
        # Decode values
        values, fidelity = self._decode_counts(counts, len(addresses))
        
        logger.info(f"✅ Read complete: {values}")
        
        return NeedleResult(
            addresses=addresses,
            values=values,
            raw_counts=counts,
            fidelity=fidelity,
            job_id=job_id
        )
    
    def read_circuit(self, circuit: QuantumCircuit) -> NeedleResult:
        """
        Execute a pre-built quantum circuit.
        
        Use for custom circuits like Anchor Sequence.
        
        Args:
            circuit: Pre-built QuantumCircuit with measurements
            
        Returns:
            NeedleResult with measured values
        """
        if not self._connected:
            self.connect()
        
        # Transpile for hardware
        logger.info(f"🔨 Transpiling for {self.backend.name}...")
        pm = generate_preset_pass_manager(
            backend=self.backend,
            optimization_level=3
        )
        isa_circuit = pm.run(circuit)
        
        # Execute
        n_classical = circuit.num_clbits
        logger.info(f"📖 Reading {n_classical} bit(s)...")
        sampler = Sampler(mode=self.backend)
        pub = (isa_circuit, None, self.shots)
        
        job = sampler.run([pub])
        job_id = job.job_id()
        logger.info(f"   Job ID: {job_id}")
        
        logger.info("   ... Waiting for needle read ...")
        result = job.result()
        
        # Extract counts
        pub_result = result[0]
        try:
            counts = pub_result.data.meas.get_counts()
        except:
            counts = {}
        
        # Decode values
        values, fidelity = self._decode_counts(counts, n_classical)
        
        logger.info(f"✅ Read complete: {values}")
        
        return NeedleResult(
            addresses=list(range(n_classical)),
            values=values,
            raw_counts=counts,
            fidelity=fidelity,
            job_id=job_id
        )
    
    def _decode_counts(self, 
                       counts: Dict[str, int], 
                       n_disks: int) -> tuple:
        """
        Decode measurement counts to disk values.
        
        Uses majority voting to determine each disk's value.
        """
        total = sum(counts.values())
        if total == 0:
            return [0] * n_disks, 0.0
        
        # Count votes for each disk position
        votes = [{0: 0, 1: 0} for _ in range(n_disks)]
        
        for bitstring, count in counts.items():
            # Pad bitstring if needed
            bits = bitstring.zfill(n_disks)
            
            for i, bit in enumerate(reversed(bits)):
                votes[i][int(bit)] += count
        
        # Majority vote
        values = []
        confidences = []
        
        for vote in votes:
            if vote[0] >= vote[1]:
                values.append(0)
                confidences.append(vote[0] / (vote[0] + vote[1]))
            else:
                values.append(1)
                confidences.append(vote[1] / (vote[0] + vote[1]))
        
        avg_fidelity = sum(confidences) / len(confidences) if confidences else 0.0
        
        return values, avg_fidelity
    
    def write_and_read(self,
                       cylinder: Cylinder,
                       writes: Dict[int, int],
                       reads: Optional[List[int]] = None) -> NeedleResult:
        """
        Write values to disks then read.
        
        Args:
            cylinder: The memory cylinder
            writes: Dict of {address: value} to write
            reads: Addresses to read after write (default: all written)
            
        Returns:
            NeedleResult with measured values
        """
        # Apply writes
        for addr, value in writes.items():
            cylinder.push(addr, value)
        
        # Read
        reads = reads or list(writes.keys())
        return self.read(cylinder, reads)


# =============================================================================
# CONVENIENCE
# =============================================================================

def quick_read(cylinder: Cylinder) -> NeedleResult:
    """Quick read of entire cylinder."""
    needle = NeedleDriver()
    return needle.read(cylinder)
