"""
Benchmark harness for evaluating code review agent on BugsInPy dataset.

This script:
1. Loads bugs from the BugsInPy dataset
2. Runs the review agent on each bug
3. Tracks success metrics
4. Generates benchmark report
"""

import json
import time
import asyncio
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from datetime import datetime


@dataclass
class BenchmarkResult:
    """Result of running agent on a single bug."""
    bug_id: str
    bug_name: str
    success: bool  # Did tests pass?
    iterations: int  # How many iterations needed?
    tokens_used: int
    cost_usd: float
    latency_seconds: float
    agent_status: str  # "fixed", "failed_max_iterations", "cannot_fix"


class BugsInPyDataset:
    """
    Simulated BugsInPy dataset loader.
    
    In production, would load from: https://github.com/soarsmu/BugsInPy
    """
    
    @staticmethod
    def load_bugs(limit: int = 50) -> List[Dict[str, Any]]:
        """
        Load bugs from BugsInPy dataset.
        
        Args:
            limit: Maximum number of bugs to load
        
        Returns:
            List of bug metadata dicts with keys:
            - bug_id: Unique identifier
            - project: Project name
            - repo_url: Repository URL
            - pr_number: Associated PR number
            - buggy_commit: Commit with bug
            - fixed_commit: Commit with fix
        """
        # Placeholder: In production, would load actual dataset
        # For demonstration, return mock bugs
        bugs = [
            {
                "bug_id": f"bug_{i:03d}",
                "project": "project_name",
                "repo_url": f"https://github.com/org/project{i}",
                "pr_number": 100 + i,
                "buggy_commit": f"buggy_{i}",
                "fixed_commit": f"fixed_{i}",
            }
            for i in range(min(limit, 50))
        ]
        return bugs


