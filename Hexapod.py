import numpy as np
from pipython import GCSDevice, pitools

#----------------------------------------------------------------------------------------------------------------------#
############################# Defines #############################
__signature__ = 0x5ee8a396c01e7eb320cad702522494ab

CONTROLLERNAME = 'C-887'
STAGES = None
REFMODES = 'FRF'

XYlimit = 2 #  mm
Zlimit = 2 #  mm
UVWlimit = 5 # deg

HEXAPODBASE = 19.02799  # mm
# PIVOTOFFSET = 184.6 - 43.78 # mm
# PIVOTOFFSET = 140.819 + HEXAPODBASE  # mm  # from top of hexapod base to iris
PIVOTOFFSET = 146.91409 + HEXAPODBASE  # mm  # from top of fpa top plane

startVector = [0., 0., 0., 0., 0., 0.]
############################# Defines #############################
#----------------------------------------------------------------------------------------------------------------------#
'''
input: N/A
output: a PI object of the controller and a string address like variable for communication 
functionality: connects the hexapod with the python interface
               references the hexapod to the X axis
               defines a new coordinate system and moves the center pivot point of the hexapod to there
               moves the hexapod to the 0^6 vector in the new coordinate system 
remarks: prints some massages for the user to keep track of the initialization process 
'''
def ConnectAndConfigure():
    with GCSDevice(CONTROLLERNAME) as pidevice:
        print('search for controllers...')
        devices = pidevice.EnumerateTCPIPDevices()
        address = devices[0]
        pidevice.ConnectTCPIPByDescription(address)
        print('Connected: {}'.format(pidevice.qIDN().strip()))
        print('\nInitializing Hexapod...\n')
        pitools.startup(pidevice, stages = STAGES, refmodes = REFMODES)

        pidevice.FRF('X')
        while not pidevice.IsControllerReady():
            pass
        print('Referencing completed for all axes:', end=' ')
        print(dict(pidevice.qFRF(pidevice.axes)))
        try:
            pidevice.KSD('MWS_Calib', 'Z', PIVOTOFFSET)
        except:
            DisconnectAndReset(pidevice)
            ConnectAndConfigure()
        pidevice.KEN('MWS_Calib')
        print('Coordinate system was brought to MWS_Calib.')

        # moving hexapod to 0^6 location
        pidevice.MOV(pidevice.axes, startVector)
        pitools.waitontarget(pidevice)
        print('\nHexapod connected and operational.\n')

        return pidevice, address
#----------------------------------------------------------------------------------------------------------------------#
'''
input: a PI object of the controller and a numpy array that represents the 6-axes target vector in the MWS_Calib coordinate system
output: N/A 
functionality: first we check if the target is in the limitations set above
               if target is valid - the hexapod will move to the specified target location 
               if target is invalid - halt program completely to avoid damage and requests the assist of the system engineer 
remarks: N/A
'''
def MoveAbsolute(pidevice, target):
    if target[2] == -5:  # only in initial movement to place the optical bench (Z=-5)
        pidevice.MOV(pidevice.axes, list(target))
        pitools.waitontarget(pidevice)
    elif (np.amax(np.abs(target[0:1])) < XYlimit) and (np.amax(np.abs(target[2])) < Zlimit) and (np.amax(np.abs(target[3:5])) < UVWlimit):
        pidevice.MOV(pidevice.axes, list(target))
        pitools.waitontarget(pidevice)
    else:
        raise Exception("Call a system engineer - Hexapod reached its maximal range.")
