#!/usr/bin/env python3
"""
Generate comprehensive test report for dbt-to-lookml.

This script analyzes test results, coverage data, and performance metrics
to create detailed reports for developers and CI/CD systems.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET


class TestReportGenerator:
    """Generate comprehensive test reports from multiple sources."""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.report_data: Dict[str, Any] = {
            "generated_at": datetime.now().isoformat(),
            "test_results": {},
            "coverage": {},
            "performance": {},
            "summary": {}
        }
    
    def parse_pytest_xml(self, xml_file: Path) -> Dict[str, Any]:
        """Parse pytest XML results."""
        if not xml_file.exists():
            return {}
        
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            results = {
                "total_tests": int(root.get("tests", 0)),
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 0,
                "time": float(root.get("time", 0)),
                "test_cases": []
            }
            
            for testcase in root.iter("testcase"):
                case = {
                    "name": testcase.get("name"),
                    "classname": testcase.get("classname"),
                    "time": float(testcase.get("time", 0)),
                    "status": "passed"
                }
                
                if testcase.find("failure") is not None:
                    case["status"] = "failed"
                    results["failed"] += 1
                    failure = testcase.find("failure")
                    case["failure"] = {
                        "message": failure.get("message", ""),
                        "type": failure.get("type", ""),
                        "text": failure.text or ""
                    }
                elif testcase.find("error") is not None:
                    case["status"] = "error"
                    results["errors"] += 1
                    error = testcase.find("error")
                    case["error"] = {
                        "message": error.get("message", ""),
                        "type": error.get("type", ""),
                        "text": error.text or ""
                    }
                elif testcase.find("skipped") is not None:
                    case["status"] = "skipped"
                    results["skipped"] += 1
                    skipped = testcase.find("skipped")
                    case["skip_reason"] = skipped.get("message", "")
                else:
                    results["passed"] += 1
                
                results["test_cases"].append(case)
            
            return results
            
        except Exception as e:
            print(f"Error parsing pytest XML {xml_file}: {e}")
            return {}
    
    def parse_coverage_xml(self, xml_file: Path) -> Dict[str, Any]:
        """Parse coverage XML results."""
        if not xml_file.exists():
            return {}
        
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            coverage_data = {
                "line_rate": float(root.get("line-rate", 0)) * 100,
                "branch_rate": float(root.get("branch-rate", 0)) * 100,
                "lines_covered": int(root.get("lines-covered", 0)),
                "lines_valid": int(root.get("lines-valid", 0)),
                "branches_covered": int(root.get("branches-covered", 0)),
                "branches_valid": int(root.get("branches-valid", 0)),
                "packages": []
            }
            
            packages = root.find("packages")
            if packages is not None:
                for package in packages.iter("package"):
                    package_data = {
                        "name": package.get("name"),
                        "line_rate": float(package.get("line-rate", 0)) * 100,
                        "branch_rate": float(package.get("branch-rate", 0)) * 100,
                        "classes": []
                    }
                    
                    classes = package.find("classes")
                    if classes is not None:
                        for cls in classes.iter("class"):
                            class_data = {
                                "name": cls.get("name"),
                                "filename": cls.get("filename"),
                                "line_rate": float(cls.get("line-rate", 0)) * 100,
                                "branch_rate": float(cls.get("branch-rate", 0)) * 100,
                            }
                            package_data["classes"].append(class_data)
                    
                    coverage_data["packages"].append(package_data)
            
            return coverage_data
            
        except Exception as e:
            print(f"Error parsing coverage XML {xml_file}: {e}")
            return {}
    
    def parse_test_results_json(self, json_file: Path) -> Dict[str, Any]:
        """Parse JSON test results from run-tests.py."""
        if not json_file.exists():
            return {}
        
        try:
            with open(json_file) as f:
                return json.load(f)
        except Exception as e:
            print(f"Error parsing test results JSON {json_file}: {e}")
            return {}
    
    def analyze_performance_data(self) -> Dict[str, Any]:
        """Analyze performance test data."""
        # Look for performance test outputs
        performance_data = {
            "benchmarks": [],
            "slow_tests": [],
            "memory_usage": {},
            "recommendations": []
        }
        
        # Parse pytest benchmark results if available
        benchmark_file = self.root_dir / ".benchmarks" / "results.json"
        if benchmark_file.exists():
            try:
                with open(benchmark_file) as f:
                    benchmark_data = json.load(f)
                    performance_data["benchmarks"] = benchmark_data
            except Exception as e:
                print(f"Error parsing benchmark data: {e}")
        
        return performance_data
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate overall summary."""
        summary = {
            "overall_status": "unknown",
            "test_suite_status": {},
            "coverage_status": "unknown",
            "performance_status": "unknown",
            "recommendations": [],
            "metrics": {}
        }
        
        # Analyze test results
        if self.report_data["test_results"]:
            total_tests = 0
            total_passed = 0
            total_failed = 0
            
            for suite_name, results in self.report_data["test_results"].items():
                if isinstance(results, dict) and "passed" in results:
                    status = "passed" if results["passed"] else "failed"
                    summary["test_suite_status"][suite_name] = status
                    
                    if "total_tests" in results:
                        total_tests += results["total_tests"]
                        total_passed += results.get("passed", 0)
                        total_failed += results.get("failed", 0)
            
            summary["metrics"]["total_tests"] = total_tests
            summary["metrics"]["pass_rate"] = (total_passed / total_tests * 100) if total_tests > 0 else 0
            
            # Overall test status
            if total_failed == 0 and total_tests > 0:
                summary["overall_status"] = "passed"
            elif total_failed > 0:
                summary["overall_status"] = "failed"
        
        # Analyze coverage
        if self.report_data["coverage"]:
            line_rate = self.report_data["coverage"].get("line_rate", 0)
            branch_rate = self.report_data["coverage"].get("branch_rate", 0)
            
            if line_rate >= 95 and branch_rate >= 90:
                summary["coverage_status"] = "excellent"
            elif line_rate >= 85 and branch_rate >= 80:
                summary["coverage_status"] = "good"
            elif line_rate >= 70:
                summary["coverage_status"] = "acceptable"
            else:
                summary["coverage_status"] = "poor"
                summary["recommendations"].append("Improve test coverage - currently below 70%")
            
            summary["metrics"]["line_coverage"] = line_rate
            summary["metrics"]["branch_coverage"] = branch_rate
        
        # Performance analysis
        if self.report_data["performance"]:
            summary["performance_status"] = "analyzed"
            # Add performance recommendations based on data
        
        return summary
    
    def generate_html_report(self, output_file: Path) -> None:
        """Generate HTML report."""
        html_template = '''
<!DOCTYPE html>
<html>
<head>
    <title>dbt-to-lookml Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; }
        .status-passed { color: green; font-weight: bold; }
        .status-failed { color: red; font-weight: bold; }
        .status-skipped { color: orange; font-weight: bold; }
        .metrics { display: flex; gap: 20px; }
        .metric { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
        .recommendations { background-color: #fff3cd; padding: 15px; border-radius: 5px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .progress-bar { background-color: #f0f0f0; border-radius: 3px; overflow: hidden; }
        .progress-fill { height: 20px; background-color: #4CAF50; text-align: center; line-height: 20px; color: white; }
    </style>
</head>
<body>
    <div class="header">
        <h1>dbt-to-lookml Test Report</h1>
        <p>Generated: {generated_at}</p>
        <p>Overall Status: <span class="status-{overall_status}">{overall_status_text}</span></p>
    </div>
    
    <div class="section">
        <h2>Summary Metrics</h2>
        <div class="metrics">
            {metrics_html}
        </div>
    </div>
    
    <div class="section">
        <h2>Test Results</h2>
        {test_results_html}
    </div>
    
    <div class="section">
        <h2>Coverage Report</h2>
        {coverage_html}
    </div>
    
    {recommendations_html}
    
    <div class="section">
        <h2>Detailed Results</h2>
        <details>
            <summary>Raw JSON Data</summary>
            <pre>{raw_json}</pre>
        </details>
    </div>
</body>
</html>
        '''
        
        # Generate HTML components
        summary = self.report_data["summary"]
        
        # Metrics HTML
        metrics_html = ""
        if "metrics" in summary:
            for key, value in summary["metrics"].items():
                if isinstance(value, float):
                    value = f"{value:.2f}%"
                metrics_html += f'<div class="metric"><h3>{key.replace("_", " ").title()}</h3><p>{value}</p></div>'
        
        # Test results HTML
        test_results_html = "<table><tr><th>Test Suite</th><th>Status</th></tr>"
        for suite, status in summary.get("test_suite_status", {}).items():
            status_class = f"status-{status}"
            test_results_html += f'<tr><td>{suite.replace("_", " ").title()}</td><td><span class="{status_class}">{status.upper()}</span></td></tr>'
        test_results_html += "</table>"
        
        # Coverage HTML
        coverage_html = ""
        if self.report_data["coverage"]:
            line_rate = self.report_data["coverage"].get("line_rate", 0)
            branch_rate = self.report_data["coverage"].get("branch_rate", 0)
            
            coverage_html = f'''
            <div class="metric">
                <h3>Line Coverage</h3>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {line_rate}%">{line_rate:.1f}%</div>
                </div>
            </div>
            <div class="metric">
                <h3>Branch Coverage</h3>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {branch_rate}%">{branch_rate:.1f}%</div>
                </div>
            </div>
            '''
        
        # Recommendations HTML
        recommendations_html = ""
        if summary.get("recommendations"):
            recommendations_html = '<div class="section recommendations"><h2>Recommendations</h2><ul>'
            for rec in summary["recommendations"]:
                recommendations_html += f"<li>{rec}</li>"
            recommendations_html += "</ul></div>"
        
        # Fill template
        html_content = html_template.format(
            generated_at=self.report_data["generated_at"],
            overall_status=summary.get("overall_status", "unknown"),
            overall_status_text=summary.get("overall_status", "unknown").upper(),
            metrics_html=metrics_html,
            test_results_html=test_results_html,
            coverage_html=coverage_html,
            recommendations_html=recommendations_html,
            raw_json=json.dumps(self.report_data, indent=2)
        )
        
        with open(output_file, 'w') as f:
            f.write(html_content)
    
    def generate_report(
        self, 
        pytest_xml: Optional[Path] = None,
        coverage_xml: Optional[Path] = None,
        test_json: Optional[Path] = None,
        output_html: Optional[Path] = None,
        output_json: Optional[Path] = None
    ) -> None:
        """Generate comprehensive test report."""
        
        # Parse available data sources
        if pytest_xml:
            self.report_data["test_results"]["pytest"] = self.parse_pytest_xml(pytest_xml)
        
        if coverage_xml:
            self.report_data["coverage"] = self.parse_coverage_xml(coverage_xml)
        
        if test_json:
            test_json_data = self.parse_test_results_json(test_json)
            if test_json_data:
                self.report_data["test_results"].update(test_json_data.get("results", {}))
        
        # Analyze performance data
        self.report_data["performance"] = self.analyze_performance_data()
        
        # Generate summary
        self.report_data["summary"] = self.generate_summary()
        
        # Output reports
        if output_json:
            with open(output_json, 'w') as f:
                json.dump(self.report_data, f, indent=2)
            print(f"📄 JSON report written to {output_json}")
        
        if output_html:
            self.generate_html_report(output_html)
            print(f"🌐 HTML report written to {output_html}")
        
        # Print summary to console
        self.print_console_summary()
    
    def print_console_summary(self) -> None:
        """Print summary to console."""
        summary = self.report_data["summary"]
        
        print("\n📊 Test Report Summary")
        print("=" * 50)
        
        print(f"Overall Status: {summary.get('overall_status', 'unknown').upper()}")
        
        if "metrics" in summary:
            print(f"Total Tests: {summary['metrics'].get('total_tests', 'N/A')}")
            print(f"Pass Rate: {summary['metrics'].get('pass_rate', 0):.1f}%")
            print(f"Line Coverage: {summary['metrics'].get('line_coverage', 0):.1f}%")
            print(f"Branch Coverage: {summary['metrics'].get('branch_coverage', 0):.1f}%")
        
        if summary.get("recommendations"):
            print("\n⚠️  Recommendations:")
            for rec in summary["recommendations"]:
                print(f"  - {rec}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate comprehensive test report")
    
    parser.add_argument("--pytest-xml", type=Path, help="Path to pytest XML results")
    parser.add_argument("--coverage-xml", type=Path, help="Path to coverage XML report")
    parser.add_argument("--test-json", type=Path, help="Path to test results JSON")
    parser.add_argument("--output-html", type=Path, help="Output HTML report path")
    parser.add_argument("--output-json", type=Path, help="Output JSON report path")
    parser.add_argument("--auto-discover", action="store_true", 
                       help="Auto-discover report files in standard locations")
    
    args = parser.parse_args()
    
    root_dir = Path(__file__).parent.parent
    generator = TestReportGenerator(root_dir)
    
    # Auto-discover files if requested
    if args.auto_discover:
        if not args.pytest_xml:
            pytest_xml = root_dir / "pytest-results.xml"
            if pytest_xml.exists():
                args.pytest_xml = pytest_xml
        
        if not args.coverage_xml:
            coverage_xml = root_dir / "coverage.xml"
            if coverage_xml.exists():
                args.coverage_xml = coverage_xml
        
        if not args.test_json:
            test_json = root_dir / "test_results.json"
            if test_json.exists():
                args.test_json = test_json
        
        if not args.output_html:
            args.output_html = root_dir / "test_report.html"
        
        if not args.output_json:
            args.output_json = root_dir / "test_report.json"
    
    generator.generate_report(
        pytest_xml=args.pytest_xml,
        coverage_xml=args.coverage_xml,
        test_json=args.test_json,
        output_html=args.output_html,
        output_json=args.output_json
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())