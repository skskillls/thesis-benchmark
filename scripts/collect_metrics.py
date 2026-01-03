#!/usr/bin/env python3
"""
============================================================================
collect_metrics.py - Aggregates benchmark JSON results into CSV format
============================================================================
"""

import json
import glob
import csv
import os
import statistics
from collections import defaultdict


def load_results(results_dir: str) -> list[dict]:
    """Load all JSON result files from the results directory."""
    results = []
    
    for pattern in [f"{results_dir}/*.json", f"{results_dir}/**/*.json"]:
        for filepath in glob.glob(pattern, recursive=True):
            # Skip security scan files
            if "trivy" in filepath or "sbom" in filepath or "security" in filepath:
                continue
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    
                    # Flatten nested performance metrics
                    flat = {
                        'tool': data.get('tool'),
                        'service': data.get('service'),
                        'dockerfile_type': data.get('dockerfile_type'),
                        'cache_scenario': data.get('cache_scenario'),
                        'run_number': data.get('run_number'),
                        'timestamp': data.get('timestamp'),
                        'ci_system': data.get('ci_system'),
                        'exit_code': data.get('exit_code', 0)
                    }
                    
                    # Handle nested performance structure
                    perf = data.get('performance', data)
                    flat.update({
                        'build_duration_seconds': perf.get('build_duration_seconds'),
                        'cpu_percent': perf.get('cpu_percent', 0),
                        'cpu_user_seconds': perf.get('cpu_user_seconds', 0),
                        'cpu_system_seconds': perf.get('cpu_system_seconds', 0),
                        'memory_peak_mb': perf.get('memory_peak_mb', 0),
                        'image_size': perf.get('image_size'),
                        'image_size_bytes': perf.get('image_size_bytes', 0),
                        'cache_hits': perf.get('cache_hits', 0),
                        'cache_total_steps': perf.get('cache_total_steps', 0),
                        'cache_hit_ratio': perf.get('cache_hit_ratio', 0)
                    })
                    
                    results.append(flat)
                    
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not parse {filepath}: {e}")
    
    return results


def export_to_csv(results: list[dict], output_path: str):
    """Export results to CSV format."""
    if not results:
        print("No results to export")
        return
    
    fieldnames = [
        'tool', 'service', 'dockerfile_type', 'cache_scenario', 'run_number',
        'timestamp', 'ci_system', 'build_duration_seconds',
        'cpu_percent', 'cpu_user_seconds', 'cpu_system_seconds',
        'memory_peak_mb', 'image_size', 'image_size_bytes',
        'cache_hits', 'cache_total_steps', 'cache_hit_ratio', 'exit_code'
    ]
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Exported {len(results)} results to {output_path}")


def print_summary(results: list[dict]):
    """Print summary statistics to console."""
    groups = defaultdict(list)
    
    for r in results:
        if r.get('build_duration_seconds') is not None:
            key = (r['tool'], r['service'], r['dockerfile_type'], r['cache_scenario'])
            groups[key].append(r)
    
    print("\n" + "=" * 100)
    print("BENCHMARK SUMMARY")
    print("=" * 100)
    
    header = f"{'Tool':<10} {'Service':<15} {'Type':<10} {'Scenario':<8} {'Duration':<12} {'CPU%':<8} {'MemMB':<10} {'Cache':<8} {'N'}"
    print(header)
    print("-" * 100)
    
    for key, runs in sorted(groups.items()):
        tool, service, dtype, scenario = key
        
        durations = [r['build_duration_seconds'] for r in runs if r['build_duration_seconds']]
        cpu = [r['cpu_percent'] for r in runs if r.get('cpu_percent')]
        mem = [r['memory_peak_mb'] for r in runs if r.get('memory_peak_mb')]
        cache = [r['cache_hit_ratio'] for r in runs if r.get('cache_hit_ratio')]
        
        mean_dur = statistics.mean(durations) if durations else 0
        mean_cpu = statistics.mean(cpu) if cpu else 0
        mean_mem = statistics.mean(mem) if mem else 0
        mean_cache = statistics.mean(cache) if cache else 0
        
        print(f"{tool:<10} {service:<15} {dtype:<10} {scenario:<8} {mean_dur:<12.2f} {mean_cpu:<8.1f} {mean_mem:<10.1f} {mean_cache:<8.4f} {len(runs)}")


def main():
    results_dir = os.environ.get('RESULTS_DIR', './results')
    output_csv = os.environ.get('OUTPUT_CSV', f'{results_dir}/benchmark_results.csv')
    
    print(f"Loading results from: {results_dir}")
    results = load_results(results_dir)
    
    if not results:
        print("No benchmark results found!")
        return
    
    print(f"Loaded {len(results)} result files")
    
    # Export to CSV
    export_to_csv(results, output_csv)
    
    # Print summary
    print_summary(results)


if __name__ == '__main__':
    main()
