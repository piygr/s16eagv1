from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON
from agentLoop.contextManager import ExecutionContextManager

class OutputAnalyzer:
    def __init__(self, context: ExecutionContextManager):
        """Work directly with NetworkX graph - no intermediate processing"""
        self.context = context
        self.graph = context.plan_graph
        self.console = Console()
    
    def show_results(self):
        """Display comprehensive results analysis directly from NetworkX graph"""
        
        # Get data directly from graph
        summary = self.context.get_execution_summary()
        
        # 1. Execution Overview
        self.console.print(Panel(
            f"✅ Completed: {summary['completed_steps']}/{summary['total_steps']} steps\n"
            f"💰 Total Cost: ${summary['total_cost']:.2f} ({summary['total_input_tokens']}/{summary['total_output_tokens']})\n"
            f"❌ Failures: {summary['failed_steps']}",
            title="📊 Execution Summary",
            border_style="green"
        ))
        
        # 2. Raw Agent Outputs (from individual nodes)
        self.console.print("\n🔍 **Raw Agent Outputs (from graph nodes):**")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Step")
        table.add_column("Agent")
        table.add_column("Status")
        table.add_column("Raw Output Keys")
        
        for node_id in self.graph.nodes:
            if node_id == "ROOT":
                continue
            node_data = self.graph.nodes[node_id]
            if node_data.get('output'):
                output = node_data['output']
                if isinstance(output, dict):
                    if 'output' in output and isinstance(output['output'], dict):
                        keys = list(output['output'].keys())
                    else:
                        keys = list(output.keys())
                else:
                    keys = ['raw_text']
                
                status = node_data['status']
                if status == 'completed':
                    status = f"[green]✅ {status}[/green]"
                elif status == 'failed':
                    status = f"[red]❌ {status}[/red]"
                
                table.add_row(
                    node_id,
                    node_data.get('agent', 'Unknown'),
                    status,
                    str(keys)
                )
        
        self.console.print(table)
        
        # 3. Session Info directly from graph
        self.console.print(f"\n📋 **Session:** {self.graph.graph['session_id']}")
        self.console.print(f"🕐 **Created:** {self.graph.graph['created_at']}")
        self.console.print(f"📁 **Session File:** memory/session_summaries_index/{self.graph.graph['created_at'][:10].replace('-', '/')}/session_{self.graph.graph['session_id']}.json")

        # Enhanced cost display
        cost_breakdown = summary.get("cost_breakdown", {})
        if cost_breakdown:
            self.console.print(f"\n💰 **Cost Breakdown:**")
            for step, data in cost_breakdown.items():
                cost = data["cost"]
                input_tokens = data["input_tokens"]
                output_tokens = data["output_tokens"]
                self.console.print(f"   • {step}: ${cost:.6f} ({input_tokens}/{output_tokens})")
            self.console.print(f"   **Total: ${summary['total_cost']:.6f}**")
        else:
            self.console.print(f"💰 Total Cost: ${summary['total_cost']:.4f}")

def get_meaningful_keys(output):
    """Filter internal keys"""
    if not isinstance(output, dict):
        return []
    
    skip_keys = {'cost', 'input_tokens', 'output_tokens', 'total_tokens', 'execution_result', 'execution_status', 'execution_error', 'execution_time', 'executed_variant'}
    return [k for k in output.keys() if k not in skip_keys]

# Usage in main.py
def analyze_results(context: ExecutionContextManager):
    """Analyze results directly from NetworkX graph"""
    analyzer = OutputAnalyzer(context)
    analyzer.show_results()

# Update the display function
def display_raw_outputs(summary):
    """Display raw agent outputs with filtered keys"""
    # ... existing code ...
    
    for step_id, step_data in summary["step_outputs"].items():
        if step_data.get('output'):
            meaningful_keys = get_meaningful_keys(step_data['output'])
            table.add_row(
                step_id,
                step_data.get('agent', 'Unknown'),
                "✅ completed" if step_data.get('status') == 'completed' else "❌ failed",
                str(meaningful_keys)
            )
