# flow.py – 100% NetworkX Graph-First (No agentSession)

import networkx as nx
import asyncio
from agentLoop.contextManager import ExecutionContextManager
from agentLoop.agents import AgentRunner
from utils.utils import log_step, log_error
from agentLoop.model_manager import ModelManager
from agentLoop.visualizer import ExecutionVisualizer
from rich.live import Live
from rich.console import Console
from datetime import datetime

class AgentLoop4:
    def __init__(self, multi_mcp, strategy="conservative"):
        self.multi_mcp = multi_mcp
        self.strategy = strategy
        self.agent_runner = AgentRunner(multi_mcp)

    async def run(self, query, file_manifest, globals_schema, uploaded_files):
        # Phase 1: File Profiling (if files exist)
        file_profiles = {}
        if uploaded_files:
            file_result = await self.agent_runner.run_agent(
                "DistillerAgent",
                {
                    "task": "profile_files",
                    "files": uploaded_files,
                    "instruction": "Profile and summarize each file's structure, columns, content type",
                    "writes": ["file_profiles"]
                }
            )
            if file_result["success"]:
                file_profiles = file_result["output"]

        # Phase 2: Planning with AgentRunner
        plan_result = await self.agent_runner.run_agent(
            "PlannerAgent",
            {
                "original_query": query,
                "planning_strategy": self.strategy,
                "globals_schema": globals_schema,
                "file_manifest": file_manifest,
                "file_profiles": file_profiles
            }
        )

        if not plan_result["success"]:
            raise RuntimeError(f"Planning failed: {plan_result['error']}")

        # Check if plan_graph exists
        if 'plan_graph' not in plan_result['output']:
            raise RuntimeError(f"PlannerAgent output missing 'plan_graph' key. Got: {list(plan_result['output'].keys())}")
        
        plan_graph = plan_result["output"]["plan_graph"]

        try:
            # Phase 3: 100% NetworkX Graph-First Execution
            context = ExecutionContextManager(
                plan_graph,
                session_id=None,
                original_query=query,
                file_manifest=file_manifest
            )
            
            # Add multi_mcp reference
            context.multi_mcp = self.multi_mcp
            
            # Initialize graph with file profiles and globals
            context.set_file_profiles(file_profiles)
            context.plan_graph.graph['globals_schema'].update(globals_schema)

            # Phase 4: Execute DAG with visualization
            await self._execute_dag(context)

            # Phase 5: Return the CONTEXT OBJECT, not summary
            return context

        except Exception as e:
            print(f"❌ ERROR creating ExecutionContextManager: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def _execute_dag(self, context):
        """Execute DAG with visualization - DEBUGGING MODE"""
        
        # Get plan_graph structure for visualization
        plan_graph = {
            "nodes": [
                {"id": node_id, **node_data} 
                for node_id, node_data in context.plan_graph.nodes(data=True)
            ],
            "links": [
                {"source": source, "target": target}
                for source, target in context.plan_graph.edges()
            ]
        }
        
        # Create visualizer
        visualizer = ExecutionVisualizer(plan_graph)
        console = Console()
        
        # 🔧 DEBUGGING MODE: No Live display, just regular prints
        max_iterations = 20
        iteration = 0

        while not context.all_done() and iteration < max_iterations:
            iteration += 1
            
            # Show current state
            console.print(visualizer.get_layout())
            
            # Get ready nodes
            ready_steps = context.get_ready_steps()
            
            if not ready_steps:
                # Check for failures
                has_failures = any(
                    context.plan_graph.nodes[n]['status'] == 'failed' 
                    for n in context.plan_graph.nodes
                )
                if has_failures:
                    break
                await asyncio.sleep(0.3)
                continue

            # Mark running
            for step_id in ready_steps:
                visualizer.mark_running(step_id)
                context.mark_running(step_id)
            
            # ✅ EXECUTE AGENTS FOR REAL
            tasks = [self._execute_step(step_id, context) for step_id in ready_steps]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for step_id, result in zip(ready_steps, results):
                if isinstance(result, Exception):
                    visualizer.mark_failed(step_id, result)
                    context.mark_failed(step_id, str(result))
                elif result["success"]:
                    visualizer.mark_completed(step_id)
                    await context.mark_done(step_id, result["output"])
                else:
                    visualizer.mark_failed(step_id, result["error"])
                    context.mark_failed(step_id, result["error"])

        # Final state
        console.print(visualizer.get_layout())
        
        if context.all_done():
            console.print("🎉 All tasks completed!")

    async def _execute_step(self, step_id, context):
        """Execute a single step with call_self support"""
        step_data = context.get_step_data(step_id)
        agent_type = step_data["agent"]
        
        # Get inputs from NetworkX graph
        inputs = context.get_inputs(step_data.get("reads", []))
        
        # 🔧 HELPER FUNCTION: Build agent input (consistent for both iterations)
        def build_agent_input(instruction=None, previous_output=None, iteration_context=None):
            print(f"\n\n\n inputs: {inputs}\n\n\n")
            if agent_type == "FormatterAgent":
                all_globals = context.plan_graph.graph['globals_schema'].copy()
                return {
                    "step_id": step_id,
                    "agent_prompt": instruction or step_data.get("agent_prompt", step_data["description"]),
                    "reads": step_data.get("reads", []),
                    "writes": step_data.get("writes", []),
                    "inputs": inputs,
                    "all_globals_schema": all_globals,  # ✅ ALWAYS included for FormatterAgent
                    "original_query": context.plan_graph.graph['original_query'],
                    "session_context": {
                        "session_id": context.plan_graph.graph['session_id'],
                        "created_at": context.plan_graph.graph['created_at'],
                        "file_manifest": context.plan_graph.graph['file_manifest']
                    },
                    **({"previous_output": previous_output} if previous_output else {}),
                    **({"iteration_context": iteration_context} if iteration_context else {})
                }
            else:
                return {
                    "step_id": step_id,
                    "agent_prompt": instruction or step_data.get("agent_prompt", step_data["description"]),
                    "reads": step_data.get("reads", []),
                    "writes": step_data.get("writes", []),
                    "inputs": inputs,
                    **({"previous_output": previous_output} if previous_output else {}),
                    **({"iteration_context": iteration_context} if iteration_context else {})
                }

        # Execute first iteration
        agent_input = build_agent_input()
        result = await self.agent_runner.run_agent(agent_type, agent_input)
        
        MAX_CALL_SELF_ITERATIONS = 4

        if result["success"]:
            output = result["output"]
            
            # Check for call_self
            if output.get("call_self"):
                current_iter = 1
                current_output = output
                final_result = result
                next_result = None
                iterations_data = []
                
                while current_output.get("call_self") and current_iter < MAX_CALL_SELF_ITERATIONS:
                    # Handle code execution if needed
                    if context._has_executable_code(current_output):
                        execution_result = await context._auto_execute_code(step_id, current_output)
                        if execution_result.get("status") == "success":
                            execution_data = context._format_executed_result(execution_result) #execution_result.get("result", {})
                            inputs = {**inputs, **execution_data}  # Update inputs for iteration 2
                    
                    # 💾 CRITICAL: Store iteration data in session
                    iterations_data.append(
                        {"iteration": current_iter, "output": current_output}
                    )

                    current_iter += 1
                    
                    # Execute second iteration with consistent input structure
                    next_agent_input = build_agent_input(
                        instruction=current_output.get("next_instruction", "Continue the task"),
                        previous_output=current_output,
                        iteration_context=current_output.get("iteration_context", {})
                    )
                    
                    next_result = await self.agent_runner.run_agent(agent_type, next_agent_input)
                    
                    if next_result["success"]:
                        final_result = next_result
                        current_output = next_result["output"]
                        if current_iter == MAX_CALL_SELF_ITERATIONS:
                            iterations_data.append({"iteration": current_iter, "output": current_output})
                            break   
                    else:
                        break
                    
                # Store iterations in the node data for session persistence
                step_data = context.get_step_data(step_id)
                step_data['iterations'] = iterations_data
                step_data['call_self_used'] = True
                step_data['final_iteration_output'] = final_result["output"]
                
                return final_result
                
            else:
                return result
        else:
            return result

    async def _handle_failures(self, context):
        """Handle failures via mid-session replanning"""
        # TODO: Implement mid-session replanning with PlannerAgent
        log_error("Mid-session replanning not yet implemented")
