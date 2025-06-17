#!/usr/bin/env python3
"""
Comprehensive Testing Harness for AI Clone

This script runs a comprehensive set of tests for both text messages and emails,
analyzes the results, and provides recommendations for improving the AI clone's performance.
"""

import os
import json
import sys
import argparse
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import test modules
from test_text_messages import run_text_message_tests, analyze_test_results
from test_email_responses import run_email_tests, analyze_email_test_results

def ensure_output_directory():
    """Ensure the output directory exists"""
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_results')
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def plot_results(text_analysis, email_analysis, output_dir):
    """
    Generate plots to visualize test results
    
    Args:
        text_analysis: Analysis results for text messages
        email_analysis: Analysis results for emails
        output_dir: Directory to save plots
    """
    # Create figure for response times
    plt.figure(figsize=(12, 6))
    
    # Text message response times by category
    categories = []
    times = []
    for category, data in text_analysis["category_analysis"].items():
        categories.append(category)
        times.append(data["avg_response_time"])
    
    x = np.arange(len(categories))
    width = 0.35
    
    plt.bar(x - width/2, times, width, label='Text Messages')
    
    # Email response times by category
    email_categories = []
    email_times = []
    for category, data in email_analysis["category_analysis"].items():
        email_categories.append(category)
        email_times.append(data["avg_response_time"])
    
    # Only plot email categories that match text categories
    matching_email_times = []
    for cat in categories:
        if cat in email_analysis["category_analysis"]:
            matching_email_times.append(email_analysis["category_analysis"][cat]["avg_response_time"])
        else:
            matching_email_times.append(0)
    
    plt.bar(x + width/2, matching_email_times, width, label='Emails')
    
    plt.xlabel('Category')
    plt.ylabel('Average Response Time (s)')
    plt.title('Response Times by Category and Channel')
    plt.xticks(x, categories, rotation=45, ha='right')
    plt.legend()
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(os.path.join(output_dir, 'response_times.png'))
    
    # Create figure for email success metrics
    plt.figure(figsize=(12, 6))
    
    email_cats = []
    greeting_rates = []
    signoff_rates = []
    
    for category, data in email_analysis["category_analysis"].items():
        email_cats.append(category)
        greeting_rates.append(data["greeting_success_rate"] * 100)
        signoff_rates.append(data["sign_off_success_rate"] * 100)
    
    x = np.arange(len(email_cats))
    width = 0.35
    
    plt.bar(x - width/2, greeting_rates, width, label='Greeting Success')
    plt.bar(x + width/2, signoff_rates, width, label='Sign-off Success')
    
    plt.xlabel('Email Category')
    plt.ylabel('Success Rate (%)')
    plt.title('Email Formatting Success Rates by Category')
    plt.xticks(x, email_cats, rotation=45, ha='right')
    plt.legend()
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(os.path.join(output_dir, 'email_success_rates.png'))

def generate_recommendations(text_analysis, email_analysis):
    """
    Generate recommendations for improving the AI clone
    
    Args:
        text_analysis: Analysis results for text messages
        email_analysis: Analysis results for emails
        
    Returns:
        dict: Recommendations
    """
    recommendations = {
        "text_messages": [],
        "emails": [],
        "general": []
    }
    
    # Text message recommendations
    for area in text_analysis.get("improvement_areas", []):
        if area["area"] == "response_time":
            recommendations["text_messages"].append({
                "priority": "medium",
                "issue": "Slow response times",
                "recommendation": "Optimize RAG retrieval for faster responses by reducing the number of examples retrieved or implementing caching for common queries."
            })
        elif area["area"] == "response_completeness":
            recommendations["text_messages"].append({
                "priority": "high",
                "issue": "Incomplete or too short responses",
                "recommendation": "Adjust the channel-specific instructions to ensure text responses are complete while still maintaining the casual style."
            })
    
    # Email recommendations
    for area in email_analysis.get("improvement_areas", []):
        if area["area"] == "email_greeting":
            recommendations["emails"].append({
                "priority": "high",
                "issue": "Missing email greetings",
                "recommendation": "Enhance the email channel processor to always include appropriate greetings based on the formality of the incoming email."
            })
        elif area["area"] == "email_sign_off":
            recommendations["emails"].append({
                "priority": "high",
                "issue": "Missing email sign-offs",
                "recommendation": "Modify the format_response_for_channel method to ensure all email responses include appropriate sign-offs."
            })
        elif area["area"] == "email_completeness":
            recommendations["emails"].append({
                "priority": "high",
                "issue": "Incomplete email responses",
                "recommendation": "Adjust the system prompt for emails to emphasize the importance of addressing all points in the original email."
            })
    
    # General recommendations
    avg_text_time = text_analysis["avg_response_time"]
    avg_email_time = email_analysis["avg_response_time"]
    
    if avg_text_time > 2.0 or avg_email_time > 3.0:
        recommendations["general"].append({
            "priority": "medium",
            "issue": "Overall response times are high",
            "recommendation": "Consider implementing a caching mechanism for common queries and optimizing the RAG retrieval process."
        })
    
    # Check if we have enough recommendations
    if len(recommendations["text_messages"]) == 0:
        recommendations["text_messages"].append({
            "priority": "low",
            "issue": "General text message improvements",
            "recommendation": "Consider adding more diverse text message examples to the RAG database to improve response variety."
        })
    
    if len(recommendations["emails"]) == 0:
        recommendations["emails"].append({
            "priority": "low",
            "issue": "General email improvements",
            "recommendation": "Add more professional email examples to the training data to improve the formality and structure of email responses."
        })
    
    return recommendations

