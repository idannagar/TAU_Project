import io
import os
import sys
import time
import csv

import numpy as np
import matplotlib

import ctypes
import cv2 as CV
import scipy as sp
import trackpy as tp
from skimage.feature import match_template
from scipy.signal import savgol_filter

matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import Measurements as Meas
import ImageProcess as ImPros
import Calculations as Calc
import Hexapod
import FGCXP2 as FGCXP
import FGCL_resource as FGCL
import AutoToolKit
import Collimators as Colli

from PyQt5.QtCore import Qt, QSize, QCoreApplication
from PyQt5.QtCore import QTimer
from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtGui import QFont, QPalette
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QWidget,
    QDialog,
    QInputDialog,
    QTextEdit,
    QSizePolicy,
)

CP_console = f"cp{ctypes.cdll.kernel32.GetConsoleOutputCP()}"

############################# Defines #############################
LOSTolerance = 10  # in pixels
FIGSIZE = (18, 8)
DPI = 100
WINDOWSIZE = (1800, 1000)

buttonSize = (200, 100)
fontSize = 20

debug_mode = False
FG = "CL"  # ["CL", "CXP"]

angleStepsCoarse = [0.5, 0.1, 0.05, 0.01]  # <- 1deg
angleStepsFine = [0.005, 0.001, 0.0005, 0.0001]  # <- 1deg     max resolution
zAxisStepCoarse = 10 ** -3  # <- 1μm
zAxisStepFine = 10 ** -4  # <- 0.1μm    max resolution

BlurFloor = 0.3

ReportPath = "D:\\Reports\\"

maxIterations = 5

