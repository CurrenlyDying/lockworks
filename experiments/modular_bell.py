"""
Multi-Core Bell Test (v2.0 Modular Architecture)
================================================

Tests the "Scale OUT" strategy: independent 2-qubit cores linked via CX.

Expected: Higher fidelity than monolithic 4-qubit braid.
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.compiler import GambitCompiler
from src.runtime import GambitExecutionManager
from src.slang import SLangProgram


def test_modular_bell():
    """
    Two independent cores, linked with CX.
    
    Core A: H → [braid] 
    Core B: 0 → [braid]
    Link: CX(A.data, B.data)
    
    Expected: |00⟩ + |11⟩ with >85% (vs 4.6% for chain4)
    """
    print("=" * 70)
    print("    MODULAR BELL TEST (v2.0)")
    print("    Scale OUT Strategy: Independent Cores + CX Link")
    print("=" * 70)
    
    # Build program
    prog = SLangProgram("ModularBell")
    a = prog.soliton("alpha", "H")  # Core 0: Superposition
    b = prog.soliton("beta", 0)     # Core 1: Ground
    
    prog.entangle(a, b)  # Link cores with CX
    
    prog.measure(a)
    prog.measure(b)
    
    circuit = prog.compile()
    
    print(f"\n📦 Circuit: {circuit.num_qubits} physical qubits ({circuit.num_qubits//2} cores)")
    print(f"   Depth: {circuit.depth()}")
    
    # Run on IBM
    print("\n🚀 Submitting to IBM Quantum...")
    manager = GambitExecutionManager()
    result = manager.run(circuit)
    
    # Analyze
    counts = result.counts
    total = sum(counts.values())
    
    bell_states = ['00', '11']
    bell_prob = sum(counts.get(s, 0) for s in bell_states) / total
    
    print("\n" + "=" * 70)
    print("    RESULTS")
    print("=" * 70)
    
    print(f"\n📊 State Distribution:")
    for state, count in sorted(counts.items(), key=lambda x: -x[1]):
        prob = count / total
        bar = "█" * int(prob * 40)
        print(f"   |{state}⟩: {prob:6.2%} {bar}")
    
    print(f"\n🎯 Bell State Probability: {bell_prob:.1%}")
    print(f"   Dominance: {result.dominance:.1%}")
    print(f"   Z-Score: {result.z_score:.1f}σ")
    
    # Compare to previous
    print("\n📈 COMPARISON:")
    print(f"   Modular (v2.0): {bell_prob:.1%} Bell states")
    print(f"   Chain4 (v1.0):  4.6% (failed)")
    print(f"   Improvement:    {bell_prob/0.046:.1f}x")
    
    if bell_prob >= 0.70:
        print("\n✅ SUCCESS: Modular architecture scales!")
    elif bell_prob >= 0.50:
        print("\n⚠️ PARTIAL: Better than chain, but not optimal")
    else:
        print("\n❌ NULL: Modular approach also failed")
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"modular_bell_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "backend": result.backend,
            "architecture": "modular_v2.0",
            "cores": 2,
            "physical_qubits": 4,
            "bell_probability": bell_prob,
            "dominance": result.dominance,
            "z_score": result.z_score,
            "counts": counts,
        }, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    
    return bell_prob


if __name__ == "__main__":
    test_modular_bell()