def save_recommendations(recommendations, output_dir):
    """
    Save recommendations to a file
    
    Args:
        recommendations: Recommendations dict
        output_dir: Directory to save the file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    recommendations_file = os.path.join(output_dir, f'recommendations_{timestamp}.json')
    
    with open(recommendations_file, 'w') as f:
        json.dump(recommendations, f, indent=2)
    
    print(f"Recommendations saved to {recommendations_file}")
    return recommendations_file

def generate_html_report(text_results, email_results, text_analysis, email_analysis, recommendations, output_dir):
    """
    Generate an HTML report of test results and recommendations
    
    Args:
        text_results: Text message test results
        email_results: Email test results
        text_analysis: Text message analysis
        email_analysis: Email analysis
        recommendations: Recommendations
        output_dir: Directory to save the report
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(output_dir, f'test_report_{timestamp}.html')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Clone Test Report - {datetime.now().strftime("%Y-%m-%d")}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3 {{ color: #333; }}
            .section {{ margin-bottom: 30px; }}
            .high {{ color: #d9534f; }}
            .medium {{ color: #f0ad4e; }}
            .low {{ color: #5bc0de; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .chart {{ margin: 20px 0; }}
        </style>
    </head>
    <body>
        <h1>AI Clone Test Report</h1>
        <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        
        <div class="section">
            <h2>Summary</h2>
            <p>This report presents the results of comprehensive testing of the AI clone's ability to respond to text messages and emails.</p>
            <ul>
                <li>Text Message Tests: {text_analysis["total_tests"]}</li>
                <li>Email Tests: {email_analysis["total_tests"]}</li>
                <li>Average Text Response Time: {text_analysis["avg_response_time"]:.2f} seconds</li>
                <li>Average Email Response Time: {email_analysis["avg_response_time"]:.2f} seconds</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>Text Message Results</h2>
            <h3>Category Analysis</h3>
            <table>
                <tr>
                    <th>Category</th>
                    <th>Tests</th>
                    <th>Avg. Response Time (s)</th>
                </tr>
    """
    
    for category, data in text_analysis["category_analysis"].items():
        html += f"""
                <tr>
                    <td>{category}</td>
                    <td>{data["num_tests"]}</td>
                    <td>{data["avg_response_time"]:.2f}</td>
                </tr>
        """
    
    html += """
            </table>
            
            <h3>Sample Responses</h3>
            <table>
                <tr>
                    <th>Category</th>
                    <th>Question</th>
                    <th>Response</th>
                </tr>
    """
    
    for result in text_results["results"][:5]:  # Show first 5 results
        html += f"""
                <tr>
                    <td>{result["category"]}</td>
                    <td>{result["question"]}</td>
                    <td>{result["response"]}</td>
                </tr>
        """
    
    html += """
            </table>
        </div>
        
        <div class="section">
            <h2>Email Results</h2>
            <h3>Category Analysis</h3>
            <table>
                <tr>
                    <th>Category</th>
                    <th>Tests</th>
                    <th>Avg. Response Time (s)</th>
                    <th>Greeting Success</th>
                    <th>Sign-off Success</th>
                </tr>
    """
    
    for category, data in email_analysis["category_analysis"].items():
        html += f"""
                <tr>
                    <td>{category}</td>
                    <td>{data["num_tests"]}</td>
                    <td>{data["avg_response_time"]:.2f}</td>
                    <td>{data["greeting_success_rate"]*100:.1f}%</td>
                    <td>{data["sign_off_success_rate"]*100:.1f}%</td>
                </tr>
        """
    
    html += """
            </table>
            
            <h3>Sample Responses</h3>
            <table>
                <tr>
                    <th>Category</th>
                    <th>Subject</th>
                    <th>Response</th>
                </tr>
    """
    
    for result in email_results["results"][:5]:  # Show first 5 results
        html += f"""
                <tr>
                    <td>{result["category"]}</td>
                    <td>{result["subject"]}</td>
                    <td>{result["response"].replace("\n", "<br>")}</td>
                </tr>
        """
    
    html += """
            </table>
        </div>
        
        <div class="section">
            <h2>Charts</h2>
            <div class="chart">
                <h3>Response Times by Category</h3>
                <img src="response_times.png" alt="Response Times Chart" width="800">
            </div>
            <div class="chart">
                <h3>Email Success Rates</h3>
                <img src="email_success_rates.png" alt="Email Success Rates Chart" width="800">
            </div>
        </div>
        
        <div class="section">
            <h2>Recommendations</h2>
            <h3>Text Message Improvements</h3>
            <table>
                <tr>
                    <th>Priority</th>
                    <th>Issue</th>
                    <th>Recommendation</th>
                </tr>
    """
    
    for rec in recommendations["text_messages"]:
        html += f"""
                <tr>
                    <td class="{rec["priority"]}">{rec["priority"].upper()}</td>
                    <td>{rec["issue"]}</td>
                    <td>{rec["recommendation"]}</td>
                </tr>
        """
    
    html += """
            </table>
            
            <h3>Email Improvements</h3>
            <table>
                <tr>
                    <th>Priority</th>
                    <th>Issue</th>
                    <th>Recommendation</th>
                </tr>
    """
    
    for rec in recommendations["emails"]:
        html += f"""
                <tr>
                    <td class="{rec["priority"]}">{rec["priority"].upper()}</td>
                    <td>{rec["issue"]}</td>
                    <td>{rec["recommendation"]}</td>
                </tr>
        """
    
    html += """
            </table>
            
            <h3>General Improvements</h3>
            <table>
                <tr>
                    <th>Priority</th>
                    <th>Issue</th>
                    <th>Recommendation</th>
                </tr>
    """
    
    for rec in recommendations["general"]:
        html += f"""
                <tr>
                    <td class="{rec["priority"]}">{rec["priority"].upper()}</td>
                    <td>{rec["issue"]}</td>
                    <td>{rec["recommendation"]}</td>
                </tr>
        """
    
    html += """
            </table>
        </div>
    </body>
    </html>
    """
    
    with open(report_file, 'w') as f:
        f.write(html)
    
    print(f"HTML report saved to {report_file}")
    return report_file

def run_comprehensive_tests(text_categories=None, email_categories=None, num_per_category=2):
    """
    Run comprehensive tests for both text messages and emails
    
    Args:
        text_categories: Categories to test for text messages (None for all)
        email_categories: Categories to test for emails (None for all)
        num_per_category: Number of tests per category
        
    Returns:
        tuple: (text_results, email_results, text_analysis, email_analysis, recommendations)
    """
    print("=== Starting Comprehensive AI Clone Testing ===")
    
    # Ensure output directory exists
    output_dir = ensure_output_directory()
    
    # Run text message tests
    print("\n=== Running Text Message Tests ===")
    text_results = run_text_message_tests(categories=text_categories, num_per_category=num_per_category)
    text_results_file = os.path.join(output_dir, 'text_results.json')
    with open(text_results_file, 'w') as f:
        json.dump(text_results, f, indent=2)
    
    # Run email tests
    print("\n=== Running Email Tests ===")
    email_results = run_email_tests(categories=email_categories, num_per_category=num_per_category)
    email_results_file = os.path.join(output_dir, 'email_results.json')
    with open(email_results_file, 'w') as f:
        json.dump(email_results, f, indent=2)
    
    # Analyze results
    print("\n=== Analyzing Results ===")
    text_analysis = analyze_test_results(text_results_file)
    email_analysis = analyze_email_test_results(email_results_file)
    
    # Generate recommendations
    print("\n=== Generating Recommendations ===")
    recommendations = generate_recommendations(text_analysis, email_analysis)
    recommendations_file = save_recommendations(recommendations, output_dir)
    
    # Plot results
    print("\n=== Generating Visualizations ===")
    plot_results(text_analysis, email_analysis, output_dir)
    
    # Generate HTML report
    print("\n=== Generating HTML Report ===")
    report_file = generate_html_report(text_results, email_results, text_analysis, email_analysis, recommendations, output_dir)
    
    print(f"\n=== Testing Complete! ===")
    print(f"HTML Report: {report_file}")
    
    return text_results, email_results, text_analysis, email_analysis, recommendations

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run comprehensive tests for the AI clone')
    parser.add_argument('--text-only', action='store_true', help='Run only text message tests')
    parser.add_argument('--email-only', action='store_true', help='Run only email tests')
    parser.add_argument('--num-tests', type=int, default=2, help='Number of tests per category')
    args = parser.parse_args()
    
    if args.text_only:
        print("=== Running Text Message Tests Only ===")
        text_results = run_text_message_tests(num_per_category=args.num_tests)
    elif args.email_only:
        print("=== Running Email Tests Only ===")
        email_results = run_email_tests(num_per_category=args.num_tests)
    else:
        run_comprehensive_tests(num_per_category=args.num_tests)
