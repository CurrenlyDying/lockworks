"""
Four-Core Modular Test (v2.0)
=============================

Tests 4 independent 2-qubit cores linked via CX.

Strategy: Braid each core independently, then link with CX.
This should outperform the failed 4-qubit monolithic braid.
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.compiler import GambitCompiler
from src.runtime import GambitExecutionManager
from src.slang import SLangProgram


def test_four_core_modular():
    """
    Test 4 independent cores.
    
    Topology:
        Core A (H) → CX → Core B (0)
                       ↓
        Core C (H) → CX → Core D (0)
    
    Expected: Higher correlation than monolithic 4-qubit chain
    """
    print("=" * 70)
    print("    FOUR-CORE MODULAR TEST (v2.0)")
    print("    8 Physical Qubits, 4 Independent Cores")
    print("=" * 70)
    
    # Build program - two independent Bell pairs
    prog = SLangProgram("FourCoreModular")
    
    # Pair 1: A-B
    a = prog.soliton("a", "H")
    b = prog.soliton("b", 0)
    prog.entangle(a, b)
    
    # Pair 2: C-D
    c = prog.soliton("c", "H")
    d = prog.soliton("d", 0)
    prog.entangle(c, d)
    
    # Measurements
    prog.measure(a)
    prog.measure(b)
    prog.measure(c)
    prog.measure(d)
    
    circuit = prog.compile()
    
    print(f"\n📦 Circuit: {circuit.num_qubits} physical qubits ({circuit.num_qubits//2} cores)")
    print(f"   Architecture: 2 independent Bell pairs")
    
    # Run
    print("\n🚀 Submitting to IBM Quantum...")
    manager = GambitExecutionManager()
    result = manager.run(circuit)
    
    counts = result.counts
    total = sum(counts.values())
    
    # Expected states: (Pair1 Bell) ⊗ (Pair2 Bell)
    # |00⟩|00⟩, |00⟩|11⟩, |11⟩|00⟩, |11⟩|11⟩
    # In measurement order: 0000, 0011, 1100, 1111
    expected = ['0000', '0011', '1100', '1111']
    expected_prob = sum(counts.get(s, 0) for s in expected) / total
    
    print("\n" + "=" * 70)
    print("    RESULTS")
    print("=" * 70)
    
    print(f"\n📊 State Distribution:")
    for state, count in sorted(counts.items(), key=lambda x: -x[1])[:8]:
        prob = count / total
        bar = "█" * int(prob * 40)
        expected_marker = " ✓" if state in expected else ""
        print(f"   |{state}⟩: {prob:6.2%} {bar}{expected_marker}")
    
    print(f"\n🎯 Correlated Pairs Probability: {expected_prob:.1%}")
    print(f"   Expected states: {expected}")
    
    # Compare to previous failed attempts
    print("\n📈 COMPARISON TO MONOLITHIC APPROACHES:")
    print(f"   Modular v2.0:  {expected_prob:.1%}")
    print(f"   Pairs (v1.0):  31.1% (NULL)")
    print(f"   GHZ4 (v1.0):   47.7% (PARTIAL)")
    print(f"   Chain4 (v1.0): 4.6% (FAILED)")
    
    if expected_prob >= 0.60:
        print("\n✅ SUCCESS: Modular 4-core scales!")
    elif expected_prob >= 0.40:
        print("\n⚠️ PARTIAL: Better than chain, investigate further")
    else:
        print("\n❌ NULL: Modular approach needs refinement")
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"four_core_modular_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "backend": result.backend,
            "architecture": "modular_v2.0",
            "cores": 4,
            "physical_qubits": 8,
            "expected_states": expected,
            "correlated_probability": expected_prob,
            "dominance": result.dominance,
            "counts": counts,
        }, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    
    return expected_prob


if __name__ == "__main__":
    test_four_core_modular()
