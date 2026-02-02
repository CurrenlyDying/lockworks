"""
GambitExecutionManager: IBM Quantum Runtime
============================================

Handles execution of Gambit circuits on IBM Quantum hardware.

Features:
    - Automatic credential loading (env or apikey.json)
    - Session vs Job mode detection (Open vs Standard plan)
    - Result decoding and dominance checking
    - Experiment logging and JSON export
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np

from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from .isa import (
    TopologyConstants,
    decode_physical_to_logical,
    calculate_dominance,
    hellinger_distance,
)


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# RESULT CONTAINER
# =============================================================================

@dataclass
class GambitResult:
    """
    Container for Gambit execution results.
    
    Attributes:
        counts: Raw measurement counts
        dominance: Top state probability
        top_state: Most frequent physical state
        logical_values: Decoded logical bit values
        is_decohered: True if dominance < threshold
        z_score: Signal strength vs noise
        purity: Sum of squared probabilities
        job_id: IBM job identifier
        backend: Backend name
        metadata: Additional experiment data
    """
    counts: Dict[str, int]
    dominance: float
    top_state: str
    logical_values: List[int]
    is_decohered: bool
    z_score: float = 0.0
    purity: float = 0.0
    job_id: str = ""
    backend: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        status = "⚠️ DECOHERED" if self.is_decohered else "✅ COHERENT"
        return (
            f"GambitResult({status})\n"
            f"  Top State: |{self.top_state}⟩ @ {self.dominance:.2%}\n"
            f"  Logical: {self.logical_values}\n"
            f"  Z-Score: {self.z_score:.2f}σ"
        )


# =============================================================================
# CREDENTIAL MANAGER
# =============================================================================

class CredentialManager:
    """Manages IBM Quantum credentials."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
    
    def load_credentials(self, search_dir: Optional[str] = None) -> str:
        """
        Load IBM credentials from environment or apikey.json.
        
        Priority:
            1. Provided api_key
            2. QISKIT_IBM_TOKEN environment variable
            3. apikey.json in search_dir
            4. apikey.json in current directory
            
        Returns:
            The API token
            
        Raises:
            ValueError if no credentials found
        """
        if self.api_key:
            logger.info("🔑 Using provided API key")
            return self.api_key
        
        # Environment variable
        token = os.environ.get("QISKIT_IBM_TOKEN")
        if token:
            logger.info("🔑 Loaded token from QISKIT_IBM_TOKEN")
            return token
        
        # Search for apikey.json
        search_paths = []
        if search_dir:
            search_paths.append(os.path.join(search_dir, "apikey.json"))
        search_paths.append(os.path.join(os.getcwd(), "apikey.json"))
        search_paths.append(os.path.join(os.path.dirname(__file__), "..", "apikey.json"))
        
        for path in search_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                        if 'apikey' in data:
                            logger.info(f"🔑 Loaded token from {path}")
                            return data['apikey']
                except Exception as e:
                    logger.warning(f"⚠️ Could not load {path}: {e}")
        
        raise ValueError(
            "No IBM credentials found. Please either:\n"
            "  - Set QISKIT_IBM_TOKEN environment variable\n"
            "  - Create apikey.json with {'apikey': 'your-token'}"
        )


# =============================================================================
# EXECUTION MANAGER
# =============================================================================

