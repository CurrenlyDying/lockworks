import numpy as np
import os
import json
import logging
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# --- SIGMA CONFIG ---
SHOT_COUNTS = [1024, 4096, 8192] 
COMPLEXITY = 6

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

# --- AUTH ---
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
    pass

if not TOKEN:
    raise ValueError("Need QISKIT_IBM_TOKEN or apikey.json")

# --- THE GRAY CODE ISA ---
class GambitGrayQubit:
    def __init__(self, name="Q_GRAY"):
        self.name = name
        self.theta = 0.0
        self.complexity = COMPLEXITY
        
    def to_gray(self, n):
        return n ^ (n >> 1)

    def write_gray_level(self, level):
        gray_val = self.to_gray(level)
        # 00 -> 0.0 (Robust)
        # 01 -> 0.1 (Tension)
        # 11 -> 0.196 (Fisher/Flip)
        # 10 -> 0.4 (Max Info)
        if gray_val == 0: self.theta = 0.0
        elif gray_val == 1: self.theta = 0.1
        elif gray_val == 3: self.theta = 0.196 
        elif gray_val == 2: self.theta = 0.4
        return self.theta, gray_val

    def compile(self):
        qc = QuantumCircuit(2)
        qc.name = f"{self.name}_th_{self.theta:.3f}"
        qc.h([0, 1]) 
        for _ in range(self.complexity):
            qc.cz(0, 1)
            qc.rx(self.theta, 0)
            qc.rz(self.theta * 2, 1)
            qc.barrier()
        qc.h([0, 1]) 
        qc.measure_all()
        return qc

# --- EXECUTION ---
def run_stress_test():
    service = QiskitRuntimeService(token=TOKEN)
    backend = service.least_busy(operational=True, simulator=False)
    logger.info(f"🚀 Target: {backend.name} | Scanning for Shot Sweet Spot...")

    # 1. Build the "Staircase" Program
    qubit = GambitGrayQubit("SIGMA")
    circuits = []
    
    print("\n--- COMPILING STAIRCASE TRAJECTORY ---")
    for level in range(4):
        theta, gray = qubit.write_gray_level(level)
        print(f"Step {level}: Gray {gray:02b} -> Theta {theta:.3f}")
        qc = qubit.compile()
        qc.metadata = {"level": level, "gray": gray, "theta": theta}
        circuits.append(qc)

    # 2. Transpile ONCE
    pm = generate_preset_pass_manager(backend=backend, optimization_level=3)
    isa_circuits = pm.run(circuits)

    # 3. Submit Multi-Shot Batch (FIXED: Flatten the list)
    sampler = Sampler(mode=backend)
    
    pubs = []
    # We generate 12 PUBs: 4 circuits * 3 shot settings
    for shots in SHOT_COUNTS:
        logger.info(f"   ... Stacking 4-step Staircase for {shots} shots")
        for qc in isa_circuits:
            # PUB format: (Circuit, ParameterValues, Shots)
            pubs.append((qc, None, shots))

    logger.info(f"\n🚀 FIRING STRESS TEST ({len(pubs)} Sub-Jobs)...")
    job = sampler.run(pubs)
    logger.info(f"   --> JOB ID: {job.job_id()}")
    
    result = job.result()
    logger.info("✅ DATA ACQUIRED.")

    # 4. Analyze "The Sweet Spot"
    print("\n" + "="*60)
    print("      SIGMA AUDIT: FINDING THE SWEET SPOT")
    print("="*60)

    # We have 12 results in a flat list. We need to iterate them correctly.
    # Order: [Shots1_Lvl0, Shots1_Lvl1... Shots1_Lvl3, Shots2_Lvl0...]
    
    current_idx = 0
    
    for shots_used in SHOT_COUNTS:
        print(f"\n🎯 SHOT COUNT: {shots_used}")
        print("-" * 30)
        
        # Iterate through the 4 levels for this shot count
        for level in range(4):
            pub_result = result[current_idx]
            current_idx += 1
            
            # Extract data
            counts = pub_result.data.meas.get_counts()
            
            # Metadata
            theta = circuits[level].metadata['theta']
            
            sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
            top_state, top_count = sorted_counts[0]
            dominance = top_count / shots_used
            
            # Sigma Grading
            marker = ""
            if dominance > 0.92: marker = "🔥 CRITICAL"
            elif dominance > 0.85: marker = "✅ SOLID"
            else: marker = "⚠️ NOISY"

            print(f"   Lvl {level} (θ={theta:.3f}): |{top_state}> @ {dominance:.2%} {marker}")

if __name__ == "__main__":
    run_stress_test()