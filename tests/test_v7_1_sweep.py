"""
LockWorks v7.1: Echo Chamber Sweep
===================================

Tests multiple Dynamical Decoupling configurations to find optimal
phase drift cancellation.

Configurations:
    - BASELINE (no echo)
    - HAHN_D0 (minimal delay Hahn echo)
    - HAHN_D5 (5-cycle delay Hahn echo)
    - CPMG_D0 (minimal delay CPMG)
    - CPMG_D5 (5-cycle delay CPMG)
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from src.echo_chamber import EchoChamber
from src.needle import NeedleDriver


class WitnessV71:
    """
    LockWorks v7.1: Echo Chamber Sweep Witness.
    
    Tests multiple echo configurations to find optimal phase cancellation.
    """
    
    def __init__(self, complexity: int = 6):
        self.complexity = complexity
        self.q = QuantumRegister(6, 'q')
        self.c = ClassicalRegister(3, 'meas')
        self.data_indices = [1, 3, 5]
    
    def build_baseline_circuit(self, val_a: int, val_b: int) -> QuantumCircuit:
        """Build v6.4-style baseline circuit (no echo)."""
        qc = QuantumCircuit(self.q, self.c)
        
        # 1. OPEN
        qc.h(self.q)
        
        # 2. X-LINK
        qc.barrier()
        for idx in self.data_indices:
            qc.h(self.q[idx])
        qc.cx(self.q[5], self.q[1])
        qc.cx(self.q[5], self.q[3])
        for idx in self.data_indices:
            qc.h(self.q[idx])
        qc.barrier()
        
        # 3. BRAID
        self._braid(qc, 0, val_a)
        self._braid(qc, 1, val_b)
        self._braid(qc, 2, 0)
        
        # 4. MEASURE (X-Basis)
        qc.barrier()
        for idx in self.data_indices:
            qc.h(self.q[idx])
        qc.measure(self.q[1], self.c[0])
        qc.measure(self.q[3], self.c[1])
        qc.measure(self.q[5], self.c[2])
        
        return qc
    
    def build_echo_circuit(
        self, 
        val_a: int, 
        val_b: int, 
        method: str = "HAHN", 
        delay: int = 0
    ) -> QuantumCircuit:
        """
        Build circuit with specified echo configuration.
        
        Args:
            val_a, val_b: Disk values
            method: "HAHN" or "CPMG"
            delay: Number of identity cycles in echo
        """
        qc = QuantumCircuit(self.q, self.c)
        
        # 1. OPEN
        qc.h(self.q)
        
        # 2. X-LINK
        qc.barrier()
        for idx in self.data_indices:
            qc.h(self.q[idx])
        qc.cx(self.q[5], self.q[1])
        qc.cx(self.q[5], self.q[3])
        for idx in self.data_indices:
            qc.h(self.q[idx])
        qc.barrier()
        
        # === 3. ECHO CHAMBER ===
        data_qubits = [self.q[1], self.q[3], self.q[5]]
        
        if method == "HAHN":
            EchoChamber.apply_echo(qc, data_qubits, delay_cycles=delay)
        elif method == "CPMG":
            EchoChamber.apply_cpmg(qc, data_qubits, n_pulses=2, delay_cycles=delay)
        
        # 4. BRAID
        self._braid(qc, 0, val_a)
        self._braid(qc, 1, val_b)
        self._braid(qc, 2, 0)
        
        # 5. MEASURE (X-Basis)
        qc.barrier()
        for idx in self.data_indices:
            qc.h(self.q[idx])
        qc.measure(self.q[1], self.c[0])
        qc.measure(self.q[3], self.c[1])
        qc.measure(self.q[5], self.c[2])
        
        return qc
    
    def _braid(self, qc: QuantumCircuit, idx: int, val: int) -> None:
        theta = 0.196 if val == 1 else 0.0
        p = idx * 2
        d = idx * 2 + 1
        
        for _ in range(self.complexity):
            qc.cz(self.q[p], self.q[d])
            qc.rx(theta, self.q[p])
            qc.rz(theta * 2, self.q[d])
            qc.barrier([self.q[p], self.q[d]])


def calculate_syndrome(counts: dict) -> float:
    """Calculate X-parity syndrome."""
    total = sum(counts.values())
    mismatch = 0
    for state, count in counts.items():
        bits = [int(b) for b in state.zfill(3)]
        if bits[0] != (bits[1] ^ bits[2]):
            mismatch += count
    return mismatch / total if total > 0 else 0


def run_echo_sweep():
    print("=" * 70)
    print("    LOCKWORKS v7.1: ECHO CHAMBER SWEEP")
    print("    Dynamical Decoupling Optimization")
    print("=" * 70)
    
    needle = NeedleDriver()
    witness = WitnessV71(complexity=6)
    
    val_a, val_b = 0, 0  # ROBUST poles
    
    results = []
    
    # 1. Baseline
    print("\n📍 Running Baseline (No Echo)...")
    qc_base = witness.build_baseline_circuit(val_a, val_b)
    res_base = needle.read_circuit(qc_base)
    syn_base = calculate_syndrome(res_base.raw_counts)
    results.append({
        "mode": "BASELINE",
        "syndrome": syn_base,
        "delta": 0.0,
        "counts": res_base.raw_counts
    })
    print(f"   Baseline Syndrome: {syn_base:.2%}")
    
    # 2. Sweep Configurations
    configs = [
        ("HAHN", 0, "Hahn Echo (Minimal)"),
        ("HAHN", 5, "Hahn Echo (Delay=5)"),
        ("CPMG", 0, "CPMG-2 (Minimal)"),
        ("CPMG", 5, "CPMG-2 (Delay=5)"),
    ]
    
    best_syn = syn_base
    best_cfg = "BASELINE"
    
    for method, delay, desc in configs:
        name = f"{method}_D{delay}"
        print(f"\n📍 Testing {desc}...")
        qc = witness.build_echo_circuit(val_a, val_b, method=method, delay=delay)
        res = needle.read_circuit(qc)
        syn = calculate_syndrome(res.raw_counts)
        
        delta = syn - syn_base
        results.append({
            "mode": name,
            "desc": desc,
            "syndrome": syn,
            "delta": delta,
            "counts": res.raw_counts
        })
        print(f"   Syndrome: {syn:.2%} (Delta: {delta:+.2%})")
        
        if syn < best_syn:
            best_syn = syn
            best_cfg = name
    
    # Analysis
    print("\n" + "=" * 70)
    print("    ECHO SWEEP RESULTS")
    print("=" * 70)
    
    print("\n   Configuration    | Syndrome | Delta")
    print("   " + "-" * 40)
    for r in results:
        mode = r['mode']
        syn = r['syndrome']
        delta = r.get('delta', 0)
        status = "✅" if delta < 0 else "❌" if delta > 0 else "—"
        print(f"   {mode:15} | {syn:6.2%}  | {delta:+.2%} {status}")
    
    # Verdict
    print("\n" + "=" * 70)
    
    if best_syn < syn_base:
        improvement = (syn_base - best_syn) / syn_base * 100
        print(f"🏆 BEST CONFIG: {best_cfg}")
        print(f"   Syndrome: {best_syn:.2%}")
        print(f"   Improvement: {improvement:.1f}% reduction")
    else:
        print("📊 BASELINE WINS")
        print("   No echo configuration improved on baseline.")
        print("   The 5% syndrome is likely the hardware noise floor.")
    
    print("=" * 70)
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lockworks_v7_1_sweep_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "experiment": "echo_sweep",
            "version": "7.1",
            "test_case": {"val_a": val_a, "val_b": val_b},
            "results": results,
            "best_config": best_cfg,
            "best_syndrome": best_syn,
            "baseline_syndrome": syn_base
        }, f, indent=2, default=str)
    
    print(f"\n💾 Saved: {filename}")
    
    return results


if __name__ == "__main__":
    run_echo_sweep()
