import numpy as np

#----------------------------------------------------------------------------------------------------------------------#
############################# Defines #############################
WIDTH = 100

############################# Defines #############################
#----------------------------------------------------------------------------------------------------------------------#
'''
input: a numpy matrix that represents the frame from the detector
output: 5 numpy matrices that represent the 5 regions in which the blur occurs
functionality: takes the entire frame and separates it into 9 equal size matrices and returns the relevant ones 
remarks: N/A 
'''
def Divide2regions(imgMAT):
    [imgH, imgW] = imgMAT.shape

    # top = imgMAT[0:imgH // 3, imgW // 3: 2 * imgW // 3]
    # bottom = imgMAT[2 * imgH // 3:imgH, imgW // 3: 2 * imgW // 3]
    # left = imgMAT[imgH // 3: 2 * imgH // 3, 0:imgW // 3]
    # right = imgMAT[imgH // 3: 2 * imgH // 3, 2 * imgW // 3:imgW]
    # center = imgMAT[imgH // 3: 2 * imgH // 3, imgW // 3: 2 * imgW // 3]

    width = WIDTH
    top = imgMAT[0:width, imgW // 2 - width // 2:imgW // 2 + width // 2]
    bottom = imgMAT[imgH - width:imgH, imgW // 2 - width // 2:imgW // 2 + width // 2]
    left = imgMAT[imgH // 2 - width // 2:imgH // 2 + width // 2, 0:width]
    right = imgMAT[imgH // 2 - width // 2:imgH // 2 + width // 2, imgW - width:imgW]
    center = imgMAT[imgH // 2 - width // 2:imgH // 2 + width // 2, imgW // 2 - width // 2:imgW // 2 + width // 2]

    return top, bottom, center, left, right
#----------------------------------------------------------------------------------------------------------------------#
'''
input: a numpy matrix that represents a specific region of the frame  
output: a 7X7 numpy matrix of the region relevent for blur calculation and display 
functionality: finds the indices of the maximal pixel value and crops around it a 7X7 region 
remarks: here there is no assumption that the maximal value is single
'''
def BlurRegion(pxMAT):
    I = np.where(pxMAT == np.amax(pxMAT)) #I are the indices of the maximum value
    inds = list(set(zip(I[0], I[1]))) #inds is matrix of maximum pixels indices

    return pxMAT[inds[0][0] - 3:inds[0][0] + 4, inds[0][1] - 3:inds[0][1] + 4]
#----------------------------------------------------------------------------------------------------------------------#
'''
input: a numpy matrix that represents the frame from the detector
output: a dictionary of the 5 collimators spot indices 
functionality: finds the top 5 valued pixels and assigns them the position labels 
remarks: here we assume that the top 5 points are such that there is only one high value point in each blur region 
         before calling this function we must check that there are 5 blur region consisiting a single max value each 
'''
def FindSpotsCenters(imgMAT):
    dict = {}
    [imgH, imgW] = imgMAT.shape
    topMAT, bottomMAT, centerMAT, leftMAT, rightMAT = Divide2regions(imgMAT)
    # # top
    # I = np.where(topMAT == np.amax(topMAT))
    # inds = list(set(zip(I[0], I[1]))) # the maximun inds are the indices of the specific region ('top') matrix
    # dict['top'] = (inds[0][0], inds[0][1] + imgW // 3) # dict['top'] are the maximum indices at the original image
    # # bottom
    # I = np.where(bottomMAT == np.amax(bottomMAT))
    # inds = list(set(zip(I[0], I[1])))
    # dict['bottom'] = (inds[0][0] + 2 * imgH // 3, inds[0][1] + imgW // 3)
    # # left
    # I = np.where(leftMAT == np.amax(leftMAT))
    # inds = list(set(zip(I[0], I[1])))
    # dict['left'] = (inds[0][0] + imgH // 3, inds[0][1])
    # # right
    # I = np.where(rightMAT == np.amax(rightMAT))
    # inds = list(set(zip(I[0], I[1])))
    # dict['right'] = (inds[0][0] + imgH // 3, inds[0][1] + 2 * imgW // 3)
    # # center
    # I = np.where(centerMAT == np.amax(centerMAT))
    # inds = list(set(zip(I[0], I[1])))
    # dict['center'] = (inds[0][0] + imgH // 3, inds[0][1] + imgW // 3)

    width = WIDTH
    # top
    I = np.where(topMAT == np.amax(topMAT))
    inds = list(set(zip(I[0], I[1])))  # the maximun inds are the indices of the specific region ('top') matrix
    dict['top'] = (inds[0][0], inds[0][1] + imgW // 2 - width // 2)  # dict['top'] are the maximum indices at the original image
    # bottom
    I = np.where(bottomMAT == np.amax(bottomMAT))
    inds = list(set(zip(I[0], I[1])))
    dict['bottom'] = (inds[0][0] + imgH - width, inds[0][1] + imgW // 2 - width // 2)
    # left
    I = np.where(leftMAT == np.amax(leftMAT))
    inds = list(set(zip(I[0], I[1])))
    dict['left'] = (inds[0][0] + imgH // 2 - width // 2, inds[0][1])
    # right
    I = np.where(rightMAT == np.amax(rightMAT))
    inds = list(set(zip(I[0], I[1])))
    dict['right'] = (inds[0][0] + imgH // 2 - width // 2, inds[0][1] + imgW - width)
    # center
    I = np.where(centerMAT == np.amax(centerMAT))
    inds = list(set(zip(I[0], I[1])))
    dict['center'] = (inds[0][0] + imgH // 2 - width // 2, inds[0][1] + imgW // 2 - width // 2)

    return dict
#----------------------------------------------------------------------------------------------------------------------#