class Benchmark:
    """Run benchmark suite on the code review agent."""
    
    def __init__(self, agent_graph, output_path: str = "benchmark_results.json"):
        """
        Initialize benchmark.
        
        Args:
            agent_graph: Compiled LangGraph StateGraph
            output_path: Where to save results JSON
        """
        self.agent_graph = agent_graph
        self.output_path = output_path
        self.results: List[BenchmarkResult] = []
    
    async def run_on_bug(self, bug: Dict[str, Any]) -> BenchmarkResult:
        """
        Run agent on a single bug from the dataset.
        
        Args:
            bug: Bug metadata
        
        Returns:
            BenchmarkResult for this bug
        """
        
        # TODO: In production:
        # 1. Clone bug repo
        # 2. Checkout buggy state
        # 3. Create initial agent state with PR diff
        # 4. Run agent_graph.invoke(initial_state)
        # 5. Collect results
        
        # For demonstration, simulate agent run
        start_time = time.time()
        
        # Placeholder simulation
        success = bug["bug_id"].endswith(("0", "5"))  # Simulate 20% fix rate
        iterations = 2 if success else 3
        tokens = 800 + (iterations * 300)
        cost = tokens * (0.015 / 1000) + (tokens * 0.3 * (0.06 / 1000))
        latency = 15.0 + (iterations * 5)
        status = "fixed" if success else "failed_max_iterations"
        
        elapsed = time.time() - start_time
        
        return BenchmarkResult(
            bug_id=bug["bug_id"],
            bug_name=bug["project"],
            success=success,
            iterations=iterations,
            tokens_used=tokens,
            cost_usd=cost,
            latency_seconds=latency,
            agent_status=status,
        )
    
    async def run(self, max_bugs: int = 50) -> None:
        """
        Run benchmark on dataset.
        
        Args:
            max_bugs: Maximum number of bugs to test
        """
        
        print(f"Loading BugsInPy dataset (max {max_bugs} bugs)...")
        bugs = BugsInPyDataset.load_bugs(max_bugs)
        
        print(f"Running benchmark on {len(bugs)} bugs...")
        
        for i, bug in enumerate(bugs, 1):
            print(f"  [{i}/{len(bugs)}] {bug['bug_id']}...", end=" ", flush=True)
            
            result = await self.run_on_bug(bug)
            self.results.append(result)
            
            status_emoji = "✅" if result.success else "❌"
            print(f"{status_emoji} ({result.iterations} iter, {result.latency_seconds:.1f}s)")
        
        print("\nBenchmark complete!")
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate benchmark report from results.
        
        Returns:
            Report dict with aggregate statistics
        """
        
        if not self.results:
            return {"error": "No results"}
        
        successful = [r for r in self.results if r.success]
        
        fix_rate = len(successful) / len(self.results)
        avg_iterations = sum(r.iterations for r in self.results) / len(self.results)
        avg_tokens = sum(r.tokens_used for r in self.results) / len(self.results)
        avg_cost = sum(r.cost_usd for r in self.results) / len(self.results)
        avg_latency = sum(r.latency_seconds for r in self.results) / len(self.results)
        
        # Only compute for successful fixes
        if successful:
            avg_iterations_for_fixes = sum(r.iterations for r in successful) / len(successful)
            avg_tokens_for_fixes = sum(r.tokens_used for r in successful) / len(successful)
            avg_cost_for_fixes = sum(r.cost_usd for r in successful) / len(successful)
        else:
            avg_iterations_for_fixes = 0
            avg_tokens_for_fixes = 0
            avg_cost_for_fixes = 0
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_bugs": len(self.results),
            "bugs_fixed": len(successful),
            "fix_rate_percent": round(fix_rate * 100, 1),
            "avg_iterations_all": round(avg_iterations, 2),
            "avg_iterations_successful": round(avg_iterations_for_fixes, 2),
            "avg_tokens_per_bug": round(avg_tokens, 0),
            "avg_tokens_per_fix": round(avg_tokens_for_fixes, 0),
            "avg_cost_per_bug_usd": round(avg_cost, 4),
            "avg_cost_per_fix_usd": round(avg_cost_for_fixes, 4),
            "avg_latency_seconds": round(avg_latency, 1),
            "total_cost_usd": round(sum(r.cost_usd for r in self.results), 2),
        }
    
    def save_results(self) -> None:
        """Save benchmark results to JSON file."""
        
        report = self.generate_report()
        report["detailed_results"] = [asdict(r) for r in self.results]
        
        with open(self.output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nResults saved to {self.output_path}")
    
    def print_summary(self) -> None:
        """Print benchmark summary to console."""
        
        report = self.generate_report()
        
        print("\n" + "=" * 70)
        print("BENCHMARK REPORT")
        print("=" * 70)
        print(f"Total bugs tested:          {report['total_bugs']}")
        print(f"Bugs fixed:                 {report['bugs_fixed']}")
        print(f"Fix rate:                   {report['fix_rate_percent']}%")
        print(f"\nAverage iterations:         {report['avg_iterations_all']}")
        print(f"Avg iterations (fixed):     {report['avg_iterations_successful']}")
        print(f"\nAvg tokens per bug:         {report['avg_tokens_per_bug']:.0f}")
        print(f"Avg tokens per fix:         {report['avg_tokens_per_fix']:.0f}")
        print(f"\nAvg cost per bug:           ${report['avg_cost_per_bug_usd']:.4f}")
        print(f"Avg cost per fix:           ${report['avg_cost_per_fix_usd']:.4f}")
        print(f"Total cost:                 ${report['total_cost_usd']:.2f}")
        print(f"\nAvg latency (seconds):      {report['avg_latency_seconds']:.1f}s")
        print("=" * 70)


async def main():
    """Run benchmark suite."""
    
    # TODO: Import and use actual agent graph
    # from src.agent.graph import build_agent_graph
    # agent_graph = build_agent_graph()
    
    benchmark = Benchmark(agent_graph=None)  # Placeholder
    
    # Run benchmark
    await benchmark.run(max_bugs=50)
    
    # Print and save results
    benchmark.print_summary()
    benchmark.save_results()


if __name__ == "__main__":
    asyncio.run(main())
