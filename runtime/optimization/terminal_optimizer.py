def summarize_terminal(stdout: str, stderr: str = "", kind: str = "command") -> dict:
    lines=[line for line in stdout.splitlines() if line.strip()]; errors=[line for line in stderr.splitlines() if line.strip()]
    return {"kind":kind,"stdout_lines":len(lines),"stderr_lines":len(errors),"stdout":lines[-20:],"stderr":errors[-20:]}