class GambitExecutionManager:
    """
    Manages execution of Gambit circuits on IBM Quantum.
    
    Features:
        - Automatic backend selection
        - Session vs Job mode detection
        - Result analysis and verification
    
    Example:
        >>> manager = GambitExecutionManager()
        >>> result = manager.run(circuit, shots=4096)
        >>> print(f"Dominance: {result.dominance:.2%}")
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 backend_name: Optional[str] = None,
                 shots: int = TopologyConstants.SHOTS):
        self.cred_manager = CredentialManager(api_key)
        self.backend_name = backend_name
        self.shots = shots
        self.service: Optional[QiskitRuntimeService] = None
        self.backend = None
        self._is_connected = False
    
    def connect(self) -> None:
        """Connect to IBM Quantum service."""
        if self._is_connected:
            return
        
        token = self.cred_manager.load_credentials()
        logger.info("🔌 Connecting to IBM Quantum...")
        
        self.service = QiskitRuntimeService(token=token)
        
        if self.backend_name:
            self.backend = self.service.backend(self.backend_name)
            logger.info(f"🎯 Selected backend: {self.backend.name}")
        else:
            self.backend = self.service.least_busy(operational=True, simulator=False)
            logger.info(f"🚀 Auto-selected: {self.backend.name} (least busy)")
        
        self._is_connected = True
    
    def run(self, 
            circuit: QuantumCircuit,
            shots: Optional[int] = None,
            optimization_level: int = 3) -> GambitResult:
        """
        Run a circuit on IBM hardware.
        
        Args:
            circuit: The quantum circuit to run
            shots: Number of shots (default: class default)
            optimization_level: Transpiler optimization (0-3)
            
        Returns:
            GambitResult with analysis
        """
        if not self._is_connected:
            self.connect()
        
        shots = shots or self.shots
        
        # Transpile
        logger.info(f"🔨 Transpiling for {self.backend.name}...")
        pm = generate_preset_pass_manager(
            backend=self.backend,
            optimization_level=optimization_level
        )
        isa_circuit = pm.run(circuit)
        
        # Execute
        logger.info(f"🚀 Submitting job ({shots} shots)...")
        sampler = Sampler(mode=self.backend)
        pub = (isa_circuit, None, shots)
        
        job = sampler.run([pub])
        job_id = job.job_id()
        logger.info(f"   → JOB ID: {job_id}")
        
        logger.info("   ... Waiting for execution ...")
        result = job.result()
        logger.info("✅ Execution complete!")
        
        # Extract counts
        pub_result = result[0]
        
        # Handle different result formats
        try:
            counts = pub_result.data.meas.get_counts()
        except AttributeError:
            # Try other common attribute names
            for attr in dir(pub_result.data):
                if not attr.startswith('_'):
                    try:
                        counts = getattr(pub_result.data, attr).get_counts()
                        break
                    except:
                        continue
            else:
                raise RuntimeError("Could not extract counts from result")
        
        # Analyze
        return self._analyze_result(counts, shots, job_id)
    
    def run_batch(self,
                  circuits: List[QuantumCircuit],
                  shots: Optional[int] = None,
                  optimization_level: int = 3) -> List[GambitResult]:
        """
        Run multiple circuits in a batch.
        
        Args:
            circuits: List of quantum circuits
            shots: Number of shots per circuit
            optimization_level: Transpiler optimization
            
        Returns:
            List of GambitResult objects
        """
        if not self._is_connected:
            self.connect()
        
        shots = shots or self.shots
        
        # Transpile all
        logger.info(f"🔨 Transpiling {len(circuits)} circuits...")
        pm = generate_preset_pass_manager(
            backend=self.backend,
            optimization_level=optimization_level
        )
        isa_circuits = pm.run(circuits)
        
        # Create PUBs
        pubs = [(c, None, shots) for c in isa_circuits]
        
        # Execute
        logger.info(f"🚀 Submitting batch ({len(pubs)} circuits, {shots} shots each)...")
        sampler = Sampler(mode=self.backend)
        job = sampler.run(pubs)
        job_id = job.job_id()
        logger.info(f"   → JOB ID: {job_id}")
        
        logger.info("   ... Waiting for batch execution ...")
        result = job.result()
        logger.info("✅ Batch complete!")
        
        # Analyze each result
        results = []
        for pub_result in result:
            try:
                counts = pub_result.data.meas.get_counts()
            except:
                counts = {}
            results.append(self._analyze_result(counts, shots, job_id))
        
        return results
    
    def _analyze_result(self, 
                        counts: Dict[str, int], 
                        shots: int,
                        job_id: str = "") -> GambitResult:
        """Analyze measurement counts and create result."""
        # Dominance calculation
        dominance, top_state, is_decohered = calculate_dominance(counts)
        
        # Decode logical values - handle variable bit widths
        logical_values = []
        for state in sorted(counts.keys()):
            # For multi-qubit, decode each pair of bits
            # For single bit, just use the bit value
            if len(state) >= 2:
                # Decode pairs (each logical qubit = 2 physical)
                for i in range(0, len(state), 2):
                    if i + 1 < len(state):
                        pair = state[i:i+2]
                        logical_values.append(1 if pair[0] == '1' else 0)
                    else:
                        # Odd bit at end
                        logical_values.append(int(state[i]))
            else:
                # Single bit state
                logical_values.append(int(state))
            break  # Only decode top state once
        
        # Calculate metrics - adapt to actual state width
        bit_width = len(top_state) if top_state else 2
        num_states = 2 ** bit_width
        
        # Generate all possible states for this width
        all_states = [format(i, f'0{bit_width}b') for i in range(num_states)]
        obs_dist = np.array([counts.get(k, 0) for k in all_states])
        obs_prob = obs_dist / max(shots, 1)
        
        # Purity (trace of rho^2)
        purity = float(np.sum(obs_prob ** 2))
        
        # Hellinger distance from uniform
        uniform_prob = np.ones(num_states) / num_states
        h_dist = hellinger_distance(obs_prob, uniform_prob)
        
        # Z-Score (based on null distribution - scaled for state count)
        # These constants are for 2-qubit, scale for others
        NULL_MEAN = 0.008 * (4 / num_states)
        NULL_STD = 0.0037 * (4 / num_states)
        z_score = (h_dist - NULL_MEAN) / max(NULL_STD, 0.001)
        
        return GambitResult(
            counts=counts,
            dominance=dominance,
            top_state=top_state,
            logical_values=logical_values,
            is_decohered=is_decohered,
            z_score=z_score,
            purity=purity,
            job_id=job_id,
            backend=self.backend.name if self.backend else "",
            metadata={
                "shots": shots,
                "hellinger": h_dist,
                "bit_width": bit_width,
            }
        )
    
    def verify_dominance(self, result: GambitResult) -> bool:
        """
        Verify result meets Sigma Standard (85% dominance).
        
        Returns:
            True if result passes verification
        """
        if result.is_decohered:
            logger.warning(
                f"⚠️ DECOHERED: Dominance {result.dominance:.2%} < "
                f"{TopologyConstants.DOMINANCE_THRESHOLD:.0%}"
            )
            return False
        
        logger.info(f"✅ VERIFIED: Dominance {result.dominance:.2%}")
        return True


# =============================================================================
# EXPERIMENT LOGGER
# =============================================================================

class ExperimentLogger:
    """Logs experiment results to files."""
    
    def __init__(self, output_dir: str = "."):
        self.output_dir = output_dir
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def log_result(self, result: GambitResult, name: str = "experiment"):
        """Log a single result to JSON."""
        filename = f"{name}_{self.timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        data = {
            "timestamp": self.timestamp,
            "backend": result.backend,
            "job_id": result.job_id,
            "counts": result.counts,
            "dominance": result.dominance,
            "top_state": result.top_state,
            "is_decohered": result.is_decohered,
            "z_score": result.z_score,
            "purity": result.purity,
            "metadata": result.metadata,
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        
        logger.info(f"💾 Saved: {filepath}")
        return filepath


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def run_circuit(circuit: QuantumCircuit, 
                shots: int = TopologyConstants.SHOTS) -> GambitResult:
    """
    Convenience function to run a circuit on IBM hardware.
    
    Args:
        circuit: The quantum circuit
        shots: Number of shots
        
    Returns:
        GambitResult
    """
    manager = GambitExecutionManager(shots=shots)
    return manager.run(circuit)


def verify_topology(result: GambitResult) -> Tuple[bool, str]:
    """
    Verify topological integrity of result.
    
    Returns:
        Tuple of (passed, message)
    """
    if result.is_decohered:
        return False, f"DECOHERED: {result.dominance:.2%} < 85%"
    
    if result.z_score > TopologyConstants.Z_SCORE_THRESHOLD:
        return True, f"ULTRA-TRIVIAL CONFIRMED ({result.z_score:.1f}σ)"
    
    if result.dominance >= TopologyConstants.DOMINANCE_THRESHOLD:
        return True, f"COHERENT ({result.dominance:.2%})"
    
    return False, "INCONCLUSIVE"
