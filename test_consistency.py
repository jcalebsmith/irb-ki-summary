#!/usr/bin/env python3
"""
Consistency Test Script
Tests the same PDF multiple times to measure output consistency
"""

import sys
import json
import hashlib
from pathlib import Path
from app.summary import generate_summary
import numpy as np
from datetime import datetime
import difflib
from collections import defaultdict

def get_text_hash(text):
    """Generate hash of text for comparison"""
    return hashlib.md5(text.encode()).hexdigest()

def calculate_similarity(text1, text2):
    """Calculate similarity ratio between two texts"""
    return difflib.SequenceMatcher(None, text1, text2).ratio() * 100

def run_consistency_test(pdf_path, num_iterations=5):
    """Run the same PDF multiple times and check consistency"""
    
    print(f"Testing consistency with: {pdf_path}")
    print(f"Running {num_iterations} iterations...")
    print("=" * 80)
    
    results = []
    section_texts = defaultdict(list)
    section_hashes = defaultdict(list)
    
    # Run multiple iterations
    for i in range(num_iterations):
        print(f"\nIteration {i+1}/{num_iterations}...")
        try:
            summary = generate_summary(pdf_path)
            results.append(summary)
            
            # Collect texts and hashes for each section
            for section, text in summary.items():
                if section != "Total Summary":
                    section_texts[section].append(text)
                    section_hashes[section].append(get_text_hash(text))
            
            print(f"✓ Iteration {i+1} complete")
            
        except Exception as e:
            print(f"✗ Error in iteration {i+1}: {e}")
            continue
    
    if len(results) < 2:
        print("Not enough successful iterations to analyze consistency")
        return
    
    print("\n" + "=" * 80)
    print("CONSISTENCY ANALYSIS")
    print("=" * 80)
    
    # Analyze each section
    section_consistency = {}
    
    for section in section_texts:
        texts = section_texts[section]
        hashes = section_hashes[section]
        
        # Check if all outputs are identical
        unique_hashes = len(set(hashes))
        is_identical = unique_hashes == 1
        
        # Calculate character length statistics
        lengths = [len(text) for text in texts]
        mean_length = np.mean(lengths)
        std_length = np.std(lengths)
        cv_length = (std_length / mean_length * 100) if mean_length > 0 else 0
        
        # Calculate pairwise similarity
        similarities = []
        for i in range(len(texts)):
            for j in range(i+1, len(texts)):
                sim = calculate_similarity(texts[i], texts[j])
                similarities.append(sim)
        
        avg_similarity = np.mean(similarities) if similarities else 100
        min_similarity = np.min(similarities) if similarities else 100
        
        section_consistency[section] = {
            "identical": is_identical,
            "unique_versions": unique_hashes,
            "mean_length": mean_length,
            "std_length": std_length,
            "cv_percent": cv_length,
            "avg_similarity": avg_similarity,
            "min_similarity": min_similarity,
            "iterations": len(texts)
        }
    
    # Print results
    print("\nPer-Section Analysis:")
    print("-" * 40)
    
    all_identical = True
    total_cv = []
    total_similarity = []
    
    for section in sorted(section_consistency.keys()):
        stats = section_consistency[section]
        print(f"\n{section}:")
        
        if stats["identical"]:
            print(f"  ✓ IDENTICAL across all {stats['iterations']} iterations")
        else:
            print(f"  ✗ {stats['unique_versions']} unique versions found")
            all_identical = False
        
        print(f"  Length CV: {stats['cv_percent']:.1f}%")
        print(f"  Avg similarity: {stats['avg_similarity']:.1f}%")
        print(f"  Min similarity: {stats['min_similarity']:.1f}%")
        
        total_cv.append(stats['cv_percent'])
        total_similarity.append(stats['avg_similarity'])
    
    # Overall metrics
    print("\n" + "-" * 40)
    print("Overall Metrics:")
    print(f"  All sections identical: {'Yes ✓' if all_identical else 'No ✗'}")
    print(f"  Average CV across sections: {np.mean(total_cv):.1f}%")
    print(f"  Average similarity: {np.mean(total_similarity):.1f}%")
    
    # Check against targets
    target_cv = 15
    target_similarity = 95
    
    print("\n" + "-" * 40)
    print("Target Achievement:")
    
    avg_cv = np.mean(total_cv)
    avg_sim = np.mean(total_similarity)
    
    if avg_cv <= target_cv:
        print(f"  ✓ CV target met: {avg_cv:.1f}% ≤ {target_cv}%")
    else:
        print(f"  ✗ CV target not met: {avg_cv:.1f}% > {target_cv}%")
    
    if avg_sim >= target_similarity:
        print(f"  ✓ Similarity target met: {avg_sim:.1f}% ≥ {target_similarity}%")
    else:
        print(f"  ✗ Similarity target not met: {avg_sim:.1f}% < {target_similarity}%")
    
    # Show example differences if not identical
    if not all_identical:
        print("\n" + "=" * 80)
        print("EXAMPLE DIFFERENCES")
        print("=" * 80)
        
        for section, stats in section_consistency.items():
            if not stats["identical"]:
                texts = section_texts[section]
                if len(texts) >= 2:
                    print(f"\n{section} - Comparing first two iterations:")
                    print("-" * 40)
                    
                    # Show first 200 chars of difference
                    diff = list(difflib.unified_diff(
                        texts[0][:200].splitlines(keepends=True),
                        texts[1][:200].splitlines(keepends=True),
                        fromfile='Iteration 1',
                        tofile='Iteration 2',
                        lineterm=''
                    ))
                    
                    if diff:
                        for line in diff[:10]:  # Show first 10 lines of diff
                            print(line.rstrip())
                    
                    break  # Just show one example
    
    # Save detailed report - convert numpy types to Python types for JSON serialization
    report = {
        "timestamp": datetime.now().isoformat(),
        "pdf_file": str(pdf_path),
        "iterations": num_iterations,
        "successful_iterations": len(results),
        "all_identical": bool(all_identical),
        "average_cv": float(avg_cv),
        "average_similarity": float(avg_sim),
        "section_consistency": {
            section: {
                "identical": bool(stats["identical"]),
                "unique_versions": int(stats["unique_versions"]),
                "mean_length": float(stats["mean_length"]),
                "std_length": float(stats["std_length"]),
                "cv_percent": float(stats["cv_percent"]),
                "avg_similarity": float(stats["avg_similarity"]),
                "min_similarity": float(stats["min_similarity"]),
                "iterations": int(stats["iterations"])
            }
            for section, stats in section_consistency.items()
        },
        "targets_met": {
            "cv_target": bool(avg_cv <= target_cv),
            "similarity_target": bool(avg_sim >= target_similarity)
        }
    }
    
    report_file = f"consistency_report_{Path(pdf_path).stem}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✓ Detailed report saved to: {report_file}")
    
    # Save all iterations for debugging
    iterations_file = f"iterations_{Path(pdf_path).stem}.json"
    with open(iterations_file, 'w') as f:
        json.dump({"iterations": results}, f, indent=2)
    
    print(f"✓ All iterations saved to: {iterations_file}")
    
    # Save section comparisons - organize by section for easy comparison
    sections_comparison = {}
    for section in section_texts:
        sections_comparison[section] = {
            "all_outputs": section_texts[section],
            "hashes": section_hashes[section],
            "identical": section_consistency[section]["identical"],
            "unique_versions": section_consistency[section]["unique_versions"],
            "similarity_matrix": []
        }
        
        # Add pairwise similarity matrix for this section
        texts = section_texts[section]
        similarity_matrix = []
        for i in range(len(texts)):
            row = []
            for j in range(len(texts)):
                if i == j:
                    row.append(100.0)
                else:
                    row.append(calculate_similarity(texts[i], texts[j]))
            similarity_matrix.append(row)
        sections_comparison[section]["similarity_matrix"] = similarity_matrix
    
    sections_file = f"sections_comparison_{Path(pdf_path).stem}.json"
    with open(sections_file, 'w') as f:
        json.dump(sections_comparison, f, indent=2)
    
    print(f"✓ Section comparisons saved to: {sections_file}")
    
    # Save side-by-side comparison text files for non-identical sections
    comparison_dir = Path(f"comparisons_{Path(pdf_path).stem}")
    comparison_dir.mkdir(exist_ok=True)
    
    for section, stats in section_consistency.items():
        if not stats["identical"]:
            # Clean section name for filename
            clean_section = section.replace(" ", "_").replace("/", "_").replace(":", "")
            
            # Save all iterations of this section to separate text files
            texts = section_texts[section]
            for i, text in enumerate(texts):
                section_file = comparison_dir / f"{clean_section}_iteration_{i+1}.txt"
                with open(section_file, 'w', encoding='utf-8') as f:
                    f.write(f"=== {section} - Iteration {i+1} ===\n\n")
                    f.write(text)
            
            # Create a diff file showing differences
            if len(texts) >= 2:
                diff_file = comparison_dir / f"{clean_section}_diff.txt"
                with open(diff_file, 'w', encoding='utf-8') as f:
                    f.write(f"=== Differences in {section} ===\n\n")
                    for i in range(len(texts) - 1):
                        f.write(f"\n--- Iteration {i+1} vs {i+2} ---\n")
                        diff_lines = list(difflib.unified_diff(
                            texts[i].splitlines(keepends=True),
                            texts[i+1].splitlines(keepends=True),
                            fromfile=f'Iteration {i+1}',
                            tofile=f'Iteration {i+2}',
                            lineterm=''
                        ))
                        f.writelines(diff_lines[:100])  # Limit to first 100 lines
    
    if comparison_dir.exists() and any(comparison_dir.iterdir()):
        print(f"✓ Individual section outputs saved to: {comparison_dir}/")

def main():
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
        iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    else:
        # Use configuration for default test PDF
        sys.path.append(str(Path(__file__).parent / "app"))
        from config import get_test_pdf_path
        pdf_path = get_test_pdf_path()
        iterations = 5
    
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    run_consistency_test(pdf_path, iterations)

if __name__ == "__main__":
    main()