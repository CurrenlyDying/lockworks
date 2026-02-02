"""
LockWorks v6.0: The Killshot Experiment
=========================================

Proves fault tolerance by comparing C=2 vs C=6 under fault injection.

Test Matrix:
    Point 0 (Baseline): Identity gate baseline (no braid)
    Point 1 (C=2): Light topology with fault
    Point 2 (C=6): Full topology with fault
    Point 3 (X-Basis): Coherence tomography

Success Criteria:
    - C=6 detects faults more reliably than C=2
    - Post-selection lift increases with C
    - X-basis shows ~50/50 (coherent sphere)
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.witness import ParityWitness
from src.needle import NeedleDriver


def analyze_syndrome(counts: dict, val_a: int, val_b: int, fault_target: int) -> dict:
    """
    Analyze syndrome detection.
    
    After fault injection on disk A:
        - Original: A, B, P = A⊕B
        - After X on A: Ā, B, P = A⊕B (parity no longer matches)
        - Syndrome = 1 if P ≠ Ā⊕B (error detected)
    """
    total = sum(counts.values())
    
    # Expected values AFTER fault on disk A
    # If we flip A, the new logical A = 1-val_a
    expected_a_after_fault = 1 - val_a if fault_target == 0 else val_a
    expected_b_after_fault = 1 - val_b if fault_target == 1 else val_b
    
    # Original parity was computed before fault
    original_parity = val_a ^ val_b
    
    syndrome_detected = 0  # Parity mismatch (error caught)
    syndrome_missed = 0    # Parity still matches (error missed OR data wrong)
    correct_data_with_syndrome = 0  # Can recover original data?
    
    for state, count in counts.items():
        bits = state.zfill(3)
        p = int(bits[0])  # Parity (MSB)
        b = int(bits[1])  # Disk 1
        a = int(bits[2])  # Disk 0 (LSB)
        
        actual_parity_should_be = a ^ b
        
        if p != actual_parity_should_be:
            # Syndrome detected: parity doesn't match current data
            syndrome_detected += count
            # Check if we can recover original data
            # The parity still holds original A⊕B
            if p == original_parity:
                correct_data_with_syndrome += count
        else:
            syndrome_missed += count
    
    return {
        "total": total,
        "syndrome_detected": syndrome_detected / total,
        "syndrome_missed": syndrome_missed / total,
        "recovery_potential": correct_data_with_syndrome / total if syndrome_detected > 0 else 0
    }


def run_killshot_test():
    print("=" * 70)
    print("    LOCKWORKS v6.0: THE KILLSHOT EXPERIMENT")
    print("    Fault Tolerance Proof")
    print("=" * 70)
    
    needle = NeedleDriver()
    
    # Test case: A=1, B=0 → P=1, inject fault on Disk 0
    val_a, val_b = 1, 0
    fault_target = 0
    
    results = []
    
    # === POINT 0: BASELINE (Identity, no braid) ===
    print("\n📍 Point 0: Baseline (Identity gates)")
    witness = ParityWitness(complexity=6)
    qc = witness.build_protected_circuit(val_a, val_b, inject_fault=True, 
                                          fault_target=fault_target, use_baseline=True)
    res = needle.read_circuit(qc)
    analysis = analyze_syndrome(res.raw_counts, val_a, val_b, fault_target)
    results.append({
        "test": "Baseline (Identity)",
        "complexity": 0,
        **analysis,
        "counts": res.raw_counts
    })
    print(f"   Syndrome Detection: {analysis['syndrome_detected']:.1%}")
    
    # === POINT 1: C=2 with fault ===
    print("\n📍 Point 1: C=2 Topology with Fault")
    witness = ParityWitness(complexity=2)
    qc = witness.build_protected_circuit(val_a, val_b, inject_fault=True, 
                                          fault_target=fault_target)
    res = needle.read_circuit(qc)
    analysis = analyze_syndrome(res.raw_counts, val_a, val_b, fault_target)
    results.append({
        "test": "C=2 with Fault",
        "complexity": 2,
        **analysis,
        "counts": res.raw_counts
    })
    print(f"   Syndrome Detection: {analysis['syndrome_detected']:.1%}")
    
    # === POINT 2: C=6 with fault ===
    print("\n📍 Point 2: C=6 Topology with Fault")
    witness = ParityWitness(complexity=6)
    qc = witness.build_protected_circuit(val_a, val_b, inject_fault=True, 
                                          fault_target=fault_target)
    res = needle.read_circuit(qc)
    analysis = analyze_syndrome(res.raw_counts, val_a, val_b, fault_target)
    results.append({
        "test": "C=6 with Fault",
        "complexity": 6,
        **analysis,
        "counts": res.raw_counts
    })
    print(f"   Syndrome Detection: {analysis['syndrome_detected']:.1%}")
    
    # === POINT 3: X-Basis Tomography (No fault, C=6) ===
    print("\n📍 Point 3: X-Basis Tomography (Coherence Test)")
    witness = ParityWitness(complexity=6)
    qc = witness.build_protected_circuit(val_a, val_b, inject_fault=False, 
                                          basis='X')
    res = needle.read_circuit(qc)
    
    # Check for ~50/50 distribution (coherent superposition)
    counts = res.raw_counts
    total = sum(counts.values())
    
    # For X-basis, coherent state should show mixed results
    entropy = 0
    for state, count in counts.items():
        p = count / total
        if p > 0:
            import math
            entropy -= p * math.log2(p)
    
    max_entropy = 3.0  # 3 bits = 8 states
    coherence_score = entropy / max_entropy
    
    results.append({
        "test": "X-Basis Tomography",
        "complexity": 6,
        "entropy": entropy,
        "max_entropy": max_entropy,
        "coherence_score": coherence_score,
        "counts": counts
    })
    print(f"   Entropy: {entropy:.2f} / {max_entropy:.2f}")
    print(f"   Coherence Score: {coherence_score:.1%}")
    
    # === SUMMARY ===
    print("\n" + "=" * 70)
    print("    KILLSHOT SUMMARY")
    print("=" * 70)
    
    print(f"\n{'Test':<25} {'Syndrome':>12} {'Post-Select':>12}")
    print("-" * 50)
    for r in results[:3]:
        syn = r.get('syndrome_detected', 0)
        rec = r.get('recovery_potential', 0)
        print(f"{r['test']:<25} {syn:>12.1%} {rec:>12.1%}")
    
    # Post-selection lift calculation
    c2_syn = results[1]['syndrome_detected']
    c6_syn = results[2]['syndrome_detected']
    lift = (c6_syn - c2_syn) / c2_syn * 100 if c2_syn > 0 else 0
    
    print(f"\n🎯 Post-Selection Lift (C=6 vs C=2): {lift:+.1f}%")
    
    if c6_syn > c2_syn and c6_syn > 0.80:
        print("\n🏆 KILLSHOT SUCCESSFUL!")
        print("   C=6 topology detects faults better than C=2.")
        print("   The 'metaphor' critique is officially DEAD.")
    elif c6_syn > 0.60:
        print("\n⚠️ PARTIAL SUCCESS")
        print(f"   C=6 syndrome detection at {c6_syn:.1%}")
    else:
        print("\n❌ NEEDS INVESTIGATION")
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lockworks_v6_killshot_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "experiment": "killshot",
            "version": "6.0",
            "test_case": {"val_a": val_a, "val_b": val_b, "fault_target": fault_target},
            "results": results,
            "post_selection_lift": lift
        }, f, indent=2, default=str)
    
    print(f"\n💾 Saved: {filename}")
    
    return results


if __name__ == "__main__":
    run_killshot_test()
