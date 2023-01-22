from pywinauto.application import Application
import os
import time

def StartToolKit():
    # open ToolKit
    os.chdir(r'C:\Toolkit\Toolkit\Toolkit_EODAS_20220511104037\P')
    os.system(r'"C:\Toolkit\Toolkit\Toolkit_EODAS_20220511104037\P\ExecutorAndTimestampReplacer.exe"')
    # time.sleep(3)
    # open automation
    app = Application(backend="uia").connect(path=r"C:\Toolkit\Toolkit\Toolkit_EODAS_20220511104037\P\AppHost.exe")
    dlg = app.top_window()
    dlg.wait("exists enabled visible ready")
    dlg.set_focus()
    time.sleep(1.5)
    dlg['TabControlProxy Screens'].child_window(title="Proxy Screens", control_type="TabItem").click_input()
    dlg['TabControlProxy Screens'].child_window(title="Proxy Screens", control_type="TabItem")\
                                  .child_window(title="Operational", control_type="Button").click_input()
    time.sleep(1.5)
    dlg.child_window(title="File", control_type="MenuItem").click_input()
    dlg.child_window(title="File", control_type="MenuItem")\
       .child_window(title="Load", control_type="MenuItem").click_input()
    dlg = app.top_window()
    file = r"C:\Users\admin\Documents\setup_10Hz.cmdx"
    dlg.child_window(title="File name:", auto_id="1148", control_type="Edit").set_edit_text(file)
    dlg.child_window(title="Open", auto_id="1", control_type="Button").click_input()
    dlg = app.top_window()
    dlg.wait("exists enabled visible ready")
    time.sleep(3)
    dlg.child_window(title="Apply", control_type="Button").click_input()
    dlg.child_window(title="Refresh", auto_id="RefreshButton", control_type="Button").click_input()
    dlg.window(title="Minimize", control_type="Button").click_input()
    # dlg.window(title="Close", control_type="Button").click_input()
    # dlg.close()
    # dlg.print_control_identifiers()

def StopToolKit():
    os.system("taskkill /f /im  AppHost.exe")
