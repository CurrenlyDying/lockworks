import numpy as np
import time
import os
import json
import logging
from datetime import datetime
from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# --- CONFIGURATION ---
# Setup Logging (Console + File)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"gambit_log_{timestamp}.txt"
data_filename = f"gambit_raw_{timestamp}.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

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

SHOTS = 4096
COMPLEXITY = 6 # Keeping at 6 for safety (12-slice), set to 8 for overclock

def build_schrodingers_braid(theta, complexity=COMPLEXITY):
    qc = QuantumCircuit(2) 
    # 1. OPEN (H)
    qc.h([0, 1])
    # 2. BRAID
    for _ in range(complexity):
        qc.cz(0, 1) 
        qc.rx(theta, 0) 
        qc.rz(theta * 2, 1) 
        qc.barrier()
    # 3. CLOSE (H) - The Lens Cap Removal
    qc.h([0, 1]) 
    # 4. MEASURE
    qc.measure_all()
    return qc

def hellinger_distance(p, q):
    """Calculates Hellinger distance between two probability distributions."""
    return (1/np.sqrt(2)) * np.linalg.norm(np.sqrt(p) - np.sqrt(q))

def analyze_sigma(counts, shots):
    """Performs the TDA/Sigma analysis on the raw counts."""
    # 1. Convert to Probabilities
    states = ['00', '01', '10', '11']
    obs_dist = np.array([counts.get(k, 0) for k in states])
    obs_prob = obs_dist / shots
    
    # 2. Dominance & Purity
    dominance = np.max(obs_prob)
    top_state = states[np.argmax(obs_prob)]
    purity = np.sum(obs_prob**2)
    
    # 3. Hellinger vs Uniform (Signal Strength)
    uniform_prob = np.array([0.25, 0.25, 0.25, 0.25])
    h_dist = hellinger_distance(obs_prob, uniform_prob)
    
    # 4. Z-Score Estimate (Simplified)
    # Based on Null Distribution of 4096 shots of noise (Mean ~0.008, Std ~0.0037)
    # We use pre-calculated constants for speed
    NULL_MEAN = 0.008
    NULL_STD = 0.0037
    z_score = (h_dist - NULL_MEAN) / NULL_STD
    
    return {
        "dominance": dominance,
        "top_state": top_state,
        "purity": purity,
        "hellinger": h_dist,
        "z_score": z_score
    }

def run_ibm_sweep():
    if not TOKEN:
        raise ValueError("Please set QISKIT_IBM_TOKEN.")

    logger.info(f"🔌 Connecting to IBM Quantum (Open Plan Mode)...")
    service = QiskitRuntimeService(token=TOKEN)
    
    backend = service.least_busy(operational=True, simulator=False)
    logger.info(f"🚀 Targeted Backend: {backend.name}")

    thetas = [0.0, 0.196, 0.4] 
    circuits = []
    for theta in thetas:
        qc = build_schrodingers_braid(theta)
        qc.name = f"theta_{theta:.3f}"
        circuits.append(qc)

    logger.info(f"🔨 Transpiling for {backend.name}...")
    pm = generate_preset_pass_manager(backend=backend, optimization_level=3)
    isa_circuits = pm.run(circuits)

    logger.info("🚀 IGNITING JOB (No Session)...")
    sampler = Sampler(mode=backend)
    pubs = [(c, None, SHOTS) for c in isa_circuits]

    job = sampler.run(pubs)
    logger.info(f"   --> JOB ID: {job.job_id()}")
    
    logger.info("   ... Waiting for cloud execution ...")
    result = job.result()
    logger.info(f"✅ BATCH COMPLETE.\n")

    # Data Container for JSON dump
    experiment_data = {
        "backend": backend.name,
        "shots": SHOTS,
        "complexity": COMPLEXITY,
        "job_id": job.job_id(),
        "timestamp": timestamp,
        "results": []
    }

    # Parse & Analyze
    for i, pub_result in enumerate(result):
        theta = thetas[i]
        counts = pub_result.data.meas.get_counts()
        
        # Run Sigma Analysis
        metrics = analyze_sigma(counts, SHOTS)
        
        # Log to Console/File
        logger.info(f"--- Theta: {theta:.3f} rad ---")
        logger.info(f"Counts: {counts}")
        logger.info(f"Dominance: {metrics['dominance']:.4f} (Top: {metrics['top_state']})")
        logger.info(f"Purity (Rho): {metrics['purity']:.4f}")
        logger.info(f"Hellinger Dist: {metrics['hellinger']:.4f}")
        logger.info(f"Sigma (Z-Score): {metrics['z_score']:.2f} σ")
        
        if theta == 0.0:
            if metrics['z_score'] > 14.0:
                 logger.info("   🌟 STATUS: ULTRA-TRIVIAL CONFIRMED (>14σ)")
            else:
                 logger.info("   ⚠️ STATUS: NOISE DETECTED (<14σ)")

        # Save to struct
        experiment_data["results"].append({
            "theta": theta,
            "counts": counts,
            "metrics": metrics
        })

    # Dump Raw Data
    with open(data_filename, "w") as f:
        json.dump(experiment_data, f, indent=4)
    logger.info(f"\n💾 Raw data saved to: {data_filename}")

if __name__ == "__main__":
    run_ibm_sweep()