#----------------------------------------------------------------------------------------------------------------------#
'''
input: a PI object of the controller and a numpy array that represents the 6-axes deltas vector in the MWS_Calib coordinate system
output: N/A 
functionality: first we check if the final position after doing the step is in the limitations set above
               if step is valid - the hexapod will move to the specified step to the new location 
               if step is invalid - halt program completely to avoid damage and requests the assist of the system engineer 
remarks: this function uses the assist of the auxiliry function "ConvertPositionToArray" to extract the location from 
         the dictinary that the hexapod returns and converts it to a numpy array 
'''
def MoveRelative(pidevice, step):
    curPos = ConvertPositionToArray(pidevice.qPOS())
    target = curPos + step
    if (np.amax(np.abs(target[0:1])) < XYlimit) and (np.amax(np.abs(target[2])) < Zlimit) and (np.amax(np.abs(target[3:5])) < UVWlimit):
        pidevice.MVR(pidevice.axes, list(target))
        pitools.waitontarget(pidevice)
    else:
        raise Exception("Call an engineer - Hexapod reached its maximal range.")
#----------------------------------------------------------------------------------------------------------------------#
'''
input: an ordered dictinary of location of the hexapod which has all the 6 axes and their values in the MWS_Calib 
       coordinate system 
output: a numpy array of the position values 
functionality: takes the values from the dictinary and inserts them in the array in the following order:
               array indice <----- dictinary key
                     0      <-----     'X'
                     1      <-----     'Y'
                     2      <-----     'Z'
                     3      <-----     'U'
                     4      <-----     'V'
                     5      <-----     'W'
remarks: N/A 
'''
def ConvertPositionToArray(curPos):
    pos = np.zeros(6)
    pos[0] = curPos['X']
    pos[1] = curPos['Y']
    pos[2] = curPos['Z']
    pos[3] = curPos['V']
    pos[4] = curPos['U']
    pos[5] = curPos['W']

    return pos
#----------------------------------------------------------------------------------------------------------------------#
'''
input: a PI object of the controller
output: N/A
functionality: moves the hexapod to the above defined 0^6 start vector in the MWS_Calib coordinate system 
remarks: N/A
'''
def MoveToStart(pidevice):
    pidevice.MOV(pidevice.axes, list(startVector))
    pitools.waitontarget(pidevice)
#----------------------------------------------------------------------------------------------------------------------#
'''
input: a PI object of the controller
output: N/A 
functionality: moves the hexapod's coordinate system back to ZERO coordinate system of the manufacturer 
remarks: prints a massage that the hexapod is disconnected and that the coordinate system is reseted
'''
def DisconnectAndReset(pidevice):
    pidevice.KEN('ZERO')
    pidevice.CloseConnection()
    print('\nHexapod disconnected and coordinate system was brought to ZERO.\n')
#----------------------------------------------------------------------------------------------------------------------#


# for safe keeping - delete after the hexapod integration is complete:
# import Hexapod
# from pipython import GCSDevice, pitools
# ################################## Code Example For Moving Hexapod - Don't Erease!!!! ##################################
# try:
#     # this combo makes the shit roll!!
#     C887, address = Hexapod.ConnectAndConfigure()
#     C887.ConnectTCPIPByDescription(address)
#
#     print('Current position:')
#     pprint.pprint(dict(C887.qPOS())) # verify that he hexapod did get to the 0^6 vctor in the coordinate system
#
#     print(C887.HasKSD()) # verify that the CS was changed to the calibration coordinate system
#
#     # the actual movement
#     target = np.array([0.7, 0.2, -0.1, 0.6, 0.8, 0.5]) * factor
#     Hexapod.MoveAbsolute(C887, target)
#     print('Current position:')
#     pprint.pprint(dict(C887.qPOS()))
#     kaki = np.array([0, 0, 0, 0, 0, 0])
#     Hexapod.MoveAbsolute(C887, kaki)
#     target = np.array([-0.7, -0.2, 0.1, -0.6, -0.8, -0.5]) * factor
#     Hexapod.MoveAbsolute(C887, target)
#     Hexapod.MoveToStart(C887)
#     print('Current position:')
#     pprint.pprint(dict(C887.qPOS()))
# finally:
#     Hexapod.DisconnectAndReset(C887)
# True
# ################################## Code Example For Moving Hexapod - Don't Erease!!!! ##################################