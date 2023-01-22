import numpy as np
import matplotlib.pyplot as plt
from scipy import interpolate
import Measurements as Meas
import ImageProcess as ImPros

#----------------------------------------------------------------------------------------------------------------------#
'''
input: a numpy matrix that represents the frame from the detector
output: 7 output values:
        BLURtop - a float that represent the blur value of the top spot 
        BLURleft - a float that represent the blur value of the left spot 
        BLURcenter - a float that represent the blur value of the center spot 
        BLURright - a float that represent the blur value of the right spot 
        BLURbottom - a float that represent the blur value of the bottom spot 
        ROLL - a tuple of the roll value of the frame and if in tolerance 
        LOS - a tuple of the LOS values, center of the FPA and if in tolerance 
functionality: calculates the different optical values from the detector's image using the Measurements module 
remarks: N/A 
'''
def CalcDetectorAll(imgMAT):
    [imgH, imgW] = imgMAT.shape
    topMAT, bottomMAT, centerMAT, leftMAT, rightMAT = ImPros.Divide2regions(imgMAT)
    spotsDict = ImPros.FindSpotsCenters(imgMAT)
    LOS = Meas.LOS(spotsDict['center'], imgH, imgW)  # in meters
    ROLL = Meas.ROLL(spotsDict['center'], spotsDict['left'], spotsDict['right'])  # in degrees
    # posibillity - put all blurs to a dictinory #
    BLURtop = Meas.BLUR(ImPros.BlurRegion(topMAT))
    BLURleft = Meas.BLUR(ImPros.BlurRegion(leftMAT))
    BLURcenter = Meas.BLUR(ImPros.BlurRegion(centerMAT))
    BLURright = Meas.BLUR(ImPros.BlurRegion(rightMAT))
    BLURbottom = Meas.BLUR(ImPros.BlurRegion(bottomMAT))

    return BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS
#----------------------------------------------------------------------------------------------------------------------#
'''
input: a numpy matrix that represents the frame from the detector and a debug flag 
output: a dictionary of the offset angles between the center of the pixel actual center and the estimated illumination 
        center for each of the 5 spots 
functionality: takes the 5 spots in the frame image and calculates for each first the metric distance to move, and than 
               returns the angular values after conversion using the auxiliry fuction "ConvertDistance2Angles"
remarks: to center the collimator with the center of the pixel we need the collimator to move the negative value of the 
         angles in the dictionary
'''
def CalcCollimatorsAngles(imgMAT, debug_mode):
    [imgH, imgW] = imgMAT.shape
    topMAT, bottomMAT, centerMAT, leftMAT, rightMAT = ImPros.Divide2regions(imgMAT)
    topDecenter = Meas.CenterSubPixelDecenter(ImPros.BlurRegion(topMAT), imgH, imgW, debug_mode)
    leftDecenter = Meas.CenterSubPixelDecenter(ImPros.BlurRegion(leftMAT), imgH, imgW, debug_mode)
    centerDecenter = Meas.CenterSubPixelDecenter(ImPros.BlurRegion(centerMAT), imgH, imgW, debug_mode)
    rightDecenter = Meas.CenterSubPixelDecenter(ImPros.BlurRegion(rightMAT), imgH, imgW, debug_mode)
    bottomDecenter = Meas.CenterSubPixelDecenter(ImPros.BlurRegion(bottomMAT), imgH, imgW, debug_mode)

    decnterDict = {
        'top': ConvertDistance2Angles(topDecenter, 'top'),
        'left': ConvertDistance2Angles(leftDecenter, 'left'),
        'center': ConvertDistance2Angles(centerDecenter, 'center'),
        'right': ConvertDistance2Angles(rightDecenter, 'right'),
        'bottom': ConvertDistance2Angles(bottomDecenter, 'bottom')
    }

    return decnterDict
#----------------------------------------------------------------------------------------------------------------------#
'''
input: a tuple with 2 float values that represent the metric decenter values and a string representing the spot's location 
       in the FPA
output: a tuple with 2 float values the represent the angular decnter values for the coliimators 
functionality: calculates the angles required to move the decenter values in the 2 axes, with respect to the field that
               the collimator illuminates from relative to the FPA plain 
remarks: auxiliry function for CalcCollimatorAngles
'''
def ConvertDistance2Angles(decenter, position):
    # values were taken from the Optical PDR
    conversionConst_00field = [0.159 * 10**3, 0.159 * 10**3] # from meters to radians
    conversionConst_50field = [0.150 * 10**3, 0.188 * 10**3] # from meters to radians
    conversionConst_60field = [0.182 * 10**3, 0.143 * 10**3] # from meters to radians
    if (position == 'top') or (position == 'bottom'):
        phi = np.rad2deg(decenter[0] * conversionConst_50field[0])
        theta = np.rad2deg(decenter[1] * conversionConst_50field[1])
    if (position == 'left') or (position == 'right'):
        phi = np.rad2deg(decenter[0] * conversionConst_60field[0])
        theta = np.rad2deg(decenter[1] * conversionConst_60field[1])
    if position == 'center':
        phi = np.rad2deg(decenter[0] * conversionConst_00field[0])
        theta = np.rad2deg(decenter[1] * conversionConst_00field[1])

    return (theta, phi)
#----------------------------------------------------------------------------------------------------------------------#