from langchain.tools import tool
import os
import sys
import subprocess

@tool("create_dir_open_tool")
def create_dir_open_tool(disk: str, name: str) -> str:
    """
    创建文件夹，并且打开（支持多层嵌套）
    disk: 盘符，比如 D盘
    name: 文件夹名称，比如: workspace\\demo文件夹
    """
    # 根据不同的操作系统，构建不同的路径
    if sys.platform == "win32":
        # 修复截图代码的Bug：大模型可能传入 "C" 或 "C盘"，需要清洗并加上冒号
        disk_letter = disk.replace("盘", "").strip()
        if not disk_letter.endswith(":"):
            disk_letter = f"{disk_letter}:"
            
        # 拼接绝对路径，例如 C:\workspace\demo
        dir_path = f"{disk_letter}\\{name}" # 构建的路径
        open_path = f"{dir_path}"
    else:
        # /User/用户名/workspace/demo
        dir_path = f"{disk}/{name}"
        open_path = f"{dir_path}"
    try:
        # 判断文件是否存在
        if os.path.exists(dir_path):
            return f"路径已存在: {dir_path}"
        # 不存在就创建文件夹
        os.makedirs(dir_path, exist_ok=True)
        # 根据不同的操作系统，打开文件夹
        if sys.platform == "win32":
            subprocess.Popen(["explorer", open_path])
        else:
            subprocess.Popen(["open", open_path])
        return f"文件夹创建成功: {open_path}"
    except Exception as e:
        return f"权限不足，创建失败: {dir_path}"
