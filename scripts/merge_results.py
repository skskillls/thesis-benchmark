#!/usr/bin/env python3
"""
Merge all benchmark JSON results into a single CSV for analysis.
"""

import json
import os
import glob
import pandas as pd
from pathlib import Path

def load_json_file(filepath):
    """Load a single JSON result file and flatten it."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Flatten nested performance dict
        flat = {
            'tool': data.get('tool', ''),
            'service': data.get('service', ''),
            'dockerfile_type': data.get('dockerfile_type', ''),
            'cache_scenario': data.get('cache_scenario', ''),
            'run_number': data.get('run_number', 0),
            'timestamp': data.get('timestamp', ''),
            'ci_system': data.get('ci_system', ''),
        }
        
        # Add performance metrics
        perf = data.get('performance', {})
        flat['build_duration_seconds'] = perf.get('build_duration_seconds', 0)
        flat['cpu_percent'] = perf.get('cpu_percent', 0)
        flat['cpu_user_seconds'] = perf.get('cpu_user_seconds', 0)
        flat['cpu_system_seconds'] = perf.get('cpu_system_seconds', 0)
        flat['memory_peak_mb'] = perf.get('memory_peak_mb', 0)
        flat['image_size'] = perf.get('image_size', '')
        flat['image_size_bytes'] = perf.get('image_size_bytes', 0)
        flat['cache_hits'] = perf.get('cache_hits', 0)
        flat['cache_total_steps'] = perf.get('cache_total_steps', 0)
        flat['cache_hit_ratio'] = perf.get('cache_hit_ratio', 0)
        flat['exit_code'] = data.get('exit_code', 0)
        flat['source_file'] = os.path.basename(filepath)
        
        return flat
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def main():
    # Find all result directories
    base_dir = Path('.')
    
    # Look for results in multiple locations
    search_paths = [
        'results-github/*/*.json',           
        'results-gitlab/*/*.json',           
        'results-gitlab-public/*/*.json',  
        'results/*.json',
        'final-results/*.json',
    ]
    
    all_records = []
    
    for pattern in search_paths:
        json_files = glob.glob(pattern)
        for filepath in json_files:
            # Skip security scan files (trivy, sbom)
            basename = os.path.basename(filepath)
            if basename.startswith('trivy-') or basename.startswith('sbom-'):
                continue
            if 'benchmark' in basename.lower():
                continue
                
            record = load_json_file(filepath)
            if record:
                all_records.append(record)
    
    if not all_records:
        print("No JSON result files found!")
        print("Searched in:", search_paths)
        return
    
    # Create DataFrame
    df = pd.DataFrame(all_records)
    
    # Sort by tool, service, dockerfile_type, cache_scenario, run_number
    df = df.sort_values(['ci_system', 'tool', 'service', 'dockerfile_type', 'cache_scenario', 'run_number'])
    
    # Save merged CSV
    output_file = 'all_benchmark_results.csv'
    df.to_csv(output_file, index=False)
    print(f"\n Merged {len(df)} records into {output_file}")
    
    # Print summary
    print(f"\n Summary:")
    print(f"   CI Systems: {df['ci_system'].unique().tolist()}")
    print(f"   Tools: {df['tool'].unique().tolist()}")
    print(f"   Services: {df['service'].unique().tolist()}")
    print(f"   Cache Scenarios: {df['cache_scenario'].unique().tolist()}")
    print(f"   Run Numbers: {sorted(df['run_number'].unique().tolist())}")
    print(f"\n   Total Records: {len(df)}")
    
    # Calculate and display statistics
    print("\n" + "="*80)
    print("COMPREHENSIVE STATISTICS BY TOOL & CACHE SCENARIO")
    print("="*80)
    
    # Build Duration Statistics
    print("\n BUILD DURATION (seconds)")
    print("-"*60)
    duration_stats = df.groupby(['ci_system', 'tool', 'cache_scenario']).agg({
        'build_duration_seconds': ['mean', 'std', 'min', 'max', 'count']
    }).round(2)
    print(duration_stats.to_string())
    
    # Image Size Statistics (by tool and dockerfile type)
    print("\n IMAGE SIZE (bytes)")
    print("-"*60)
    size_stats = df.groupby(['tool', 'service', 'dockerfile_type']).agg({
        'image_size_bytes': ['mean', 'min', 'max']
    }).round(0)
    print(size_stats.to_string())
    
    # Memory Statistics
    print("\n PEAK MEMORY USAGE (MB)")
    print("-"*60)
    mem_stats = df.groupby(['ci_system', 'tool', 'cache_scenario']).agg({
        'memory_peak_mb': ['mean', 'std', 'min', 'max']
    }).round(2)
    print(mem_stats.to_string())
    
    # CPU Statistics
    print("\n CPU USAGE (%)")
    print("-"*60)
    cpu_stats = df.groupby(['ci_system', 'tool', 'cache_scenario']).agg({
        'cpu_percent': ['mean', 'std', 'min', 'max']
    }).round(2)
    print(cpu_stats.to_string())
    
    # Cache Hit Ratio Statistics
    print("\n CACHE HIT RATIO")
    print("-"*60)
    cache_stats = df.groupby(['ci_system', 'tool', 'cache_scenario']).agg({
        'cache_hit_ratio': ['mean', 'std', 'min', 'max'],
        'cache_hits': ['mean'],
        'cache_total_steps': ['mean']
    }).round(4)
    print(cache_stats.to_string())
    
    # Save all statistics to separate CSV files
    duration_stats.to_csv('stats_build_duration.csv')
    size_stats.to_csv('stats_image_size.csv')
    mem_stats.to_csv('stats_memory.csv')
    cpu_stats.to_csv('stats_cpu.csv')
    cache_stats.to_csv('stats_cache.csv')
    
    # Create a comprehensive summary table
    print("\n" + "="*80)
    print("SUMMARY TABLE (for thesis)")
    print("="*80)
    
    summary = df.groupby(['ci_system', 'tool', 'cache_scenario']).agg({
        'build_duration_seconds': 'mean',
        'memory_peak_mb': 'mean',
        'cpu_percent': 'mean',
        'image_size_bytes': 'first',
        'cache_hit_ratio': 'mean'
    }).round(2)
    summary.columns = ['Duration (s)', 'Memory (MB)', 'CPU (%)', 'Image Size (bytes)', 'Cache Hit Ratio']
    print(summary.to_string())
    summary.to_csv('thesis_summary_table.csv')
    
    print("\n All statistics saved:")
    print("   - all_benchmark_results.csv (raw data)")
    print("   - stats_build_duration.csv")
    print("   - stats_image_size.csv")
    print("   - stats_memory.csv")
    print("   - stats_cpu.csv")
    print("   - stats_cache.csv")
    print("   - thesis_summary_table.csv (main summary)")

if __name__ == '__main__':
    main()
