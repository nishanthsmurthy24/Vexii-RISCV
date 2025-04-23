#!/project/sartori00/conda/bin/python3

import subprocess
import os
import sys
import csv
from vcdvcd import VCDVCD

# Ensure the script receives a directory path as an argument
if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} <dir_path>")
    sys.exit(1)

# Get the directory path from the command-line argument
dir_path = sys.argv[1]

# Ensure the directory path ends with a slash for consistency
if not dir_path.endswith("/"):
    dir_path += "/"

# Set paths for wave.fst, wave.vcd, and activity_factors.csv
fst_path = dir_path + "wave.fst"      # Path to the input FST file
vcd_path = dir_path + "wave.vcd"      # Path to the output VCD file
act_path = dir_path + "activity_factors.csv"  # Path to the activity factors CSV file
const_path = dir_path + "constant_bits.txt" # Path for 

# Ensure the directory exists
os.makedirs(dir_path, exist_ok=True)

# Check if wave.fst exists
if not os.path.isfile(fst_path):
    print(f"Error: '{fst_path}' not found.")
    sys.exit(1)

# Convert wave.fst to wave.vcd
try:
    subprocess.run(["fst2vcd", "-f", fst_path, "-o", vcd_path], check=True)
except subprocess.CalledProcessError:
    print("Error: fst2vcd conversion failed. Ensure fst2vcd is installed and in your PATH.")
    sys.exit(1)

# Load the VCD file
vcd = VCDVCD(vcd_path)

# Get total simulation time
start_time = min(min(vcd[signal].tv, default=[0])[0] for signal in vcd.signals)
end_time = max(max(vcd[signal].tv, default=[0])[0] for signal in vcd.signals)
total_time = end_time - start_time if end_time > start_time else 1  # Avoid division by zero

# Calculate activity factors
activity_factors = {
    signal: ((len(vcd[signal].tv) - 1) / total_time) * 5 if total_time > 0 else 0
    for signal in vcd.signals
}

# Sort by activity factor in descending order
sorted_activity_factors = sorted(activity_factors.items(), key=lambda x: x[1], reverse=True)

# Write results to the activity_factors.csv file
with open(act_path, "w", newline="") as f:
    csv_writer = csv.writer(f)
    # Write header
    csv_writer.writerow(["SignalName", "ActivityFactor"])
    # Write data
    for signal, activity_factor in sorted_activity_factors:
        csv_writer.writerow([signal, f"{activity_factor:.8f}"])

print(f"Activity factors written to: {act_path}")

# Helper function to find constant bits
def find_constant_bits(signal_values):
    if len(signal_values) == 0:
        return []
    
    # Extract all values and check their bit width
    all_values = [value for _, value in signal_values]

    # Ensure all values are the same length (e.g., 32 bits)
    max_width = max(len(v) for v in all_values)
    padded_values = [v.zfill(max_width) for v in all_values]

    # Transpose to check bit-wise consistency
    constant_bits = []
    for bit_pos in range(max_width):
        bit_column = {v[bit_pos] for v in padded_values}
        if len(bit_column) == 1:  # No toggling if only one unique value
            constant_bits.append(bit_pos)

    return constant_bits

# Collect signals with constant bits
constant_bits_report = []

for signal in vcd.signals:
    signal_values = vcd[signal].tv
    constant_bits = find_constant_bits(signal_values)

    if constant_bits:
        constant_bits_report.append((signal, constant_bits))
        
# Sort the report by signal name in ascending order
constant_bits_report.sort(key=lambda x: x[0])

# Write results to the constant_bits.txt file
with open(const_path, "w") as f:
    f.write("Signals and Constant Bits Report:\n")
    f.write("=" * 40 + "\n\n")
    for signal, bits in constant_bits_report:
        bit_positions = ", ".join(map(str, bits))
        f.write(f"Signal: {signal}\n")
        f.write(f"Constant Bits: {bit_positions}\n")
        f.write("-" * 40 + "\n")

print(f"Constant bits report written to: {const_path}")