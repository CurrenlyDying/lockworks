"""
CTM v1.1 Gearbox Comparison Test
================================

Test different gearbox configurations to find optimal LINK protection.

Configurations:
    1. NO_GEARBOX: Raw CX (baseline)
    2. BASIC_SHIFT: Barrier + X-X + CX + Barrier
    3. DOUBLE_SHIFT: Barrier + X-X on both + CX + Barrier
    4. ECHO_SHIFT: Barrier + X + CX + X + Barrier (spin echo)
    5. NO_DD: Just barriers, no dynamical decoupling
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

from src.isa import TopologyConstants
from src.gearbox import Gearbox


def build_bell_circuit(gearbox_mode: str, complexity: int = 6) -> QuantumCircuit:
    """
    Build a 2-disk Bell circuit with different gearbox modes.
    """
    n_phys = 4  # 2 disks × 2 qubits
    qreg = QuantumRegister(n_phys, 'q')
    creg = ClassicalRegister(2, 'meas')
    qc = QuantumCircuit(qreg, creg, name=f"CTM_{gearbox_mode}")
    
    # Disk 0: θ=0.1 (superposition)
    # Disk 1: θ=0.0 (ground)
    theta_a = 0.1
    theta_b = 0.0
    
    # Open Portal
    qc.h(qreg)
    
    # Braid Disk 0
    for _ in range(complexity):
        qc.cz(qreg[0], qreg[1])
        qc.rx(theta_a, qreg[0])
        qc.rz(theta_a * 2, qreg[1])
        qc.barrier([qreg[0], qreg[1]])
    
    # Braid Disk 1
    for _ in range(complexity):
        qc.cz(qreg[2], qreg[3])
        qc.rx(theta_b, qreg[2])
        qc.rz(theta_b * 2, qreg[3])
        qc.barrier([qreg[2], qreg[3]])
    
    # LINK with different gearbox modes
    ctrl = qreg[1]  # Disk 0 data bit
    tgt = qreg[3]   # Disk 1 data bit
    
    if gearbox_mode == "NO_GEARBOX":
        # Raw CX - no protection
        qc.cx(ctrl, tgt)
    
    elif gearbox_mode == "BASIC_SHIFT":
        # Standard shift_gear
        Gearbox.shift_gear(qc, ctrl, tgt)
    
    elif gearbox_mode == "DOUBLE_SHIFT":
        # DD on both qubits
        Gearbox.double_shift(qc, ctrl, tgt)
    
    elif gearbox_mode == "ECHO_SHIFT":
        # Spin echo pattern
        Gearbox.echo_shift(qc, ctrl, tgt)
    
    elif gearbox_mode == "BARRIER_ONLY":
        # Just barriers, no DD
        qc.barrier(ctrl, tgt)
        qc.cx(ctrl, tgt)
        qc.barrier(ctrl, tgt)
    
    elif gearbox_mode == "HEAVY_DD":
        # Heavy dynamical decoupling (4 X gates)
        qc.barrier(ctrl, tgt)
        Gearbox.double_idle(qc, ctrl)
        qc.cx(ctrl, tgt)
        qc.barrier(ctrl, tgt)
    
    # Close Portal
    qc.h(qreg)
    
    # Measure data bits
    qc.measure(qreg[1], creg[0])
    qc.measure(qreg[3], creg[1])
    
    return qc


def run_comparison():
    print("=" * 70)
    print("    GEARBOX CONFIGURATION COMPARISON")
    print("    Finding optimal LINK protection")
    print("=" * 70)
    
    modes = [
        "NO_GEARBOX",
        "BARRIER_ONLY",
        "BASIC_SHIFT",
        "DOUBLE_SHIFT",
        "ECHO_SHIFT",
        "HEAVY_DD",
    ]
    
    # Build circuits
    circuits = []
    for mode in modes:
        qc = build_bell_circuit(mode)
        circuits.append(qc)
        print(f"📦 {mode}: depth={qc.depth()}")
    
    # Connect
    print("\n🔌 Connecting to IBM Quantum...")
    
    import os
    token = os.environ.get("QISKIT_IBM_TOKEN")
    if not token:
        with open("apikey.json") as f:
            token = json.load(f).get("apikey")
    
    service = QiskitRuntimeService(token=token)
    backend = service.least_busy(operational=True, simulator=False)
    print(f"   Backend: {backend.name}")
    
    # Transpile
    print("\n🔨 Transpiling...")
    pm = generate_preset_pass_manager(backend=backend, optimization_level=3)
    isa_circuits = pm.run(circuits)
    
    # Run
    print("\n🚀 Running on QPU...")
    sampler = Sampler(mode=backend)
    pubs = [(qc, None, 4096) for qc in isa_circuits]
    job = sampler.run(pubs)
    
    print(f"   Job ID: {job.job_id()}")
    print("   ... Waiting ...")
    
    result = job.result()
    
    # Analyze
    print("\n" + "=" * 70)
    print("    RESULTS")
    print("=" * 70)
    
    all_results = []
    
    for i, mode in enumerate(modes):
        pub_result = result[i]
        try:
            counts = pub_result.data.meas.get_counts()
        except:
            counts = {}
        
        total = sum(counts.values())
        bell_prob = (counts.get("00", 0) + counts.get("11", 0)) / total if total > 0 else 0
        leakage_01 = counts.get("01", 0) / total if total > 0 else 0
        
        success = "✅" if bell_prob >= 0.60 else "❌"
        
        print(f"\n{success} {mode}:")
        print(f"   Bell (|00⟩+|11⟩): {bell_prob:.1%}")
        print(f"   Leakage (|01⟩):   {leakage_01:.1%}")
        print(f"   Counts: {counts}")
        
        all_results.append({
            "mode": mode,
            "bell_probability": bell_prob,
            "leakage_01": leakage_01,
            "counts": counts,
            "success": bell_prob >= 0.60
        })
    
    # Find best
    best = max(all_results, key=lambda x: x["bell_probability"])
    print("\n" + "=" * 70)
    print(f"🏆 BEST: {best['mode']} with {best['bell_probability']:.1%} Bell fidelity")
    print("=" * 70)
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"gearbox_comparison_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "backend": backend.name,
            "results": all_results,
            "best_mode": best["mode"]
        }, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    
    return all_results


if __name__ == "__main__":
    run_comparison()
