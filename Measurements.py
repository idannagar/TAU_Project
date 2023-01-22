import numpy as np
import matplotlib.pyplot as plt
# from scipy import interpolate
from scipy import ndimage

#----------------------------------------------------------------------------------------------------------------------#
############################# Defines #############################
pixelScale = 1e-6 # in meters
LOSTolerance = 10 # in pixels
ROllTolerance = 34e-3 # in radians
IFOV5um = 0.85e-3 # in radians # nominal average value for the whole FPA <- maybe useless, might delete later

############################# Defines #############################
#----------------------------------------------------------------------------------------------------------------------#
'''
input: a 7X7 numpy matrix that represents the area in which we shall calculate the blur value
output: a float value that is the blur value 
functionality: calculates the blur according to the formula from the CDR  
remarks: N/A
'''
def BLUR(pxMAT):
    AC = 1
    AB = 24
    AT = 9
    SC = pxMAT[3, 3]
    SB = pxMAT.sum() - pxMAT[1:6, 1:6].sum()
    ST = pxMAT[2:5, 2:5].sum()
    # print(f"SC = {SC}")
    return (SC - AC/AB * SB)/(ST - AT/AB * SB)
#----------------------------------------------------------------------------------------------------------------------#
'''
input: the indices of the center spot and the dimensions of the original image
output: 6 output values:
        (LOSH, LOSV) - a float that represent the distances in meters that the hexapod needs to move in X and Y directions in order 
        to move center of the FPA under the collimator's center spot
        distance - a float that represent the distance in meters between the center of the spot and the center of the FPA 
        (centerX, centerY) - the center of the FPA out of the 4 possible center options based on the initial spot indices
        (distance < LOSTolerance * pixelSize) - a boolean value that states if the LOS is in tolerance 
functionality: first we define the pixel size and the IFOV according to the FPA size or throw an exception 
               than we choose the center pixel of the frame from the 4 pixels in the middle based on the closest center 
               to the center of the spot
               finally we calculate the LOS values
remarks: N/A
'''
def LOS(centerSpot, imgH, imgW):
    if (imgH == 1024) and (imgW == 1280):
        pixelSize = 10 * pixelScale
        # IFOV = 2 * IFOV5um
    elif (imgH == 2048) and (imgW == 2560):
        pixelSize = 5 * pixelScale
        # IFOV = IFOV5um
    else:
        raise Exception("Invalid FPA Size")
    if centerSpot[1] <= imgW / 2:
        centerX = imgW / 2
    else:
        centerX = imgW / 2 + 1
    if centerSpot[0] <= imgH / 2:
        centerY = imgH / 2
    else:
        centerY = imgH / 2 + 1
    LOSH = (centerSpot[1] - centerX) * pixelSize # for hexapod
    LOSV = (centerSpot[0] - centerY) * pixelSize # for hexapod
    distance = np.linalg.norm([LOSH, LOSV]) # distance im meters for display and spec

    return LOSH, LOSV, distance, centerX, centerY, (distance < LOSTolerance * pixelSize)
#----------------------------------------------------------------------------------------------------------------------#
'''
input: the indices of the center spot, left spot, right spot at the original image
output: 2 output values:
        averageROLL - a float value that represent the FPA tilt relative to the horizon in degrees for the hexapod 
        (averageROLL < rollLimitDeg) - a boolean value that states if the ROLL is in tolerance 
functionality: calculates the angle between the line created by the left and right spot and the FPA horizon 
remarks: the print of "Bad Horizontal Alignment" is only for qualitative purpose and not a requirement 
'''
def ROLL(centerSpot, leftSpot, rightSpot):
    angleCenter2right = np.rad2deg(np.arctan2(rightSpot[0] - centerSpot[0], rightSpot[1] - centerSpot[1]))
    angleCenter2Left = np.rad2deg(np.arctan2(centerSpot[0] - leftSpot[0], centerSpot[1] - leftSpot[1]))
    # if np.abs(angleCenter2Left - angleCenter2right) > 5:
    #     print('Bad Horizontal Alignment')
    averageROLL = np.mean([angleCenter2right, angleCenter2Left], dtype=np.float64)
    # averageROLL = np.rad2deg(np.arctan2(rightSpot[0] - leftSpot[0], rightSpot[1] - leftSpot[1])) # angle between right and left
    rollLimitDeg = np.rad2deg(ROllTolerance)

    return averageROLL, (averageROLL < rollLimitDeg)
