from langchain.tools import tool
import os
import subprocess
import platform

@tool("create_file_open_tool")
def create_file_open_tool(folder_path: str, file_name: str, content: str, extension: str) -> str:
    """
    在指定的文件夹中，创建文件，并写入内容，修改后缀名;
    params 参数:
        folder_path: 文件夹的路径，存放文件的完整路径;
        file_name: 文件名称 (不包含后缀名);
        content: 要写入的文件内容;
        extension: 文件名的后缀 (只需要文件后缀名，不包括 . )，比如: html、py、mp3、pdf、word等
    """
    # 构建写入文件的完整路径
    file_path = os.path.join(folder_path, f"{file_name}.{extension}")
    try:
        # 检测文件夹是否存在
        if not os.path.exists(folder_path):
            return f"文件夹不存在-{folder_path}"
        
        # 判断文件是否存在 (修复了教程图片中的 file_name 的 bug)
        if os.path.exists(file_path):
            return f"文件已存在-{file_name}"
            
        # 文件不存在，就创建文件，写入内容
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        # 根据操作系统打开文件
        if platform.system() == "Windows":
            # 使用记事本打开
            subprocess.Popen(["notepad", file_path])
        else:
            subprocess.Popen(["open", file_path])
            
        return f"文件创建成功: {file_path} 内容写入成功！"
    except Exception as e:
        return f"文件创建失败: {str(e)}"
