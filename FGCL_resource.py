import matlab.engine

#----------------------------------------------------------------------------------------------------------------------#
############################# Defines #############################
ENG = matlab.engine.start_matlab()

PATH = r"C:\Users\admin\Documents\Matlab_resources_for_python"
ENG.addpath(PATH)
############################# Defines #############################
#----------------------------------------------------------------------------------------------------------------------#
'''
input: 
output: 
functionality: 
remarks: 
'''
def ConnectFGandCAM():
    vidobjPath = ENG.ConnectFGandCAM()

    return vidobjPath
#----------------------------------------------------------------------------------------------------------------------#
'''
input: 
output: 
functionality: 
remarks: 
'''
def GrabIMG(vidobjPath, enableNUC):
    imgMAT = ENG.GrabIMG(vidobjPath, enableNUC)

    return imgMAT
#----------------------------------------------------------------------------------------------------------------------#
'''
input: 
output: 
functionality: 
remarks: 
'''
def GrabIMGMean(vidobjPath, amount, enableNUC):
    imgMAT = ENG.GrabIMGMean(vidobjPath, amount, enableNUC)

    return imgMAT
#----------------------------------------------------------------------------------------------------------------------#
'''
input: 
output: 
functionality: 
remarks: 
'''
def OpenLiveVideo(vidobjPath):
    ENG.OpenLiveVideo(vidobjPath)
#----------------------------------------------------------------------------------------------------------------------#
'''
input: 
output: 
functionality: 
remarks: 
'''
def CloseLiveVideo(vidobjPath):
    ENG.CloseLiveVideo(vidobjPath)
#----------------------------------------------------------------------------------------------------------------------#
'''
input: 
output: 
functionality: 
remarks: 
'''
def DisconnectFGandCAM(vidobjPath):
    ENG.DisconnectFGandCAM(vidobjPath)
    ENG.quit()
#----------------------------------------------------------------------------------------------------------------------#