from langchain.tools import tool
import subprocess
import os

@tool("office_cli_tool")
def office_cli_tool(command: str) -> str:
    """
    执行 officecli 命令行工具以创建或编辑 Word/Excel 等 Office 文件。
    参数 command 必须是完整的 officecli 执行命令字符串。
    """
    try:
        # 针对 IDE 环境变量可能未及时刷新的问题，手动将 officecli 的全局安装路径加入执行环境
        env = os.environ.copy()
        officecli_path = r"C:\Users\Elysi\AppData\Local\OfficeCLI"
        if officecli_path not in env.get("PATH", ""):
            env["PATH"] = officecli_path + os.pathsep + env.get("PATH", "")

        # 使用 shell=True 允许执行终端命令
        result = subprocess.run(command, shell=True, capture_output=True, text=True, env=env)
        if result.returncode == 0:
            return f"Office命令执行成功:\n{result.stdout}"
        else:
            return f"Office命令执行失败:\n{result.stderr}"
    except Exception as e:
        return f"命令行工具调用异常: {str(e)}"
