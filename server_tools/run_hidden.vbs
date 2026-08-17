Set WshShell = CreateObject("WScript.Shell")
' Lấy thư mục hiện tại của file vbs
strPath = Wscript.ScriptFullName
Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objFile = objFSO.GetFile(strPath)
strFolder = objFSO.GetParentFolderName(objFile)

' Chạy file start_server.bat ở chế độ ẩn (số 0 = Hidden window)
WshShell.Run chr(34) & strFolder & "\start_server.bat" & chr(34), 0
Set WshShell = Nothing