# plt.ion()
############################# Defines #############################
'''
input: N/A
output: N/A
functionality: N/A
remarks: N/A
'''

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        # build the gui window
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setFixedSize(QSize(WINDOWSIZE[0], WINDOWSIZE[1]))
        self.setStyleSheet("QMainWindow {background:rgb(225, 225, 225)}")
        # define the layouts
        layoutUpLow = QVBoxLayout()  # for upper lower divide
        layoutLeftRight = QHBoxLayout()  # for left right divide
        layoutButtons = QGridLayout()  # grid for buttons
        # build canves for the plot and place at the top the uplow layout
        self.canvas = FigureCanvas(plt.figure(figsize=FIGSIZE, dpi=DPI, frameon=False))
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.updateGeometry()

        layoutUpLow.addWidget(self.canvas)
        # add to the lower part the rightleft layout and place the text editor for display
        layoutUpLow.addLayout(layoutLeftRight)
        self.outputText = QtWidgets.QTextEdit(readOnly=True)
        layoutLeftRight.addWidget(self.outputText)
        # add in the lower layout the layout for the buttons
        layoutLeftRight.addLayout(layoutButtons)

        # define and add the buttons into the window
        self.button1 = QPushButton("Initialize TE")
        self.button1.setFixedSize(QSize(buttonSize[0], buttonSize[1]))
        self.button1.setFont(QFont('Calibri', fontSize))
        self.button1.setStyleSheet("background-color:rgb(107, 164, 255)")
        layoutButtons.addWidget(self.button1, 0, 0)

        self.button2 = QPushButton("Start Calibration")
        self.button2.setFixedSize(QSize(buttonSize[0], buttonSize[1]))
        self.button2.setFont(QFont('Calibri', fontSize))
        self.button2.setStyleSheet("background-color:rgb(156, 255, 107)")
        self.button2.setEnabled(False)
        layoutButtons.addWidget(self.button2, 0, 1)

        self.button3 = QPushButton("Exit TE")
        self.button3.setFixedSize(QSize(buttonSize[0], buttonSize[1]))
        self.button3.setFont(QFont('Calibri', fontSize))
        self.button3.setStyleSheet("background-color:rgb(225, 225, 225)")
        layoutButtons.addWidget(self.button3, 1, 0)

        self.button4 = QPushButton("Stop Calibration")
        self.button4.setFixedSize(QSize(buttonSize[0], buttonSize[1]))
        self.button4.setFont(QFont('Calibri', fontSize))
        self.button4.setStyleSheet("background-color:rgb(255, 87, 69)")
        self.button4.setEnabled(False)
        self.button4.setCheckable(True)
        layoutButtons.addWidget(self.button4, 1, 1)

        # assign button functionality
        self.button1.clicked.connect(self.InitPushed)
        self.button2.clicked.connect(self.StartPushed)
        self.button3.clicked.connect(self.ExitPushed)
        self.button4.clicked.connect(self.StopPushed)
        # --------------------------------------------------------------------------------------------------------------#
        # define figure parameters
        self.fig = self.canvas.figure  # <----------------------- the actual figure
        self.fig.patch.set_visible(False)
        self.frameNumber = 0

        # # define data collecting parameters
        # self.f = open('data.csv', 'w')
        # self.dataCSV = csv.writer(self.f)
        # header = ['Frame #', 'BLUR top', 'BLUR left', 'BLUR center', 'BLUR right', 'BLUR bottom',
        #           'ROLL [radian]', 'LOS horizontal [m]', 'LOS vertical [m]',
        #           'Angle correction top [theta degree, phi degree]',
        #           'Angle correction left [theta degree, phi degree]',
        #           'Angle correction center [theta degree, phi degree]',
        #           'Angle correction right [theta degree, phi degree]',
        #           'Angle correction bottom [theta degree, phi degree]']
        # self.dataCSV.writerow(header)

        # define hexapod parameters
        self.C887 = None
        self.address = None
        self.masterPosition = None

        # define coaxpress parameters
        self.buffHandle = None

        # define camera link parameters
        self.vidobjPath = None

        # define the collimators object parameters
        self.connection = None
        self.dictCollimators = None

        # # define matrices
        # self.badPixels = self.createBadPixalMap()
        # self.sensitivityMAT = None                             # <-- for newton rephson

        # define pixel and image parameters
        self.pixelSize = None
        # --------------------------------------------------------------------------------------------------------------#
        # put everything togather in the window
        widget = QWidget()
        widget.setLayout(layoutUpLow)
        self.setCentralWidget(widget)
        # # add a startup dialog to capture the S/N of the tested UUT
        # dialogTitle = "EagleEye TE"
        # inputTitle = "UTT S/N:"
        # text, isPressed = QInputDialog.getText(widget, dialogTitle, inputTitle, QLineEdit.Normal)
        # if isPressed:
        #     self.fullPath = ReportPath + text
        #     os.mkdir(self.fullPath)
        # else:
        #     self.fullPath = ReportPath + time.ctime().replace(" ", "").replace(":", "")
        #     os.mkdir(self.fullPath)
        # process configuration
        self.process = QtCore.QProcess(self)
        self.process.readyRead.connect(self.stdoutReady)
        self.process.readyRead.connect(self.stderrReady)

    def stdoutReady(self):
        cursor = self.outputText.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(str(self.process.readAllStandardOutput().data().decode(CP_console)))

    def stderrReady(self):
        cursor = self.outputText.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(str(self.process.readAllStandardError().data().decode(CP_console)))

    def InitPushed(self):
        self.button1.setEnabled(False)
        self.button2.setEnabled(True)
        self.outputText.append("Initializing TE...")

        # frame grabber activation
        try:
            if FG == "CXP":
                self.buffHandle = FGCXP.ConnectFGandCAM(debug_mode)
            if FG == "CL":
                self.vidobjPath = FGCL.ConnectFGandCAM()
                FGCL.OpenLiveVideo(self.vidobjPath)
        except:
            FGCL.CloseLiveVideo(self.vidobjPath)
            FGCL.DisconnectFGandCAM(self.vidobjPath)

        # # SCD toolkit activation
        # try:
        #     AutoToolKit.StartToolKit()
        # except:
        #     AutoToolKit.StopToolKit()

        # hexapod activation
        try:
            self.C887, self.address = Hexapod.ConnectAndConfigure()
            self.C887.ConnectTCPIPByDescription(self.address)
            Hexapod.MoveAbsolute(self.C887, np.array([0, 0, -5, 0, 0, 0]))
        except:
            Hexapod.DisconnectAndReset(self.C887)

        # collimators activation
        try:
            self.connection, self.dictCollimators = Colli.ConnectAndConfigure()
        except:
            Colli.DisconnectAndReset(self.connection)

        self.outputText.append("TE operational and ready to start")

    def StartPushed(self):
        self.button2.setEnabled(False)
        self.button3.setEnabled(False)
        self.button4.setEnabled(True)

        # move back to 0^6
        Hexapod.MoveToStart(self.C887)

        # do the initial calibration
        initTime = time.time()
        self.outputText.append("------ initial calibration  started ------\n")
        self.InitCalib()
        self.outputText.append("------ initial calibration finished ------\n")
        self.outputText.append(f"initial calibration took {time.time() - initTime} seconds\n")
        print(f"initial calibration took {time.time() - initTime} seconds")  # delete later

        currentPosition = self.ConvertPositionToArray(self.C887.qPOS())
        self.outputText.append(f"------ current hexapod position: ------")
        self.outputText.append(f"------ X:  {str(round(currentPosition[0], 5))} [mm] ------")
        self.outputText.append(f"------ Y:  {str(round(currentPosition[1], 5))} [mm] ------")
        self.outputText.append(f"------ Z:  {str(round(currentPosition[2], 5))} [mm] ------")
        self.outputText.append(f"------ U:  {str(round(currentPosition[3], 5))} [° ] ------")
        self.outputText.append(f"------ V:  {str(round(currentPosition[4], 5))} [° ] ------")
        self.outputText.append(f"------ W: {str(round(currentPosition[5], 5))} [° ] ------\n")
        # delete later
        print(f"------ current hexapod position: ------")
        print(f"------ X: {currentPosition[0]} [mm] ------")
        print(f"------ Y: {currentPosition[1]} [mm] ------")
        print(f"------ Z: {currentPosition[2]} [mm] ------")
        print(f"------ U: {currentPosition[3]} [° ] ------")
        print(f"------ V: {currentPosition[4]} [° ] ------")
        print(f"------ W: {currentPosition[5]} [° ] ------\n")

        # # calibrate the UV axes
        # tiltTime = time.time()
        # self.outputText.append("------ tilt calibration  started ------\n")
        # self.FullTilt(enablePlot=True)
        # # self.FullCenter()
        # self.outputText.append("------ tilt calibration finished ------\n")
        # self.outputText.append(f"tilt calibration took {time.time() - tiltTime} seconds\n")
        # print(f"tilt calibration took {time.time() - tiltTime} seconds")  # delete later
        #
        # currentPosition = self.ConvertPositionToArray(self.C887.qPOS())
        # self.outputText.append(f"------ current hexapod position: ------")
        # self.outputText.append(f"------ X:  {str(round(currentPosition[0], 5))} [mm] ------")
        # self.outputText.append(f"------ Y:  {str(round(currentPosition[1], 5))} [mm] ------")
        # self.outputText.append(f"------ Z:  {str(round(currentPosition[2], 5))} [mm] ------")
        # self.outputText.append(f"------ U:  {str(round(currentPosition[3], 5))} [° ] ------")
        # self.outputText.append(f"------ V:  {str(round(currentPosition[4], 5))} [° ] ------")
        # self.outputText.append(f"------ W: {str(round(currentPosition[5], 5))} [° ] ------\n")
        # # delete later
        # print(f"------ current hexapod position: ------")
        # print(f"------ X: {currentPosition[0]} [mm] ------")
        # print(f"------ Y: {currentPosition[1]} [mm] ------")
        # print(f"------ Z: {currentPosition[2]} [mm] ------")
        # print(f"------ U: {currentPosition[3]} [° ] ------")
        # print(f"------ V: {currentPosition[4]} [° ] ------")
        # print(f"------ W: {currentPosition[5]} [° ] ------\n")

        # # update screen to last calibration state
        # testpic = FGCL.GrabIMG(self.vidobjPath, enableNUC=True)
        # imgMAT = np.array(testpic)
        # [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS] = Calc.CalcDetectorAll(imgMAT)
        # self.PLOT(imgMAT, BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS)
        # plt.suptitle(str(self.C887.qPOS()))

        self.outputText.append("################################")
        self.outputText.append("### calibration finished for now ###")
        self.outputText.append("################################\n")

        # self.button3.setEnabled(True)
        # self.button4.setEnabled(False)

        if self.button4.isChecked():
            self.button4.toggle()

    def StopPushed(self):
        self.button3.setEnabled(True)
        self.button4.setEnabled(False)
        self.outputText.append("Calibration Stopped")

        # frame grabber termination
        if FG == "CXP":
            FGCXP.DisconnectFGandCAM()
        if FG == "CL":
            FGCL.CloseLiveVideo(self.vidobjPath)
            FGCL.DisconnectFGandCAM(self.vidobjPath)

        # # SCD toolkit termination
        # AutoToolKit.StopToolKit()

        # hexapod termination
        Hexapod.DisconnectAndReset(self.C887)

        # collimators termination
        Colli.DisconnectAndReset(self.connection)

    def ExitPushed(self):
        # # close the csv file, not the writer
        # self.f.close()
        # # move the collected data from the calibration into the UUT directory
        # import shutil
        # shutil.copy('C:\\Users\\admin\\PycharmProjects\\pythonProject1\\EagleEyeProj\\CurrentRev\\data.csv',
        #             self.fullPath + '\\data.csv')
        # close the gui window
        self.close()

    def PLOT(self, imgMAT, BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS):
        # clean the canvas before drawing the current figure
        self.fig.axes.clear()
        self.canvas.figure.clear()
        # redefine the figure segmantation
        GS = self.fig.add_gridspec(1, 2)
        GSleft = GS[0].subgridspec(1, 1)
        GSright = GS[1].subgridspec(3, 3)
        ax = self.fig.add_subplot(GSleft[0, 0])
        ax.axis('off')
        # start from here to build the figure for the current image
        [imgH, imgW] = imgMAT.shape
        topMAT, bottomMAT, centerMAT, leftMAT, rightMAT = ImPros.Divide2regions(imgMAT)
        im = ax.imshow(imgMAT,
                       vmin=3000,
                       vmax=imgMAT.max() + 500)
        ax.axis('on')
        spotsDict = ImPros.FindSpotsCenters(imgMAT)
        # mark with circles the colomators' spots
        for inds in spotsDict.values():
            circle = plt.Circle((inds[1], inds[0]),
                                10,
                                edgecolor='r',
                                fill=False)
            plt.gca().add_patch(circle)
        # draw the ROLL line between the left and right spots
        plt.plot([spotsDict['left'][1], spotsDict['right'][1]],
                 [spotsDict['left'][0], spotsDict['right'][0]],
                 '--',
                 color='r')
        # calculate ROLL value for display
        ROLLmRad = np.deg2rad(np.abs(ROLL[0])) * 1000  # in mRadians for displaying
        # draw LOS boundaries
        rectengle = plt.Rectangle((LOS[3] - LOSTolerance, LOS[4] - LOSTolerance),
                                  2 * LOSTolerance,
                                  2 * LOSTolerance,
                                  edgecolor='r',
                                  fill=False)
        plt.gca().add_patch(rectengle)
        plt.plot([spotsDict['center'][1], LOS[3]],
                 [spotsDict['center'][0], LOS[4]],
                 ':',
                 color=(0, 0.5, 1))
        # calculate LOS deviation for display
        LOSHmm = LOS[0] * 1000
        LOSVmm = LOS[1] * 1000
        LOSmm = LOS[2] * 1000
        plt.title('Detector')
        plt.xlabel('ROLL = ' + str(round(ROLLmRad, 2)) + 'mRad'
                   + '\nLOS = ' + str(round(LOSmm, 2)) + 'mm'
                   + '\nLOSH = ' + str(round(LOSHmm, 2)) + 'mm'
                   + '\nLOSV = ' + str(round(LOSVmm, 2)) + 'mm')

        axs = []
        for nn, (x, y) in enumerate([(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)]):
            ax = self.fig.add_subplot(GSright[x, y])
            if nn == 0:
                ax.imshow(ImPros.BlurRegion(topMAT))
                plt.title('Blur=' + str(round(BLURtop, 4)))
                plt.xlabel('Pixel ' + str(spotsDict['top']))
            if nn == 1:
                ax.imshow(ImPros.BlurRegion(leftMAT))
                plt.title('Blur=' + str(round(BLURleft, 4)))
                plt.xlabel('Pixel ' + str(spotsDict['left']))
            if nn == 2:
                ax.imshow(ImPros.BlurRegion(centerMAT))
                plt.title('Blur=' + str(round(BLURcenter, 4)))
                plt.xlabel('Pixel ' + str(spotsDict['center']))
            if nn == 3:
                ax.imshow(ImPros.BlurRegion(rightMAT))
                plt.title('Blur=' + str(round(BLURright, 4)))
                plt.xlabel('Pixel ' + str(spotsDict['right']))
            if nn == 4:
                ax.imshow(ImPros.BlurRegion(bottomMAT))
                plt.title('Blur=' + str(round(BLURbottom, 4)))
                plt.xlabel('Pixel ' + str(spotsDict['bottom']))
            axs += [ax]
        plt.subplots_adjust(wspace=0.25, hspace=0.25)
        self.frameNumber += 1
        plt.suptitle(f'Frame #{self.frameNumber}')
        plt.colorbar(im, ax=axs)
        # draw and refresh the figure on the canvas
        self.canvas.draw()
        QApplication.processEvents()  # <--- refreshes the drawing for each plot

    def InitCalib(self):
        alignmentTime = time.time()
        self.outputText.append("------ alignment  started ------")
        self.FirstAlignment(enablePlot=False)
        self.outputText.append("------ alignment finished ------")
        self.outputText.append(f"process took {time.time() - alignmentTime} seconds\n")
        print(f"alignment took {time.time() - alignmentTime} seconds")

        fullFocusTime = time.time()
        self.outputText.append("------ focusing  started ------")
        self.FullFocus(enablePlot=True)
        self.outputText.append("------ focusing finished ------")
        self.outputText.append(f"process took {time.time() - fullFocusTime} seconds\n")
        print(f"focus took {time.time() - fullFocusTime} seconds")  # delete later

        losTime = time.time()
        self.outputText.append("------ LOS/ROLL  started ------")
        self.LOSAndROLLCorrection(enablePlot=False)
        self.outputText.append("------ LOS/ROLL finished ------")
        self.outputText.append(f"process took {time.time() - losTime} seconds\n")
        print(f"los took {time.time() - losTime} seconds")  # delete later

        fineFocusTime = time.time()
        self.outputText.append("------ refocusing  started ------")
        self.FineFocusModified(enablePlot=True)
        self.outputText.append("------ refocusing finished ------")
        self.outputText.append(f"process took {time.time() - fineFocusTime} seconds\n")
        print(f"refocus took {time.time() - fineFocusTime} seconds")  # delete later

        centeringTime = time.time()
        self.outputText.append("------ centering  started ------")
        self.FullCenter()
        self.outputText.append("------ centering finished ------")
        self.outputText.append(f"process took {time.time() - centeringTime} seconds\n")
        print(f"centering took {time.time() - centeringTime} seconds")  # delete later

        self.outputText.append("------ grabbing image after initial calibration ------\n")
        testpic = FGCL.GrabIMG(self.vidobjPath, enableNUC=True)
        imgMAT = np.array(testpic)
        # calculate all parameters to correct the FPA
        # plot the whole calibration image
        [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS] = Calc.CalcDetectorAll(imgMAT)
        self.PLOT(imgMAT, BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS)

    def CoarseFocus(self, enablePlot=False):
        # step #1
        stepSize = 10 ** -1  # mm
        Nsteps = 15
        self.ScanFocus(stepSize,
                       Nsteps,
                       'center',
                       'focusValueSmall',
                       enablePlot)

    def FullFocus(self, enablePlot=False):
        # step #1
        stepSize = 10 ** -1  # mm
        Nsteps = 15
        self.ScanFocus(stepSize,
                       Nsteps,
                       'center',
                       'focusValueSmall',
                       enablePlot)

        # step #2
        stepSize = 10 ** -2  # mm
        Nsteps = 10
        self.ScanFocus(stepSize,
                       Nsteps,
                       'center',
                       'focusValueSmall',
                       enablePlot)

        # step #3
        stepSize = 10 ** -3  # mm
        Nsteps = 10
        self.ScanFocus(stepSize,
                       Nsteps,
                       'center',
                       'blur',
                       enablePlot)

    def FineFocus(self, enablePlot=False):
        # step #1
        stepSize = 10 ** -2  # mm
        Nsteps = 10
        self.ScanFocus(stepSize,
                       Nsteps,
                       'center',
                       'focusValueSmall',
                       enablePlot)

        # step #2
        stepSize = 10 ** -3  # mm
        Nsteps = 10
        self.ScanFocus(stepSize,
                       Nsteps,
                       'center',
                       'blur',
                       enablePlot)

    def FineFocusModified(self, enablePlot=False):
        # step #1
        stepSize = 10 ** -3  # mm
        Nsteps = 10
        self.ScanFocus(stepSize,
                       Nsteps,
                       'center',
                       'blur',
                       enablePlot)

    def ScanFocus(self, stepSize, Nsteps, tag, type, enablePlot=False):
        pos = self.ConvertPositionToArray(self.C887.qPOS())
        zDict = {}
        for Z in range(-Nsteps, Nsteps + 1):
            Hexapod.MoveAbsolute(self.C887, np.array(pos + [0, 0, Z * stepSize, 0, 0, 0]))

            testpic = FGCL.GrabIMG(self.vidobjPath, enableNUC=True)
            imgMAT = np.array(testpic)

            topMAT, bottomMAT, centerMAT, leftMAT, rightMAT = ImPros.Divide2regions(imgMAT)

            if tag == 'center':
                small = centerMAT
            elif tag == 'top':
                small = topMAT
            elif tag == 'bottom':
                small = bottomMAT
            elif tag == 'left':
                small = leftMAT
            elif tag == 'right':
                small = rightMAT

            focusValueImage = CV.Laplacian(imgMAT, CV.CV_64F).var()
            focusValueSmall = CV.Laplacian(small, CV.CV_64F).var()
            print(f"focus value of the full frame: {CV.Laplacian(imgMAT, CV.CV_64F).var()}\n"
                  f"focus value of the region around the spot: {CV.Laplacian(small, CV.CV_64F).var()}\n")

            I = np.where(small == np.amax(small))
            inds = list(set(zip(I[0], I[1])))
            r_center = inds[0][0]
            c_center = inds[0][1]
            # stupid and straightforward blur calculation
            AC = 1
            AB = 24
            AT = 9
            SC = small[r_center, c_center]
            SB = np.sum(small[r_center - 3:r_center + 4, c_center - 3:c_center + 4]) \
                 - np.sum(small[r_center - 2:r_center + 3, c_center - 2:c_center + 3])
            ST = np.sum(small[r_center - 1:r_center + 2, c_center - 1:c_center + 2])
            blur = (SC - AC / AB * SB) / (ST - AT / AB * SB)

            # save blur/GL to dict
            if type == 'blur':
                zDict[Z] = blur
            elif type == 'focusValueSmall':
                zDict[Z] = focusValueSmall
            else:
                zDict[Z] = focusValueImage
            print(f"the {type} at z={pos[2] + Z * stepSize} is {zDict[Z]}")
            if enablePlot:
                # create a small image for display
                cropped = small[r_center - 5:r_center + 6, c_center - 5:c_center + 6]
                # plot
                self.fig.axes.clear()
                self.canvas.figure.clear()
                ax = self.fig.add_subplot(1, 1, 1)
                ax.axis('off')
                ax.imshow(cropped)
                plt.title(f"the blur = {blur}")
                plt.xlabel(f"the center GL = {SC}\n"
                           f"({r_center}, {c_center})")
                self.canvas.draw()
                QApplication.processEvents()  # <--- refreshes the drawing for each plot

        bestZ = max(zDict, key=zDict.get)
        pos = pos + [0, 0, bestZ * stepSize, 0, 0, 0]
        Hexapod.MoveAbsolute(self.C887, np.array(pos))

        if enablePlot:
            # print again the best of the run
            testpic = FGCL.GrabIMG(self.vidobjPath, enableNUC=True)
            imgMAT = np.array(testpic)
            topMAT, bottomMAT, centerMAT, leftMAT, rightMAT = ImPros.Divide2regions(imgMAT)
            if tag == 'center':
                small = centerMAT
            elif tag == 'top':
                small = topMAT
            elif tag == 'bottom':
                small = bottomMAT
            elif tag == 'left':
                small = leftMAT
            elif tag == 'right':
                small = rightMAT
            I = np.where(small == np.amax(small))
            inds = list(set(zip(I[0], I[1])))
            r_center = inds[0][0]
            c_center = inds[0][1]
            # create a small image for display
            cropped = small[r_center - 5:r_center + 6, c_center - 5:c_center + 6]
            # plot
            self.fig.axes.clear()
            self.canvas.figure.clear()
            ax = self.fig.add_subplot(1, 1, 1)
            ax.axis('off')
            ax.imshow(cropped)
            plt.title(f"the *best* {type} = {zDict[bestZ]}")
            plt.xlabel(f"the center GL = {SC}")
            # ax.draw()
            # ax.pause(1)
            self.canvas.draw()
            QApplication.processEvents()  # <--- refreshes the drawing for each plot

    def ScanFocusModified(self, stepSize, Nsteps, tag, type, enablePlot=False):
        pos = self.ConvertPositionToArray(self.C887.qPOS())
        zDict = {}
        for Z in range(-Nsteps, Nsteps + 1):
            Hexapod.MoveAbsolute(self.C887, np.array(pos + [0, 0, Z * stepSize, 0, 0, 0]))

            testpic = FGCL.GrabIMG(self.vidobjPath, enableNUC=True)
            imgMAT = np.array(testpic)

            topMAT, bottomMAT, centerMAT, leftMAT, rightMAT = ImPros.Divide2regions(imgMAT)

            if tag == 'center':
                small = centerMAT
            elif tag == 'top':
                small = topMAT
            elif tag == 'bottom':
                small = bottomMAT
            elif tag == 'left':
                small = leftMAT
            elif tag == 'right':
                small = rightMAT

            focusValueImage = CV.Laplacian(imgMAT, CV.CV_64F).var()
            focusValueSmall = CV.Laplacian(small, CV.CV_64F).var()
            print(f"focus value of the full frame: {CV.Laplacian(imgMAT, CV.CV_64F).var()}\n"
                  f"focus value of the region around the spot: {CV.Laplacian(small, CV.CV_64F).var()}\n")

            I = np.where(small == np.amax(small))
            inds = list(set(zip(I[0], I[1])))
            r_center = inds[0][0]
            c_center = inds[0][1]
            # stupid and straightforward blur calculation
            AC = 1
            AB = 24
            AT = 9
            SC = small[r_center, c_center]
            SB = np.sum(small[r_center - 3:r_center + 4, c_center - 3:c_center + 4]) \
                 - np.sum(small[r_center - 2:r_center + 3, c_center - 2:c_center + 3])
            ST = np.sum(small[r_center - 1:r_center + 2, c_center - 1:c_center + 2])
            blur = (SC - AC / AB * SB) / (ST - AT / AB * SB)

            # save blur/GL to dict
            if type == 'blur':
                zDict[Z] = blur
            elif type == 'focusValueSmall':
                zDict[Z] = focusValueSmall
            else:
                zDict[Z] = focusValueImage
            print(f"the {type} at z={pos[2] + Z * stepSize} is {zDict[Z]}")
            if enablePlot:
                # create a small image for display
                cropped = small[r_center - 5:r_center + 6, c_center - 5:c_center + 6]
                # plot
                self.fig.axes.clear()
                self.canvas.figure.clear()
                ax = self.fig.add_subplot(1, 1, 1)
                ax.axis('off')
                ax.imshow(cropped)
                plt.title(f"the blur = {blur}")
                plt.xlabel(f"the center GL = {SC}\n"
                           f"({r_center}, {c_center})")
                self.canvas.draw()
                QApplication.processEvents()  # <--- refreshes the drawing for each plot

        w = savgol_filter(np.array(list(zDict.values())), Nsteps + 1, 2)

        indexMaxFiltered = np.argmax(w)
        filteredBestZ = list(zDict.keys())[indexMaxFiltered]
        filteredMax = w[indexMaxFiltered]

        measuredBestZ = max(zDict, key=zDict.get)
        measuredMax = zDict[measuredBestZ]

        pos = pos + [0, 0, filteredBestZ * stepSize, 0, 0, 0]
        Hexapod.MoveAbsolute(self.C887, np.array(pos))

        if enablePlot:
            # print again the best of the run
            testpic = FGCL.GrabIMG(self.vidobjPath, enableNUC=True)
            imgMAT = np.array(testpic)
            topMAT, bottomMAT, centerMAT, leftMAT, rightMAT = ImPros.Divide2regions(imgMAT)
            if tag == 'center':
                small = centerMAT
            elif tag == 'top':
                small = topMAT
            elif tag == 'bottom':
                small = bottomMAT
            elif tag == 'left':
                small = leftMAT
            elif tag == 'right':
                small = rightMAT
            I = np.where(small == np.amax(small))
            inds = list(set(zip(I[0], I[1])))
            r_center = inds[0][0]
            c_center = inds[0][1]
            # create a small image for display
            cropped = small[r_center - 5:r_center + 6, c_center - 5:c_center + 6]
            # plot
            self.fig.axes.clear()
            self.canvas.figure.clear()
            ax = self.fig.add_subplot(1, 1, 1)
            ax.axis('off')
            ax.imshow(cropped)
            plt.title(f"the *best* {type} = {zDict[filteredBestZ]}")
            plt.xlabel(f"the center GL = {SC}")
            # ax.draw()
            # ax.pause(1)
            self.canvas.draw()
            QApplication.processEvents()  # <--- refreshes the drawing for each plot

    def FirstAlignment(self, enablePlot=False):
        testpic = FGCL.GrabIMG(self.vidobjPath, enableNUC=False)
        imgMAT = np.array(testpic)

        pos = self.ConvertPositionToArray(self.C887.qPOS())
        # template with collimator
        focused = sp.io.loadmat(
            r"C:\Users\admin\PycharmProjects\pythonProject1\EagleEyeProj\CurrentRev\foucuesd_and_centered.mat")
        template = focused["snapshot6"][430:590, 530:720]

        # template without collimator
        # template = sp.io.loadmat(r"C:\Users\admin\PycharmProjects\pythonProject1\EagleEyeProj\CurrentRev\template.mat")
        # template = template["kernel"]

        test = imgMAT
        result = match_template(test, template, pad_input=True)
        y, x = np.unravel_index(np.argmax(result), result.shape)

        if enablePlot:
            plt.imshow(imgMAT, vmin=3000, vmax=5000)
            plt.plot(x, y, 'o', markeredgecolor='r', markerfacecolor='none', markersize=10)
            plt.plot(x, y, 'o', markeredgecolor='r', markerfacecolor='none', markersize=10)
            print(x, y)
            # plt.imshow(template, vmin=3000, vmax=5000)
            plt.show()

        dx = (x - 640) * 10e-6 * 1000
        dy = (y - 512) * 10e-6 * 1000
        Hexapod.MoveAbsolute(self.C887, np.array([-dx, -dy, 0, 0, 0, 0]))

    def LOSAndROLLCorrection(self, enablePlot=False):
        testpic = FGCL.GrabIMG(self.vidobjPath, enableNUC=True)
        print("image grabbed")
        imgMAT = np.array(testpic)
        topMAT, bottomMAT, centerMAT, leftMAT, rightMAT = ImPros.Divide2regions(imgMAT)
        spotsDict = ImPros.FindSpotsCenters(imgMAT)
        [imgH, imgW] = imgMAT.shape
        LOS = Meas.LOS(spotsDict['center'], imgH, imgW)  # in meters
        ROLL = Meas.ROLL(spotsDict['center'], spotsDict['left'], spotsDict['right'])  # in degrees
        print("calculated")
        print("moving the hexapod to align now!!")
        pos = self.ConvertPositionToArray(self.C887.qPOS())
        Hexapod.MoveAbsolute(self.C887, np.array(pos + [-LOS[0] * 1000, -LOS[1] * 1000, 0, 0, 0, ROLL[0]]))
        if enablePlot:
            # plot again after correction
            testpic = FGCL.GrabIMG(self.vidobjPath, enableNUC=True)
            print("image grabbed")
            imgMAT = np.array(testpic)
            print("recalculate")
            [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS] = Calc.CalcDetectorAll(imgMAT)
            self.PLOT(imgMAT, BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS)
            plt.close('all')

    # this is a dud at the moment and possibly useless
    def ScanXY(self, xyStepSize=10 ** -2, zStepSize=10 ** -3, enablePlot=False):
        pos = self.ConvertPositionToArray(self.C887.qPOS())

        zSteps = 5
        xySteps = 5

        # data = np.empty((0, 11))
        blurs = np.zeros((11, 11, 11))
        gls = np.zeros((11, 11, 11))
        bestPositon = None
        bestCenterBlur = 0

        for x in range(-xySteps, xySteps + 1):  # left->right
            for y in range(-xySteps, xySteps + 1):  # bottom->top
                # for z in range(-zSteps, zSteps + 1):  # down->up
                Hexapod.MoveAbsolute(self.C887, np.array(pos + [x * xyStepSize,
                                                           y * xyStepSize,
                                                           0,
                                                           0, 0, 0]))

                testpic = FGCL.GrabIMG(self.vidobjPath, enableNUC=True)
                imgMAT = np.array(testpic)

                ### delete ###
                topMAT, bottomMAT, centerMAT, leftMAT, rightMAT = ImPros.Divide2regions(imgMAT)
                I = np.where(centerMAT == np.amax(centerMAT))
                inds = list(set(zip(I[0], I[1])))
                r_center = inds[0][0]
                c_center = inds[0][1]
                SC = centerMAT[r_center, c_center]  # GL
                ### delete ###

                [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS] = Calc.CalcDetectorAll(imgMAT)
                blurs[x + xySteps][y + xySteps] = BLURcenter  # [z + zSteps]
                gls[x + xySteps][y + xySteps] = SC  # [z + zSteps]
                print(f"blur at {(x, y)} is {BLURcenter}\n"
                      f"gl at {(x, y)} is {SC}")

                if enablePlot:
                    self.PLOT(imgMAT, BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS)

                # pos = ConvertPositionToArray(C887.qPOS())
                # data = np.append(data, np.array([BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom].extend(pos)), axis=0)

        #         dataTable = np.transpose(data[x + xySteps][y + xySteps])
        #         bestCenterBlurZ = np.argmax(dataTable[2, :])  # <-- center oriented
        #         bestBalancedBlurZ = np.argmin(np.std(dataTable[0:4, :], axis=0))  # <-- all oriented
        #         if (np.min(dataTable[0:4, bestBalancedBlurZ]) > 0.3) or \
        #            (np.min(dataTable[0:4, bestCenterBlurZ]) > 0.3):
        #             if (bestBalancedBlurZ > bestCenterBlurZ):
        #                 direction = 1
        #             else:
        #                 direction = -1
        #             # move from the best center to the best balanced state that favors the center
        #             for z in range(bestCenterBlurZ, bestBalancedBlurZ, direction):
        #                 if (np.min(dataTable[0:4, z]) > 0.3):
        #                     if (dataTable[2][z] > bestCenterBlur):
        #                         bestCenterBlur = dataTable[2][z]
        #                         bestPositon = dataTable[5][z]
        #                     break
        #             else:
        #                 bestCenterBlur = dataTable[2][bestBalancedBlurZ]
        #                 bestPositon = dataTable[5][bestBalancedBlurZ]
        #
        # return bestPositon
        plt.figure(1)
        plt.matshow(blurs[:, :, 0])  #
        plt.figure(2)
        plt.matshow(gls[:, :, 0])  #
        plt.show()

    def FullCenter(self):
        self.Centering(D=7,
                       preprocess=True,
                       enablePlot=False)
        self.Centering(D=7,
                       preprocess=True,
                       enablePlot=False)
        self.Centering(D=5,
                       preprocess=True,
                       enablePlot=False)
        self.Centering(D=3,
                       preprocess=False,
                       enablePlot=False)

    def FineCenter(self):
        self.Centering(D=5,
                       preprocess=True,
                       enablePlot=False)
        self.Centering(D=3,
                       preprocess=False,
                       enablePlot=False)

    def Centering(self, D=7, preprocess=True, enablePlot=False):
        testpic = FGCL.GrabIMG(self.vidobjPath, enableNUC=True)
        # testpic = FGCL.GrabIMGMean(vidobjPath, 10)
        imgMAT = np.array(testpic)
        topMAT, bottomMAT, centerMAT, leftMAT, rightMAT = ImPros.Divide2regions(imgMAT)

        factor = 10e-6
        conversionConst_00field = [0.170 * 10 ** 3, 0.170 * 10 ** 3]  # from [m] to [rad]
        conversionConst_50field = [0.150 * 10 ** 3, 0.188 * 10 ** 3]  # from [m] to [rad]
        conversionConst_60field = [0.182 * 10 ** 3, 0.143 * 10 ** 3]  # from [m] to [rad]

        mat = ImPros.BlurRegion(centerMAT)
        x, y = self.FindCentroid(mat, D, preprocess, enablePlot)
        dx = x - 3
        dy = -(y - 3)
        collimator = self.dictCollimators['center']
        Colli.MoveRelative(collimator, (np.rad2deg(-dx * factor * conversionConst_00field[0]),
                                        np.rad2deg(-dy * factor * conversionConst_00field[1])))

        mat = ImPros.BlurRegion(topMAT)
        x, y = self.FindCentroid(mat, D, preprocess, enablePlot)
        dx = x - 3
        dy = -(y - 3)
        collimator = self.dictCollimators['top']
        Colli.MoveRelative(collimator, (np.rad2deg(-dx * factor * conversionConst_50field[0]),
                                        np.rad2deg(-dy * factor * conversionConst_50field[1])))

        mat = ImPros.BlurRegion(bottomMAT)
        x, y = self.FindCentroid(mat, D, preprocess, enablePlot)
        dx = x - 3
        dy = -(y - 3)
        collimator = self.dictCollimators['bottom']
        Colli.MoveRelative(collimator, (np.rad2deg(-dx * factor * conversionConst_50field[0]),
                                        np.rad2deg(-dy * factor * conversionConst_50field[1])))

        mat = ImPros.BlurRegion(leftMAT)
        x, y = self.FindCentroid(mat, D, preprocess, enablePlot)
        dx = x - 3
        dy = -(y - 3)
        collimator = self.dictCollimators['left']
        Colli.MoveRelative(collimator, (np.rad2deg(+dy * factor * conversionConst_60field[0]),
                                        np.rad2deg(-dx * factor * conversionConst_60field[1])))

        mat = ImPros.BlurRegion(rightMAT)
        x, y = self.FindCentroid(mat, D, preprocess, enablePlot)
        dx = x - 3
        dy = -(y - 3)
        collimator = self.dictCollimators['right']
        Colli.MoveRelative(collimator, (np.rad2deg(+dy * factor * conversionConst_60field[0]),
                                        np.rad2deg(-dx * factor * conversionConst_60field[1])))

    @staticmethod
    def FindCentroid(mat, D=7, preprocess=True, toPlot=False):
        # maybe should add try-expect
        features = tp.locate(mat,
                             D,
                             topn=1,
                             preprocess=preprocess,
                             engine='python')
        try:
            x, y = features[['x', 'y']].iloc[0].values
        except IndexError as error:
            print(error)
            return 0, 0

        if toPlot:
            fig, ax = plt.subplots(1, 2)
            tp.annotate(features, mat,
                        plot_style=dict(marker='x', markersize=8),
                        imshow_style=dict(vmin=4000, vmax=7500),
                        # imshow_style=dict(vmin=np.max(mat) - 1600, vmax=np.max(mat)),
                        ax=ax[0])
            ax[0].plot([3, 3], [2.5, 3.5], 'b')
            ax[0].plot([2.5, 3.5], [3, 3], 'b')
            tp.annotate(features, mat,
                        plot_style=dict(marker='x', markersize=8),
                        imshow_style=dict(vmin=4000, vmax=7500),
                        ax=ax[1])
            ax[1].plot([3, 3], [2.5, 3.5], 'b')
            ax[1].plot([2.5, 3.5], [3, 3], 'b')
            ax[1].axis([2.5, 3.5, 3.5, 2.5])
            ax[1].plot([3, x], [y, y], 'g')
            ax[1].plot([x, x], [3, y], 'g')
            plt.xlabel(f"dx={x - 3}\ndy={-(y - 3)}")
            # # need fixing :)
            # angle = np.rad2deg(np.arctan2(3 - x, y - 3))
            # ax[1].set_title(angle)
            plt.show()

        return x, y

    def FullTilt(self, enablePlot=False):
        # # step #1
        # angleRes = 0.01  # deg
        # Nsteps = 5
        # ScanTiltModified(vidobjPath, C887, dictCollimators, angleRes, Nsteps, enablePlot)
        #
        # # step #2
        # angleRes = 0.005  # deg
        # Nsteps = 2
        # ScanTiltModified(vidobjPath, C887, dictCollimators, angleRes, Nsteps, enablePlot)

        # step #3
        angleRes = 0.05  # deg
        Nsteps = 2
        self.ScanTiltModified(angleRes,
                              Nsteps,
                              enablePlot)

        # step #4
        angleRes = 0.01  # deg
        Nsteps = 3
        self.ScanTiltModified(angleRes,
                              Nsteps,
                              enablePlot)

        # step #5
        angleRes = 0.005  # deg
        Nsteps = 2
        self.ScanTiltModified(angleRes,
                              Nsteps,
                              enablePlot)

    # this is a dud at the moment and possibly useless
    def ScanTilt(self, angleRes, Nsteps, enablePlot=False):  # delete later!
        pos = self.ConvertPositionToArray(self.C887.qPOS())

        # uDict = {}
        # vDict = {}
        # qDict = {}

        qMat = np.zeros((2 * Nsteps + 1, 2 * Nsteps + 1))

        motherMat = np.zeros(((2 * Nsteps + 1) ** 2, 5))

        for U in range(-Nsteps, Nsteps + 1):
            for V in range(-Nsteps, Nsteps + 1):
                Hexapod.MoveAbsolute(self.C887, np.array(pos + [0, 0, 0, U * angleRes, V * angleRes, 0]))
                self.Centering(self.vidobjPath,
                               self.dictCollimators,
                               D=5,
                               preprocess=True,
                               enablePlot=False)
                self.Centering(self.vidobjPath,
                               self.dictCollimators,
                               D=3,
                               preprocess=False,
                               enablePlot=False)
                testpic = FGCL.GrabIMG(self.vidobjPath, enableNUC=True)
                imgMAT = np.array(testpic)
                [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS] = Calc.CalcDetectorAll(imgMAT)
                # uDict[U * angleRes] = np.abs(BLURtop - BLURbottom) - (BLURtop + BLURbottom)
                # vDict[V * angleRes] = np.abs(BLURleft - BLURright) - (BLURleft + BLURright)
                # qDict[(U * angleRes, V * angleRes)] = uDict[U * angleRes] + vDict[V * angleRes]

                qMat[U + Nsteps][V + Nsteps] = np.abs(BLURtop - BLURbottom) - (BLURtop + BLURbottom) + \
                                               np.abs(BLURleft - BLURright) - (BLURleft + BLURright)
                motherMat[U + Nsteps + V + Nsteps, 0] = np.abs(BLURleft - BLURright)
                motherMat[U + Nsteps + V + Nsteps, 1] = (BLURleft + BLURright)
                motherMat[U + Nsteps + V + Nsteps, 2] = np.abs(BLURtop - BLURbottom)
                motherMat[U + Nsteps + V + Nsteps, 3] = (BLURtop + BLURbottom)
                motherMat[U + Nsteps + V + Nsteps, 4] = BLURcenter

                print(f"at U={U} and V={V}:\n"
                      # f"top-bottom factor is {uDict[U * angleRes]}\n"
                      # f"left-right factor is {vDict[V * angleRes]}\n"
                      # f"total qFactor is {qDict[(U * angleRes, V * angleRes)]}"
                      f"total qFactor is {qMat[U + Nsteps][V + Nsteps]}")

                if enablePlot:
                    [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS] = Calc.CalcDetectorAll(imgMAT)
                    self.PLOT(imgMAT, BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS)

        # bestU = min(uDict, key=uDict.get)
        # bestV = min(vDict, key=vDict.get)
        # (bestU, bestV) = min(qDict, key=qDict.get)

        def get_weights(vector, weight, getMax):
            index = []
            if getMax:
                sorted_vector = np.sort(vector.copy())
            else:
                sorted_vector = np.sort(vector.copy())[::-1]
            weight_sorted_list = np.linspace(0, weight, len(vector))
            weight_list = np.zeros((len(vector), 1))
            for i, j in enumerate(sorted_vector):
                index.append(np.where(j == vector)[0][0])
                weight_list[index[i]] = weight_sorted_list[i]
            return weight_list

        I = np.where(qMat == np.amin(qMat))
        bestU = I[0][0] - Nsteps
        bestV = I[1][0] - Nsteps

        pos = pos + [0, 0, 0, bestU * angleRes, bestV * angleRes, 0]
        Hexapod.MoveAbsolute(self.C887, np.array(pos))
        self.self.Centering(self.vidobjPath,
                            self.dictCollimators,
                            D=5,
                            preprocess=True,
                            enablePlot=False)
        self.self.Centering(self.vidobjPath,
                            self.dictCollimators,
                            D=3,
                            preprocess=False,
                            enablePlot=False)

        if enablePlot:
            testpic = FGCL.GrabIMG(self.vidobjPath, enableNUC=True)
            imgMAT = np.array(testpic)
            [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS] = Calc.CalcDetectorAll(imgMAT)
            self.PLOT(imgMAT, BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS)

            plt.figure(2)
            plt.matshow(qMat)
            plt.show()

    def ScanTiltModified(self, angleRes, Nsteps, enablePlot=False):
        pos = self.ConvertPositionToArray(self.C887.qPOS())

        qMat = np.zeros((2 * Nsteps + 1, 2 * Nsteps + 1))
        # uMat = np.zeros((2 * Nsteps + 1, 2 * Nsteps + 1))
        # vMat = np.zeros((2 * Nsteps + 1, 2 * Nsteps + 1))

        rMat = np.zeros((2 * Nsteps + 1, 2 * Nsteps + 1))
        lMat = np.zeros((2 * Nsteps + 1, 2 * Nsteps + 1))
        tMat = np.zeros((2 * Nsteps + 1, 2 * Nsteps + 1))
        bMat = np.zeros((2 * Nsteps + 1, 2 * Nsteps + 1))

        for U in range(-Nsteps, Nsteps + 1):
            for V in range(-Nsteps, Nsteps + 1):
                Hexapod.MoveAbsolute(self.C887, np.array(pos + [0, 0, 0, U * angleRes, V * angleRes, 0]))
                self.FineCenter()

                numOfSamples = 10
                blurArray = np.zeros((numOfSamples, 5))

                for i in range(numOfSamples):
                    testpic = FGCL.GrabIMG(self.vidobjPath, enableNUC=True)
                    imgMAT = np.array(testpic)
                    [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS] = Calc.CalcDetectorAll(imgMAT)
                    blurArray[i, :] = [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom]

                # average criteria
                blurAverages = np.average(blurArray, axis=0)
                top, left, center, right, bottom = blurAverages

                # qMat[U + Nsteps][V + Nsteps] = np.abs(top - bottom) - (top + bottom)/2 +\
                #                                np.abs(left - right) - (left + right)/2
                # uMat[U + Nsteps][V + Nsteps] = np.abs(top - bottom) - (top + bottom) / 2
                # vMat[U + Nsteps][V + Nsteps] = np.abs(left - right) - (left + right) / 2

                # # maximum criteria
                # blurMaximums = np.amax(blurArray, axis=0)
                # top, left, center, right, bottom = blurMaximums
                # qMat[U + Nsteps][V + Nsteps] = np.abs(top - bottom) - (top + bottom) + \
                #                                np.abs(left - right) - (left + right)

                rMat[U + Nsteps][V + Nsteps] = BLURright
                lMat[U + Nsteps][V + Nsteps] = BLURleft
                tMat[U + Nsteps][V + Nsteps] = BLURtop
                bMat[U + Nsteps][V + Nsteps] = BLURbottom

                print(f"at U={U} and V={V}:\n"
                      f"total qFactor is {qMat[U + Nsteps][V + Nsteps]}")

                if enablePlot:
                    [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS] = Calc.CalcDetectorAll(imgMAT)
                    self.PLOT(imgMAT, BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS)

        bestLR, deltaLR, sumLR = self.findBestIndices(rMat, lMat, Nsteps)
        bestTB, deltaTB, sumTB = self.findBestIndices(tMat, bMat, Nsteps)

        qFactorLR = sumLR - deltaLR
        qFactorTB = sumTB - deltaTB

        bestLRU, bestLRV = bestLR[0] - Nsteps, bestLR[1] - Nsteps
        bestTBU, bestTBV = bestTB[0] - Nsteps, bestTB[1] - Nsteps

        if qFactorTB > qFactorLR:
            bestU, bestV = bestTBU, bestTBV
        else:
            bestU, bestV = bestLRU, bestLRV
        pos = pos + [0, 0, 0, bestU * angleRes, bestV * angleRes, 0]
        Hexapod.MoveAbsolute(self.C887, np.array(pos))
        self.FineCenter()

        if enablePlot:
            testpic = FGCL.GrabIMG(self.vidobjPath, enableNUC=True)
            imgMAT = np.array(testpic)
            [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS] = Calc.CalcDetectorAll(imgMAT)
            self.PLOT(imgMAT, BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS)

    @staticmethod
    def findBestIndices(blurA, blurB, N):
        blurA = blurA.reshape(1, len(blurA) ** 2)[0]
        blurB = blurB.reshape(1, len(blurB) ** 2)[0]

        Idx = np.arange(0, len(blurA))
        indices = list(np.ndindex((2 * N + 1, 2 * N + 1)))

        delta = np.abs(blurA - blurB)
        motherMat = np.vstack((Idx, delta))
        sum = blurA + blurB
        motherMat = np.vstack((motherMat, sum))

        sortedMoM = motherMat[:, motherMat[1].argsort()]
        print(sortedMoM)

        optLocation = sortedMoM[0, np.argmax(sortedMoM[2, :N] - sortedMoM[1, :N])]
        optDelta = sortedMoM[1, np.argmax(sortedMoM[2, :N] - sortedMoM[1, :N])]
        optSum = sortedMoM[2, np.argmax(sortedMoM[2, :N] - sortedMoM[1, :N])]
        optIndices = indices[int(optLocation)]

        return optIndices, optDelta, optSum

    @staticmethod
    def ConvertPositionToArray(curPos):
        pos = np.zeros(6)
        pos[0] = curPos['X']
        pos[1] = curPos['Y']
        pos[2] = curPos['Z']
        pos[3] = curPos['V']
        pos[4] = curPos['U']
        pos[5] = curPos['W']

        return pos

    def Grab(self):
        pass
        # # take a frame from the detector
        # if (FG == "CXP"):
        #     imgMAT = FGCXP.GrabIMG(self.buffHandle, debug_mode)
        # if (FG == "CL"):
        #     imgMAT = FGCL.GrabIMG(self.vidobjPath)
        # [imgH, imgW] = imgMAT.shape
        # if (imgH == 1024) and (imgW == 1280):
        #     self.pixelSize = 10 * 10 ** -6
        # elif (imgH == 2048) and (imgW == 2560):
        #     self.pixelSize = 5 * 10 ** -6
        # # pass through the NUC <-- local GO does not work at the moment @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
        # nucPath = 'C:\\Users\\admin\\PycharmProjects\\pythonProject1\\EagleEyeProj\\CurrentRev\\NUC\\'
        # nuc_top.arr2hex(imgMAT, nucPath + 'imgNUCin.txt', 16, imgH, imgW)
        # imgMAT, badPixels = nuc_top.nuc_top(nucPath + 'imgNUCin.txt',
        #                                     nucPath + 'imgNUCout.txt',
        #                                     nucPath + 'reg_file_12801024.csv',
        #                                     nucPath + 'parameters_nuc.csv',
        #                                     nucPath + 'GO_hex.txt',
        #                                     nucPath + 'GO_hex.txt', True)
        # # address the bad pixels
        # dictSpots = ImPros.FindSpotsCenters(imgMAT)
        # dis = 10  # the distance allowed to move from the initial point
        # for tag in ['top', 'bottom', 'left', 'right', 'center']:
        #     flagBreak = False
        #     # currentCollimator = self.dictCollimators[tag]
        #     if np.sum(badPixels[dict[tag][0] - 4:dict[tag][0] + 5,
        #               dict[tag][1] - 4:dict[tag][1] + 5]) == 0:
        #         continue
        #     # circular search
        #     for i in range(1, dis + 1):
        #         for j in range(0, 2 * i + 1):
        #             if np.sum(badPixels[dict[tag][0] - 4 - i:dict[tag][0] + 5 - i,
        #                       dict[tag][1] - 4 - i + j:dict[tag][1] + 5 - i + j]) == 0:
        #                 angles = self.ConvertDistance2Angles((i * self.pixelSize, (-i + j) * self.pixelSize),
        #                                                      tag)  # minus at y/row
        #                 flagBreak = True
        #                 break
        #         if flagBreak:
        #             # Colli.MoveRelative(currentCollimator, angles)
        #             break
        #         for j in range(1, 2 * i + 1):
        #             if np.sum(badPixels[dict[tag][0] - 4 - i + j:dict[tag][0] + 5 - i + j,
        #                       dict[tag][1] - 4 + i:dict[tag][1] + 5 + i]) == 0:
        #                 angles = self.ConvertDistance2Angles((-(-i + j) * self.pixelSize, i * self.pixelSize),
        #                                                      tag)  # minus at y/row
        #                 flagBreak = True
        #                 break
        #         if flagBreak:
        #             # Colli.MoveRelative(currentCollimator, angles)
        #             break
        #         for j in range(1, 2 * i + 1):
        #             if np.sum(badPixels[dict[tag][0] - 4 + i:dict[tag][0] + 5 + i,
        #                       dict[tag][1] - 4 + i - j:dict[tag][1] + 5 + i - j]) == 0:
        #                 angles = self.ConvertDistance2Angles((-i * self.pixelSize, (i - j) * self.pixelSize),
        #                                                      tag)  # minus at y/row
        #                 flagBreak = True
        #                 break
        #         if flagBreak:
        #             # Colli.MoveRelative(currentCollimator, angles)
        #             break
        #         for j in range(1, 2 * i):
        #             if np.sum(badPixels[dict[tag][0] - 4 + i - j:dict[tag][0] + 5 + i - j,
        #                       dict[tag][1] - 4 - i:dict[tag][1] + 5 - i]) == 0:
        #                 angles = self.ConvertDistance2Angles((-(i - j) * self.pixelSize, -i * self.pixelSize),
        #                                                      tag)  # minus at y/row
        #                 flagBreak = True
        #                 break
        #         if flagBreak:
        #             # Colli.MoveRelative(currentCollimator, angles)
        #             break
        # # we move the collimators to the pixel centers - we correct the offset amount in dictAngles
        # dictAngles = Calc.CalcCollimatorsAngles(imgMAT, debug_mode)
        # # Colli.MoveRelative(self.dictCollimators['top'], tuple(-angle for angle in dictAngles['top']))
        # # Colli.MoveRelative(self.dictCollimators['bottom'], tuple(-angle for angle in dictAngles['bottom']))
        # # Colli.MoveRelative(self.dictCollimators['left'], tuple(-angle for angle in dictAngles['left']))
        # # Colli.MoveRelative(self.dictCollimators['right'], tuple(-angle for angle in dictAngles['right']))
        # # Colli.MoveRelative(self.dictCollimators['center'], tuple(-angle for angle in dictAngles['center']))
        # # now we should not be upon bad pixels and at the center of the pixel - need to retake the image
        # if (FG == "CXP"):
        #     imgMAT = FGCXP.GrabIMG(self.buffHandle, debug_mode)
        # if (FG == "CL"):
        #     imgMAT = FGCL.GrabIMG(self.vidobjPath)
        # [imgH, imgW] = imgMAT.shape
        # # pass through the NUC again
        # nuc_top.arr2hex(imgMAT, nucPath + 'imgNUCin.txt', 16, imgH, imgW)
        # imgMAT, badPixels = nuc_top.nuc_top(nucPath + 'imgNUCin.txt',
        #                                     nucPath + 'imgNUCout.txt',
        #                                     nucPath + 'reg_file_12801024.csv',
        #                                     nucPath + 'parameters_nuc.csv',
        #                                     nucPath + 'GO_hex.txt',
        #                                     nucPath + 'GO_hex.txt', True)
        # self.UpdateGUI("Grabbing Message")
        #
        # return imgMAT

    @staticmethod
    def ConvertDistance2Angles(decenter, position):
        # values were taken from the Optical PDR
        conversionConst_00field = [0.159 * 10 ** 3, 0.159 * 10 ** 3]  # from meters to radians
        conversionConst_50field = [0.150 * 10 ** 3, 0.188 * 10 ** 3]  # from meters to radians
        conversionConst_60field = [0.182 * 10 ** 3, 0.143 * 10 ** 3]  # from meters to radians
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

    def UpdateGUI(self, message, imgMAT=None, data=None):
        if message == "Grabbing Message":
            self.outputText.append(f"↓↓↓↓↓↓↓↓↓↓↓↓ Frame #{self.frameNumber + 1} ↓↓↓↓↓↓↓↓↓↓↓↓")
            self.outputText.append("Frame taken successfully.")
            self.outputText.append("Non-uniformity correction done.")

        if message == "Calc Plot Save Message":
            self.outputText.append("Calculating...")
            [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS, angles] = data
            self.outputText.append("Plotting...")
            self.PLOT(imgMAT, BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS)
            self.outputText.append("Saving collected data...")
            row = [self.frameNumber, BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom,
                   ROLL, LOS[0], LOS[1],
                   angles['top'], angles['left'], angles['center'], angles['right'], angles['bottom']]
            self.dataCSV.writerow(row)  # <-- save frame data
            self.outputText.append(f"Blur:\ttop:{round(BLURtop, 4)}"
                                   f"\tleft:{round(BLURleft, 4)}"
                                   f"\tcenter:{round(BLURcenter, 4)}"
                                   f"\tright:{round(BLURright, 4)}"
                                   f"\tbottom:{round(BLURbottom, 4)}")
            self.outputText.append(f"Line-Of-Sight:\thorizontal:{round(LOS[0] * 1000, 2)} mm"
                                   f"\tvertical:{round(LOS[1] * 1000, 2)} mm")
            self.outputText.append(f"Horizontal Roll:\t{round(np.deg2rad(np.abs(ROLL[0])) * 1000, 2)} mrad")

        if message == "Move Message":
            self.outputText.append("Moving Hexapod to the next position...")
            self.outputText.append(f"↑↑↑↑↑↑↑↑↑↑↑↑ Frame #{self.frameNumber} ↑↑↑↑↑↑↑↑↑↑↑↑")

    def placeholder5(self):
        pass

    def placeholder6(self):
        pass

    def placeholder7(self):
        pass

    def Calib1(self, axis, axisStepSize):  # <--- no idea at the moment, need idan

        pass

    # ------------------------------------------------------------------------------------------------------------------#
    # def Calib2(self, zStepSize, xyStepSize):
    #     '''draft - this should be adapted as a research tool of the FPA to study the change of the blur with each axis
    #     instead of a calibration tool , since it uses a large amount of data which will take time to gather
    #     '''
    #     # we choose to prioritize the center value, but we must meet the
    #     # minimum blur critiria for all the spots, so we will stop on the position that
    #     # gives the highest center value with edges that above the min blur value
    #     # this logic can and should be modified according to the finding in practice
    #     # inputs for coarse or fine calibration:
    #         # Calib2Coarse(self, zStepSize = zAxisStepCoarse, xyStepSize = self.pixelSize * 5)
    #         # Calib2Fine(self,   zStepSize = zAxisStepFine,   xyStepSize = self.pixelSize)
    #     curPos = self.C887.qPOS()
    #     pos = self.ConvertPositionToArray(curPos) # <-- this is the position after initCalib, thus on LOS
    #     zSteps = 21
    #     xySteps = 2 * LOSTolerance / 5 + 1 # this works, don't question
    #     data = np.zeros((xySteps, xySteps, zSteps)) # <--- 9X9X21X5 values to collect
    #     bestPositon = None
    #     bestCenterBlur = 0
    #     # bestAverageEdgeBlur = 0 # <-- maybe in the future
    #     for x in range(-xySteps, xySteps + 1): # left->right
    #         for y in range(xySteps, -xySteps - 1, -1): # top->bottom
    #             for z in range(-zSteps // 2, zSteps // 2 + 1):  # down->up
    #                 Hexapod.MoveAbsolute(self.C887, np.array(pos + [x * xyStepSize,
    #                                                                 y * xyStepSize,
    #                                                                 z * zStepSize,
    #                                                                 0, 0, 0]))
    #                 imgMAT = self.Grab()
    #                 [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS] = Calc.CalcDetectorAll(imgMAT)
    #                 angles = Calc.CalcCollimatorsAngles(imgMAT, False)
    #                 self.UpdateGUI("Calc Plot Save Message", imgMAT,
    #                                [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS, angles])
    #                 curPos = self.C887.qPOS()
    #                 pos = self.ConvertPositionToArray(curPos)
    #                 data[x + xySteps][y + xySteps][z + zSteps // 2] = [BLURtop,
    #                                                                    BLURleft,
    #                                                                    BLURcenter,
    #                                                                    BLURright,
    #                                                                    BLURbottom,
    #                                                                    pos]
    #
    #             dataTable = np.transpose(data[x + xySteps][y + xySteps])
    #             bestCenterBlurZ = np.argmax(dataTable[2])                                          # <-- center oriented
    #             bestBalancedBlurZ = np.argmin(np.std(dataTable, axis=0))                           # <-- all oriented
    #             if (np.min(dataTable[0:4, bestBalancedBlurZ]) > BlurFloor) or\
    #                (np.min(dataTable[0:4, bestCenterBlurZ]) > BlurFloor):
    #                 if (bestBalancedBlurZ > bestCenterBlurZ):
    #                     direction = 1
    #                 else:
    #                     direction = -1
    #                 # move from the best center to the best balanced state that favors the center
    #                 for z in range(bestCenterBlurZ, bestBalancedBlurZ, direction):
    #                     if (np.min(dataTable[0:4, z]) > BlurFloor):
    #                         if (dataTable[2][z] > bestCenterBlur):
    #                             bestCenterBlur = dataTable[2][z]
    #                             bestPositon = dataTable[5][z]
    #                         break
    #                 else:
    #                     bestCenterBlur = dataTable[2][bestBalancedBlurZ]
    #                     bestPositon = dataTable[5][bestBalancedBlurZ]
    #
    #     return bestCenterBlur, bestPositon
    # ------------------------------------------------------------------------------------------------------------------#
    def Calib3(self, iterAmount=2):  # "Elsec" alg - we ignore the edge blurs as a condition
        # correct the LOS (and ROLL, why not) that may changed after Tilt in InitClaib
        pos = self.ConvertPositionToArray(self.C887.qPOS())
        imgMAT = self.Grab()
        [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS] = Calc.CalcDetectorAll(imgMAT)
        angles = Calc.CalcCollimatorsAngles(imgMAT, False)
        self.UpdateGUI("Calc Plot Save Message", imgMAT,
                       [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS, angles])
        Hexapod.MoveAbsolute(self.C887, np.array(pos + [LOS[0] * 1000, LOS[1] * 1000, 0, 0, 0, ROLL[0]]))
        i = 0
        catch = 0
        while (i < iterAmount):
            # maximize the center blur
            self.Focus(zAxisStepFine)
            # level the edges for balance and maximal blur with respect to the given z height
            self.Tilt(angleStepsFine)
            # take image after tilt adjustment to check if the LOS is still in spec
            imgMAT = self.Grab()
            [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS] = Calc.CalcDetectorAll(imgMAT)
            angles = Calc.CalcCollimatorsAngles(imgMAT, False)
            self.UpdateGUI("Calc Plot Save Message", imgMAT,
                           [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS, angles])
            if not LOS[5]:  # if due to the tilt adjustment the LOS fall off the tolerance, move back to center of FPA
                pos = self.ConvertPositionToArray(self.C887.qPOS())
                Hexapod.MoveAbsolute(self.C887, np.array(pos + [LOS[0] * 1000, LOS[1] * 1000, 0, 0, 0, ROLL]))
                i = -1
                catch += 1
            else:
                prevCenterBlur = BLURcenter
                # move to center of the FPA to check if it improves the blur in the center
                # if not we will return to the previous position
                pos = self.ConvertPositionToArray(self.C887.qPOS())
                Hexapod.MoveAbsolute(self.C887, np.array(pos + [LOS[0] * 1000, LOS[1] * 1000, 0, 0, 0, ROLL]))
                if prevCenterBlur > BLURcenter:
                    Hexapod.MoveAbsolute(self.C887, np.array(pos))
            i += 1
            if catch > maxIterations:
                raise Exception("Too many iterations")
        # hopefully we converged into a good position - the last position we been at
        bestPositon = self.ConvertPositionToArray(self.C887.qPOS())

        return bestPositon

    def Calib4(self):  # healthy logic using z axis and tilt optimazation
        pass
        '''
        need idan !! 
        '''
        pos = self.ConvertPositionToArray(self.C887.qPOS())
        Nsteps = 11
        zDict = {}
        for Z in range(-Nsteps // 2, Nsteps // 2 + 1):
            # this makes sure that the movement in the Z axis is not affected by the UV changes due to Tilt
            Hexapod.MoveAbsolute(self.C887, np.array(pos + [0, 0, Z * zAxisStepFine, 0, 0, 0]))  # XYZUVW
            # optimaize the UV axes for max edges' blur
            self.Tilt(angleStepsFine)
            imgMAT = self.Grab()
            [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS] = Calc.CalcDetectorAll(imgMAT)
            angles = Calc.CalcCollimatorsAngles(imgMAT, False)
            self.UpdateGUI("Calc Plot Save Message", imgMAT,
                           [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS, angles])
            qFactor = BLURcenter - np.sum(np.abs(BLURcenter - BLURtop),
                                          np.abs(BLURcenter - BLURleft),
                                          np.abs(BLURcenter - BLURright),
                                          np.abs(BLURcenter - BLURbottom))
            zDict[Z] = [qFactor, self.ConvertPositionToArray(self.C887.qPOS())]
        bestZ = max(zDict.items(), key=lambda k: k[0])
        bestPositon = zDict[bestZ][1]
        Hexapod.MoveAbsolute(self.C887, bestPositon)

        return bestPositon

    def Calib5(self, zStepSize, xyStepSize):  # an optimized version of calib2 that needs to take less time
        # we choose to prioritize the center value, but we must meet the
        # minimum blur criteria for all the spots, so we will stop on the position that
        # gives the highest center value with edges that above the min blur value
        # this logic can and should be modified according to the finding in practice
        # there is no tilt adjustment

        # inputs for coarse or fine calibration:
        # Calib2Coarse(self, zStepSize = zAxisStepCoarse, xyStepSize = self.pixelSize * 5)
        # Calib2Fine(self,   zStepSize = zAxisStepFine,   xyStepSize = self.pixelSize)
        curPos = self.C887.qPOS()
        pos = self.ConvertPositionToArray(curPos)  # <-- this is the position after initCalib, thus on LOS
        zSteps = 11
        xySteps = 2 * LOSTolerance / 5 + 1  # this works, don't question -> = 9
        data = np.zeros((xySteps, xySteps, zSteps))  # <--- 9X9X11X6 values to collect
        bestPositon = None
        bestCenterBlur = 0
        for x in range(-xySteps // 2, xySteps // 2 + 1):  # left->right
            for y in range(-xySteps // 2, xySteps // 2 + 1):  # bottom->top
                for z in range(-zSteps // 2, zSteps // 2 + 1):  # down->up
                    Hexapod.MoveAbsolute(self.C887, np.array(pos + [x * xyStepSize,
                                                                    y * xyStepSize,
                                                                    z * zStepSize,
                                                                    0, 0, 0]))
                    imgMAT = self.Grab()
                    [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS] = Calc.CalcDetectorAll(imgMAT)
                    angles = Calc.CalcCollimatorsAngles(imgMAT, False)
                    self.UpdateGUI("Calc Plot Save Message", imgMAT,
                                   [BLURtop, BLURleft, BLURcenter, BLURright, BLURbottom, ROLL, LOS, angles])
                    curPos = self.C887.qPOS()
                    pos = self.ConvertPositionToArray(curPos)
                    data[x + xySteps // 2][y + xySteps // 2][z + zSteps // 2] = [BLURtop,
                                                                                 BLURleft,
                                                                                 BLURcenter,
                                                                                 BLURright,
                                                                                 BLURbottom,
                                                                                 pos]

                dataTable = np.transpose(data[x + xySteps][y + xySteps])
                bestCenterBlurZ = np.argmax(dataTable[2, :])  # <-- center oriented
                bestBalancedBlurZ = np.argmin(np.std(dataTable[0:4, :], axis=0))  # <-- all oriented
                if (np.min(dataTable[0:4, bestBalancedBlurZ]) > BlurFloor) or \
                        (np.min(dataTable[0:4, bestCenterBlurZ]) > BlurFloor):
                    if bestBalancedBlurZ > bestCenterBlurZ:
                        direction = 1
                    else:
                        direction = -1
                    # move from the best center to the best balanced state that favors the center
                    for z in range(bestCenterBlurZ, bestBalancedBlurZ, direction):
                        if np.min(dataTable[0:4, z]) > BlurFloor:
                            if dataTable[2][z] > bestCenterBlur:
                                bestCenterBlur = dataTable[2][z]
                                bestPositon = dataTable[5][z]
                            break
                    else:
                        bestCenterBlur = dataTable[2][bestBalancedBlurZ]
                        bestPositon = dataTable[5][bestBalancedBlurZ]

        return bestPositon
