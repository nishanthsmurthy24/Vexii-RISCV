import os, sys, csv, subprocess
from vcdvcd import VCDVCD
from concurrent.futures import ThreadPoolExecutor

from functools import partial

# Command-line arg parsing (unchanged)
if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} <dir_path>")
    sys.exit(1)

dir_path = sys.argv[1]
if not dir_path.endswith("/"):
    dir_path += "/"

fst_path = dir_path + "wave.fst"
vcd_path = dir_path + "wave.vcd"
act_path = dir_path + "activity_factors.csv"
const_path = dir_path + "constant_bits.txt"

os.makedirs(dir_path, exist_ok=True)

if not os.path.isfile(fst_path):
    print(f"Error: '{fst_path}' not found.")
    sys.exit(1)

subprocess.run(["fst2vcd", "-f", fst_path, "-o", vcd_path], check=True)

print("Parsing VCD... (this may take a bit)")
vcd = VCDVCD(vcd_path, store_tvs=True)

start_time = min((min(tv := vcd[s].tv, default=[(0, '')])[0] for s in vcd.signals))
end_time = max((max(vcd[s].tv, default=[(0, '')])[0] for s in vcd.signals))
total_time = max(end_time - start_time, 1)

def analyze_signal(signal, tv):
    """Compute activity factor and constant bits"""
    # Activity factor
    activity_factor = ((len(tv) - 1) / total_time) * 5 if total_time > 0 else 0

    # Constant bits
    values = [v for _, v in tv]
    if not values:
        return (signal, activity_factor, [])

    max_width = max(len(v) for v in values)
    padded = [v.zfill(max_width) for v in values]

    const_bits = []
    for bit_pos in range(max_width):
        if len(set(row[bit_pos] for row in padded)) == 1:
            const_bits.append(bit_pos)

    return (signal, activity_factor, const_bits)

print("Analyzing signals in parallel...")
with ThreadPoolExecutor() as executor:
    futures = [
        executor.submit(analyze_signal, sig, vcd[sig].tv)
        for sig in vcd.signals
    ]
    results = [f.result() for f in futures]

# Write activity factors
sorted_activity = sorted(results, key=lambda x: x[1], reverse=True)
with open(act_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["SignalName", "ActivityFactor"])
    for signal, af, _ in sorted_activity:
        writer.writerow([signal, f"{af:.8f}"])

print(f"Activity factors written to: {act_path}")

# Write constant bits
with open(const_path, "w") as f:
    f.write("Signals and Constant Bits Report:\n")
    f.write("=" * 40 + "\n\n")
    for signal, _, const_bits in sorted(results, key=lambda x: x[0]):
        if const_bits:
            f.write(f"Signal: {signal}\n")
            f.write(f"Constant Bits: {', '.join(map(str, const_bits))}\n")
            f.write("-" * 40 + "\n")

print(f"Constant bits report written to: {const_path}")