#----------------------------------------------------------------------------------------------------------------------#
'''
input: a 7X7 numpy matrix that represents the spot, two integars of the dimensions of the original image and a debug flag 
output: 2 float values of the estimated sub pixel horizontal and vertical decencter between the center of the center 
        pixel and the collimator's illumination 
functionality: @@@@@@@@@@@@@@@@@@ need to update @@@@@@@@@@@@@@@@@@
remarks: this is a mathematical approach to find the required distances (next to angles) to move the collimators without 
         doing iterations 
         may need additional fine search around achieved location to ensure that the collimator does point to the actual 
         center of the pixel and achieves the best power distribution in the blur region amount the pixels 
'''
def CenterSubPixelDecenter(pxMAT, imgH, imgW, debug_mode):
    if (imgH == 1024) and (imgW == 1280):
        pixelSize = 10 * pixelScale
        # IFOV = 2 * IFOV5um
    elif (imgH == 2048) and (imgW == 2560):
        pixelSize = 5 * pixelScale
        # IFOV = IFOV5um
    else:
        raise Exception("Invalid FPA Size")

    CoM = ndimage.center_of_mass(pxMAT[1:6, 1:6])
    subPixelDecenterH = (CoM[1] - 2) * pixelSize
    subPixelDecenterV = -(CoM[0] - 2) * pixelSize # minus is because of the way python arranges matrices and we want the distance required to move

    if debug_mode:
        fig, axs = plt.subplots(1, 2, figsize=(12, 6))
        axs[0].imshow(pxMAT[1:6, 1:6])
        # plt.title('Blur=' + (str(round(BLURcenter, 2))))
        plt.imshow(pxMAT[1:6, 1:6])
        plt.plot(CoM[1], CoM[0], color='green', marker='o', markersize=2)
        for i in range(-4, 5):
            plt.plot([2 + i * 0.1, 2 + i * 0.1], [1.5, 2.5], color=(0, 0.5, 1))
        for i in range(-4, 5):
            plt.plot([1.5, 2.5], [2 + i * 0.1, 2 + i * 0.1], color=(0, 0.5, 1))
        plt.plot([2, 2], [1.5, 2.5], color=(1, 0, 0.5))
        plt.plot([1.5, 2.5], [2, 2], color=(1, 0, 0.5))
        plt.plot([CoM[1], 2], [CoM[0], 2], color='green')
        plt.xlim((1.25, 2.75))
        plt.ylim((2.75, 1.25))
        plt.xlabel('Hoffset=' + str(round(subPixelDecenterH * 10 ** 6, 2)) + 'μm' +
                   '\nVoffset=' + str(round(subPixelDecenterV * 10 ** 6, 2)) + 'μm')
        # plt.show()
        plt.draw()
        plt.pause(2)
        plt.close()

    return (subPixelDecenterH, subPixelDecenterV)
