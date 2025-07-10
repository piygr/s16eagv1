import uuid
from utils.utils import log_step, log_error
from action.executor import run_user_code
from agent.agentSession import ExecutionSnapshot
from concurrent.futures import ThreadPoolExecutor
import asyncio

executor = ThreadPoolExecutor(max_workers=3)  # Limit to 3 variants

async def execute_step(step_id, code, ctx, session, multi_mcp, variant_used: str = ""):
    result = None
    try:
        result = await run_user_code(code, multi_mcp, ctx.session_id)

        if session:
            session.add_execution_snapshot(
                ExecutionSnapshot(
                    run_id=str(uuid.uuid4()),
                    step_id=step_id,
                    variant_used=variant_used,
                    code=code,
                    status=result.get("status", "error"),
                    result=result.get("result"),
                    error=result.get("error"),
                    execution_time=result.get("execution_time", ""),
                    total_time=result.get("total_time", ""),
                )
            )
    except Exception as e:
        result = {"status": "error", "error": str(e)}

    if result.get("status") == "success":
        ctx.update_step_result(step_id, result["result"])
        ctx.mark_step_completed(step_id)
    else:
        ctx.mark_step_failed(step_id, result.get("error", "Unknown error"))

    return result


def run_step_in_thread(step_id, code, ctx, session, multi_mcp, variant):
    return asyncio.run(execute_step(step_id, code, ctx, session, multi_mcp, variant_used=variant))

async def execute_step_with_mode(step_id, code_variants, ctx, mode, session, multi_mcp):
    if mode == "parallel":
        loop = asyncio.get_event_loop()
        tasks = []
        variant_map = []

        for suffix in ["A", "B", "C"]:
            variant = f"CODE_{step_id}{suffix}"
            if variant in code_variants:
                code = code_variants[variant]
                variant_map.append(variant)
                tasks.append(
                    loop.run_in_executor(
                        executor,
                        run_step_in_thread,
                        step_id, code, ctx, session, multi_mcp, variant
                    )
                )

        if not tasks:
            return {"status": "error", "error": "No valid variants to run."}

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_results = []
        for variant, result in zip(variant_map, results):
            if isinstance(result, Exception):
                all_results.append({"status": "error", "error": str(result), "variant": variant})
            else:
                result["variant"] = variant
                all_results.append(result)

        for result in all_results:
            if result.get("status") == "success":
                return {"status": "success", "results": all_results, "result": result["result"]}

        return {"status": "error", "results": all_results, "error": "All variants failed."}

    else:  # fallback mode
        result = None
        for suffix in ["A", "B", "C"]:
            variant = f"CODE_{step_id}{suffix}"
            if variant not in code_variants:
                continue
            code = code_variants[variant]
            try:
                result = await execute_step(step_id, code, ctx, session, multi_mcp, variant_used=variant)
                if result.get("status") == "success":
                    log_step(f"✅ Variant {variant} succeeded.", symbol="✅")
                    return result
                else:
                    log_error(f"❌ Variant {variant} failed: {result.get('error')}")
            except Exception as e:
                log_error(f"❌ Exception in variant {variant}: {e}")

        log_error(f"❌ All variants failed during fallback execution for step {step_id}")
        if result and result.get("status") == "error":
            log_error(f"↳ Error: {result.get('error')}")

        return {"status": "error", "error": "All fallback variants failed."}
