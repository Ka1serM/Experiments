#!/usr/bin/env bash
set -uo pipefail

PBRT=/home/marcel/GitRepositories/ROSS/build/pbrt-v4/pbrt
SCENES_DIR=/home/marcel/GitRepositories/Experiments/assets/scenes/slanted-edge-target
OUT_DIR=/home/marcel/GitRepositories/Experiments/traces
mkdir -p "$OUT_DIR"

run_gpu() {
    local name=$1 scene=$2 spp=$3
    local out="$OUT_DIR/gpu_${spp}spp_$name.nsys-rep"
    echo "=== GPU: $name (--spp $spp) ==="
    cd "$SCENES_DIR"
    if [ -f "$out" ]; then
        echo "  exists: $out ($(du -h "$out" | cut -f1))"
        return 0
    fi
    sudo nsys profile -o "${out%.nsys-rep}" --trace=cuda,nvtx -f true \
        "$PBRT" --gpu --spp "$spp" "$scene" 2>&1
    echo "  done: $(ls -lh "$out" 2>/dev/null | awk '{print $5}')"
}

run_cpu() {
    local name=$1 scene=$2 spp=$3
    local out="$OUT_DIR/cpu_${spp}spp_$name.nsys-rep"
    echo "=== CPU: $name (--spp $spp) ==="
    cd "$SCENES_DIR"
    if [ -f "$out" ]; then
        echo "  exists: $out ($(du -h "$out" | cut -f1))"
        return 0
    fi
    nsys profile -o "${out%.nsys-rep}" --trace=nvtx -f true \
        "$PBRT" --spp "$spp" "$scene" 2>&1
    echo "  done: $(ls -lh "$out" 2>/dev/null | awk '{print $5}')"
}

echo "────────────────────────────────────────────"
echo "Output dir: $OUT_DIR"
echo "Scenes dir: $SCENES_DIR"
echo "────────────────────────────────────────────"
echo ""

# GPU (sudo erforderlich, hier einzeln aufrufbar)
run_gpu perspective        perspective.pbrt                            1
run_gpu perspective        perspective.pbrt                           16
run_gpu interpolatedpsf    rossinterpolatedpsf_lg_innotek_31x18.pbrt  1
run_gpu interpolatedpsf    rossinterpolatedpsf_lg_innotek_31x18.pbrt 16
run_gpu realistic          rossrealistic_lg_innotek.pbrt               1
run_gpu realistic          rossrealistic_lg_innotek.pbrt            4096

# CPU
run_cpu perspective        perspective.pbrt                            1
run_cpu interpolatedpsf    rossinterpolatedpsf_lg_innotek_31x18.pbrt   1
run_cpu realistic          rossrealistic_lg_innotek.pbrt                1

echo ""
echo "=== All done ==="
ls -lh "$OUT_DIR"/*.nsys-rep 2>/dev/null | awk '{print $5, $NF}'