#----------------------------------------------------------------------------------------------------------------------#
# '''
# input: a 7X7 numpy matrix that represents the spot, two integars of the dimensions of the full frame and a debug flag
# output: 2 float values of the estimated sub pixel horizontal and vertical decencter between the center of the center
#         pixel and the collimator's illumination
# functionality: first using the frame's dimensions we set the actual size of the pixel in meters
#                than we interpolate the given 7X7 matrix to a larger matrix that each pixel in said matrix is divided to
#                factorXfactor size, creating a new matrix of 7*factorX7*factor size
#                for the extended matrix created earlier we find the maximal value that represents the estimated position
#                of the illumination insdie the pixel, meaning it's a sub-pixel estimation
#                finally we calculate the metric distance of the horizontal and vertical offset between the estimated center
#                of the illumination and the actual center of the center pixel
#                if debug_mode is enabled than a graphic representation of the blur region of the pixel in question will
#                appear on the screen, alongside the interpolation inside the center pixel that illustrates the illumination
#                distribution insdie it
# remarks: this is a mathematical approach to find the required distances (next to angles) to move the collimators without
#          doing iterations
#          may need additional fine search around achieved location to ensure that the collimator does point to the actual
#          center of the pixel and achieves the best power distribution in the blur region amount the pixels
# '''
# def CenterSubPixelDecenter(pxMAT, imgH, imgW, debug_mode):
#     if (imgH == 1024) and (imgW == 1280):
#         pixelSize = 10 * pixelScale
#         # IFOV = 2 * IFOV5um
#     elif (imgH == 2048) and (imgW == 2560):
#         pixelSize = 5 * pixelScale
#         # IFOV = IFOV5um
#     else:
#         raise Exception("Invalid FPA Size")
#
#     X = np.linspace(0, 6, 7)
#     Y = np.linspace(0, 6, 7)
#     x, y = np.meshgrid(X, Y)
#     inter = interpolate.interp2d(x, y, pxMAT, kind ='quintic')  # cubic also does good job, need to verify in action
#
#     factor = 45
#     extendTo = 7 * factor
#     extendCenter = extendTo // 2 + 1
#     newX = np.linspace(0, 6, extendTo)
#     newY = np.linspace(0, 6, extendTo)
#     extendedImg = np.round(inter(newX, newY))
#     extendedCenterPixel = extendedImg[extendCenter - factor//2 - 1:extendCenter + factor//2,
#                           extendCenter - factor//2 - 1:extendCenter + factor//2]
#     I = np.where(extendedCenterPixel == np.amax(extendedCenterPixel))
#     inds = list(set(zip(I[0], I[1])))
#     extendedCenterIterp = np.round(np.mean(inds, axis = 0))
#     extendedCenterRelative = (factor//2 + 1, factor//2 + 1)
#
#     # distance on the horizontal axis and on the vertical axis of the interpolated sub-pixel center relative to the absulote center of the center pixel of the spot
#     subPixelDecenterH = (extendedCenterIterp[1] - extendedCenterRelative[1]) / factor * pixelSize
#     subPixelDecenterV = -(extendedCenterIterp[0] - extendedCenterRelative[0]) / factor * pixelSize  # minus is because of the way python arranges matrices and we want the distance required to move
#
#     if debug_mode:
#         fig, axs = plt.subplots(1, 2, figsize = (12, 6))
#         axs[0].imshow(pxMAT)
#         plt.title('Blur=' + (str(round(BLUR(pxMAT), 2))))
#         plt.imshow(extendedCenterPixel)
#         # circle = plt.Circle(extendedCenterRelative, 0.5, edgecolor = (1, 0, 0.5), fill = False) # circle around the center of the extended pixel
#         # plt.gca().add_patch(circle)
#         circle = plt.Circle((extendedCenterIterp[1], extendedCenterIterp[0]), 0.5, edgecolor = (0, 0.5, 1), fill = False)
#         plt.gca().add_patch(circle)
#         plt.plot([extendedCenterRelative[1], extendedCenterIterp[1]],
#                  [extendedCenterRelative[0], extendedCenterIterp[0]], '-', color = (0, 0.5, 1))
#         plt.plot([extendedCenterRelative[1], extendedCenterRelative[1]],
#                  [extendedCenterRelative[0] - 5, extendedCenterRelative[0] + 5], '-', color = (1, 0, 0.5))
#         plt.plot([extendedCenterRelative[1] - 5, extendedCenterRelative[1] + 5],
#                  [extendedCenterRelative[0], extendedCenterRelative[0]], '-', color = (1, 0, 0.5))
#         plt.xlabel('Hoffset=' + str(round(subPixelDecenterH * 10**6, 2)) + 'μm' +
#                    '\nVoffset=' + str(round(subPixelDecenterV * 10**6, 2)) + 'μm')
#         # plt.draw()
#         # plt.pause(1.5)
#         plt.show() # <- delete later, this halts the program
#
#     return (subPixelDecenterH, subPixelDecenterV)
#----------------------------------------------------------------------------------------------------------------------#