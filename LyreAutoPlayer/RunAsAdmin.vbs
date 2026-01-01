' 以管理员身份运行 LyreAutoPlayer
' 双击此文件即可

Set objShell = CreateObject("Shell.Application")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' 获取脚本所在目录
strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' 构建 Python 路径
strPython = strPath & "\.venv\Scripts\python.exe"
strMain = strPath & "\main.py"

' 以管理员身份运行
objShell.ShellExecute strPython, """" & strMain & """", strPath, "runas", 1
