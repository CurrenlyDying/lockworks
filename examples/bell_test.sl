# Bell State: |00⟩ + |11⟩ Topological Entanglement
# ================================================
# This demonstrates the Schrödinger's Gambit entanglement.
# 
# Expected Output:
#   - |00⟩ and |11⟩ should dominate (combined > 80%)
#   - Error states |01⟩ and |10⟩ should be < 20%

program BellTest:
    # Create superposition: Soliton at Edge (θ=0.1)
    soliton alpha = H;
    
    # Create ground state: Soliton at ROBUST (θ=0.0)
    soliton beta = 0;
    
    # Topological Entanglement (CNOT between data bits)
    entangle(alpha, beta);
    
    # Collapse the wavefunction
    a = measure(alpha);
    b = measure(beta);
