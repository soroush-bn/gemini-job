import os
from config import TRACKER_FILE_PATH
from utils.messenger import pipeline_messenger

def log_token_usage(node_name: str, usage_metadata: dict, model_type: str = "flash-lite"):
    """Logs token usage and estimated cost for a specific agent node to tracker/token_log.md."""
    tracker_dir = os.path.dirname(TRACKER_FILE_PATH)
    log_file = os.path.join(tracker_dir, "token_log.md")
    
    # Ensure directory exists
    os.makedirs(tracker_dir, exist_ok=True)
    
    prompt_tokens = usage_metadata.get('prompt_token_count', 0)
    candidates_tokens = usage_metadata.get('candidates_token_count', 0)
    total_tokens = usage_metadata.get('total_token_count', 0)
    
    # Pricing (Paid Tier USD per 1M tokens)
    if "pro" in model_type.lower():
        input_price = 1.25
        output_price = 10.00
    else: # Default to flash-lite
        input_price = 0.10
        output_price = 0.40
        
    # CAD Conversion Rate (Assumed 1 USD = 1.40 CAD)
    usd_to_cad = 1.40
    input_cost_usd = (prompt_tokens / 1_000_000) * input_price
    output_cost_usd = (candidates_tokens / 1_000_000) * output_price
    total_cost_cad = (input_cost_usd + output_cost_usd) * usd_to_cad
    
    # Broadcast to GUI
    pipeline_messenger.send("metrics", {
        "node": f"{node_name} ({model_type})",
        "total_tokens": total_tokens,
        "cost_cad": total_cost_cad
    })
    
    headers = "| Node | Model | Prompt Tokens | Response Tokens | Total Tokens | Cost (CAD) |\n"
    separator = "| --- | --- | --- | --- | --- | --- |\n"
    new_row = f"| {node_name} | {model_type} | {prompt_tokens} | {candidates_tokens} | {total_tokens} | ${total_cost_cad:.6f} |\n"
    
    file_exists = os.path.exists(log_file)
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            if not file_exists:
                f.write("# Token Usage and Cost Log\n\n")
                f.write("**Pricing (USD per 1M tokens):**\n")
                f.write("- **Pro:** Input $1.25, Output $10.00\n")
                f.write("- **Flash-Lite:** Input $0.10, Output $0.40\n")
                f.write(f"\n**FX Rate:** {usd_to_cad} CAD/USD\n\n")
                f.write(headers)
                f.write(separator)
            f.write(new_row)
        return f"Logged tokens and cost for {node_name}."
    except Exception as e:
        return f"Error logging tokens: {str(e)}"
