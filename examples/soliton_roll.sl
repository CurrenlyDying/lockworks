# Soliton Roll Demo (Logical NOT)
# ================================
# Demonstrates the Soliton Roll - the quantum NOT gate.
# 
# Physics:
#   - Start at ROBUST pole (θ=0.0, expect |00⟩)
#   - Roll to FISHER pole (θ=0.196, expect |10⟩)
#
# Expected Output:
#   - |10⟩ should dominate (~90%)

program SolitonRoll:
    # Initialize at ground state
    soliton q = 0;
    
    # Apply the Soliton Roll (Logical NOT)
    # This rotates θ from 0.0 to 0.196
    q.roll();
    
    # Measure - should be 1
    result = measure(q);
