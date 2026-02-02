import numpy as np
import time
import os
import json
import logging
from datetime import datetime
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# --- CONFIGURATION (The Sigma Grindset) ---
SHOTS = 4096
COMPLEXITY = 6 # The "12-slice" lock verified on ibm_fez

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

# Auth Loading
TOKEN = os.environ.get("QISKIT_IBM_TOKEN")
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.join(script_dir, "apikey.json")
    if os.path.exists(key_path):
        with open(key_path, "r") as f:
            data = json.load(f)
            if "apikey" in data:
                TOKEN = data["apikey"]
                logger.info("🔑 Loaded token from apikey.json")
except Exception as e:
    logger.warning(f"⚠️ Could not load apikey.json: {e}")

if not TOKEN:
    raise ValueError("Bruh. Need QISKIT_IBM_TOKEN.")

# --- THE LOGICAL QUBIT (G-ISA) ---
class GambitLogicalQubit:
    """
    The Sigma Logical Qubit.
    Abstracts away the Braid Physics into simple Transistor Logic.
    """
    def __init__(self, name="Q_L"):
        self.name = name
        self.theta = 0.0 # Default to ROBUST state
        self.complexity = COMPLEXITY
        
    def write(self, value):
        """L_WRITE: Snaps the topological parameter to a pole."""
        if value == 0:
            self.theta = 0.0   # The 93% Purity Pole
            # logger.info(f"[{self.name}] Locked to ROBUST (|0>_L)")
        elif value == 1:
            self.theta = 0.196 # The 90% Purity Fisher Peak
            # logger.info(f"[{self.name}] Locked to FISHER (|1>_L)")
        else:
            raise ValueError("Based binary only.")

    def flip(self):
        """L_NOT: Rolls the Soliton."""
        # Simple toggle logic for the parameter
        if np.isclose(self.theta, 0.0):
            self.theta = 0.196
        else:
            self.theta = 0.0
        # logger.info(f"[{self.name}] Soliton Rolled to theta={self.theta}")

    def compile(self):
        """
        Compiles the Logical State into Physical Hardware Circuit.
        Includes the 'Close Portal' (H) lens cap fix.
        """
        qc = QuantumCircuit(2) 
        qc.name = f"{self.name}_theta_{self.theta:.3f}"
        
        # 1. OPEN PORTAL (Carrier)
        qc.h([0, 1])
        
        # 2. ENFORCE TOPOLOGY (Transistor State)
        for _ in range(self.complexity):
            qc.cz(0, 1) 
            qc.rx(self.theta, 0) 
            qc.rz(self.theta * 2, 1) 
            qc.barrier()
            
        # 3. CLOSE PORTAL (Readout Lens)
        qc.h([0, 1]) 
        
        # 4. MEASURE
        qc.measure_all()
        return qc

# --- EXECUTION ENGINE ---
def run_isa_benchmark():
    logger.info("🔌 Connecting to IBM Quantum...")
    service = QiskitRuntimeService(token=TOKEN)
    
    # Target the hardware
    backend = service.least_busy(operational=True, simulator=False)
    logger.info(f"🚀 Targeted Backend: {backend.name}")

    # --- DEFINE LOGICAL PROGRAMS ---
    logger.info("\n💾 COMPILING LOGICAL BATCH...")
    
    # Program 1: Write 0
    q1 = GambitLogicalQubit("PROG_A_WRITE0")
    q1.write(0)
    circ1 = q1.compile()
    print(f"   [Program A] WRITE(0) -> Theta {q1.theta} -> Expect |00>")

    # Program 2: Write 1
    q2 = GambitLogicalQubit("PROG_B_WRITE1")
    q2.write(1)
    circ2 = q2.compile()
    print(f"   [Program B] WRITE(1) -> Theta {q2.theta} -> Expect |10>")

    # Program 3: NOT Gate (Soliton Roll)
    q3 = GambitLogicalQubit("PROG_C_NOT_GATE")
    q3.write(0) # Init 0
    q3.flip()   # Apply NOT (Roll to 1)
    circ3 = q3.compile()
    print(f"   [Program C] WRITE(0) + NOT -> Theta {q3.theta} -> Expect |10>")

    circuits = [circ1, circ2, circ3]

    # --- TRANSPILE ---
    logger.info(f"\n🔨 Transpiling for {backend.name} (Opt Level 3)...")
    pm = generate_preset_pass_manager(backend=backend, optimization_level=3)
    isa_circuits = pm.run(circuits)

    # --- SUBMIT ---
    logger.info("\n🚀 IGNITING G-ISA KERNEL (Job Mode)...")
    sampler = Sampler(mode=backend)
    pubs = [(c, None, SHOTS) for c in isa_circuits]
    
    job = sampler.run(pubs)
    logger.info(f"   --> JOB ID: {job.job_id()}")
    
    logger.info("   ... Waiting for Quantum CPU ...")
    result = job.result()
    logger.info(f"✅ EXECUTION COMPLETE.\n")

    # --- DECODE RESULTS ---
    print("="*40)
    print("      LOGICAL QUBIT READOUT")
    print("="*40)
    
    expected_states = {
        0: '00', # Expect ROBUST
        1: '10', # Expect FISHER
        2: '10'  # Expect FISHER (after NOT)
    }
    
    programs = ["A (WRITE 0)", "B (WRITE 1)", "C (0 + NOT)"]

    for i, pub_result in enumerate(result):
        counts = pub_result.data.meas.get_counts()
        total = sum(counts.values())
        
        # Sort by count to find dominant physical state
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        top_state, top_count = sorted_counts[0]
        dominance = top_count / total
        
        # Decode to Logical Bit
        # Mapping: Physical '00' -> Logical 0, Physical '10' -> Logical 1
        logical_val = "UNKNOWN"
        if top_state == '00': logical_val = "0"
        elif top_state == '10': logical_val = "1"
        
        target_phys = expected_states[i]
        success_mark = "✅" if top_state == target_phys else "❌"
        
        print(f"\nProgram {programs[i]}:")
        print(f"   Raw Counts: {counts}")
        print(f"   Physical Output: |{top_state}> (Conf: {dominance:.2%})")
        print(f"   Logical Output:  {logical_val}")
        print(f"   Verification:    {success_mark}")

if __name__ == "__main__":
    run_isa_benchmark()