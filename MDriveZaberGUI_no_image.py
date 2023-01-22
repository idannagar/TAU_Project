from PyQt5.QtCore import Qt, QSize, QCoreApplication
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QWidget,
    QSizePolicy,
    QComboBox,
)
import serial
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

import ImageProcess as ImPros
import Calculations as Calc
import Collimators as Colli
import FGCL_resource as FGCL
#----------------------------------------------------------------------------------------------------------------------#
############################# Defines #############################
WINDOWSIZE = (800, 300)

buttenSize = (65, 65)
fontSizeButtens = 24
fontSizeText = 12

baud = 9600
portH = "COM1"
portV = "?"

FIGSIZE = (12, 8)
DPI = 100

factor = 10 * 10**-6  # for 5um it will by 5 and for 10um it will be 10
conversionConst_00field = [0.159 * 10**3, 0.159 * 10**3]  # from [m] to [rad]
conversionConst_50field = [0.150 * 10**3, 0.188 * 10**3]  # from [m] to [rad]
conversionConst_60field = [0.182 * 10**3, 0.143 * 10**3]  # from [m] to [rad]
############################# Defines #############################
#----------------------------------------------------------------------------------------------------------------------#
class MdriveDevice():
    def __init__(self, name, port, baud):
        self.ser = serial.Serial(port=port,
                                 baudrate=baud,
                                 bytesize=serial.EIGHTBITS,
                                 timeout=1,
                                 write_timeout=1)
        self.name = name
        self.position = 0

        # parameters
        self.MS = 256
        self.HM = 2
        self.ratio = 51
        self.stepsPerRevolution = 200
        self.degPerMicrostep = round(360 / (self.MS * self.stepsPerRevolution), 3)
        self.microstepPerDeg = round((self.MS * self.stepsPerRevolution) / 360)
        # # safety bounds for later
        # degreeLimit = 5
        # maxBound = degreeLimit * degPerMicrostep
        # minBound = -degreeLimit * degPerMicrostep

        if self.ser.isOpen():
            print(f"Session with the {self.name} motor is open and active")
            # set motor to home position
            print(f"{self.name} motor is homing...")  # not actually working - need to replace with a MA to the proper location for the beginning of the calib of the table
            cmd = f'HM={self.HM} \r\n'
            self.ser.write(cmd.encode())
            # set microstep resolution
            cmd = f'MS={self.MS} \r\n'
            self.ser.write(cmd.encode())
            print(f"{self.name} motor is ready for operation")
        else:
            raise Exception(f"session problam with the \"{self.name}\" motor")
    #------------------------------------------------------------------------------------------------------------------#
    def MR(self, distance, type, direction):  # relative movement at the correction table
        if distance.isnumeric() or self.isFloat(distance):
            if type == 'Degrees':
                amount = round(float(distance) * self.ratio * self.microstepPerDeg) * direction
                cmd = f'MR {amount} \r\n'
                self.ser.write(cmd.encode())
            else:  # type == microsteps
                amount = int(distance) * self.ratio * self.microstepPerDeg * direction
                cmd = f'MR {amount} \r\n'
                self.ser.write(cmd.encode())
            self.position += amount  # update the postion of the motor
    #------------------------------------------------------------------------------------------------------------------#
    def MA(self, position, type, direction):  # absolute movement at the correction table
        if position.isnumeric() or self.isFloat(position):
            if type == 'Degrees':
                amount = round(float(position) * self.ratio * self.microstepPerDeg) * direction
                cmd = f'MA {amount} \r\n'
                self.ser.write(cmd.encode())
            else:  # type == microsteps
                amount = int(position) * self.ratio * self.microstepPerDeg * direction
                cmd = f'MA {amount} \r\n'
                self.ser.write(cmd.encode())
            self.position = amount  # update the postion of the motor
    #------------------------------------------------------------------------------------------------------------------#
    # def MV(self): # boolean flag to check if the motor is running
    #     cmd = 'PR MV^M \r\n'
    #     self.ser.write(cmd.encode())
    #     response = self.ser.read()
    #
    #     return response == '1' # if the motor is running, True will be returned
    #------------------------------------------------------------------------------------------------------------------#
    @staticmethod
    def isFloat(str):
        try:
            float(str)
            return True
        except ValueError:
            return False
#----------------------------------------------------------------------------------------------------------------------#
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setFixedSize(QSize(WINDOWSIZE[0], WINDOWSIZE[1]))
        self.setStyleSheet("QMainWindow {background:rgb(225, 225, 225)}")
        self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        # define the frame zone of the gui
        self.canvas = FigureCanvas(plt.figure(figsize=FIGSIZE, dpi=DPI, frameon=False))
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.updateGeometry()
        self.fig = self.canvas.figure
        self.fig.patch.set_visible(False)
        self.fig.tight_layout()
        # layout templates
        layoutUpLow = QVBoxLayout()
        layoutLeftRight = QHBoxLayout()
        layoutLeft = QVBoxLayout()
        layoutRight = QVBoxLayout()
        layoutButtensLeft = QGridLayout()
        layoutButtensRight = QGridLayout()
        layoutControlsCollimator = QVBoxLayout()
        layoutButtensCollimator = QGridLayout()
        # main layout constrator
        layoutUpLow.addWidget(self.canvas)
        layoutUpLow.addLayout(layoutLeftRight)
        #--------------------------------------------------------------------------------------------------------------#
        # left layout constractor
        layoutLeftRight.addStretch(0)
        layoutLeftRight.addLayout(layoutLeft)
        self.labelLeft = QLabel("Horizontal Mdrive")
        self.labelLeft.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.labelLeft.setAlignment(Qt.AlignCenter)
        self.labelLeft.setStyleSheet("font-weight: bold")
        self.labelLeft.setStyleSheet(f"font-size: {fontSizeText}pt")
        layoutLeft.addWidget(self.labelLeft)
        self.dropMenuMoveLeft = QComboBox()
        self.dropMenuMoveLeft.addItems(['MR', 'MA'])
        layoutLeft.addWidget(self.dropMenuMoveLeft)
        self.dropMenutypeLeft = QComboBox()
        self.dropMenutypeLeft.addItems(['Degrees', 'Steps'])
        layoutLeft.addWidget(self.dropMenutypeLeft)
        self.amountLeft = QLineEdit()
        layoutLeft.addWidget(self.amountLeft)
        self.buttenLL = QPushButton("↺")
        self.buttenLL.setStyleSheet("font-weight: bold")
        self.buttenLL.setStyleSheet(f"font-size: {fontSizeButtens}pt")
        self.buttenLL.setFixedSize(QSize(buttenSize[0], buttenSize[1]))
        self.buttenLR = QPushButton("↻")
        self.buttenLR.setStyleSheet("font-weight: bold")
        self.buttenLR.setStyleSheet(f"font-size: {fontSizeButtens}pt")
        self.buttenLR.setFixedSize(QSize(buttenSize[0], buttenSize[1]))
        layoutButtensLeft.addWidget(self.buttenLL, 0 ,0)
        layoutButtensLeft.addWidget(self.buttenLR, 0 ,1)
        layoutLeft.addLayout(layoutButtensLeft)
        #--------------------------------------------------------------------------------------------------------------#
        # right layout constractor
        layoutLeftRight.addLayout(layoutRight)
        self.labelCoolimator = QLabel("Vertical Mdrive")
        self.labelCoolimator.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.labelCoolimator.setAlignment(Qt.AlignCenter)
        self.labelCoolimator.setStyleSheet("font-weight: bold")
        self.labelCoolimator.setStyleSheet(f"font-size: {fontSizeText}pt")
        layoutRight.addWidget(self.labelCoolimator)
        self.dropMenuMoveRight = QComboBox()
        self.dropMenuMoveRight.addItems(['MR', 'MA'])
        layoutRight.addWidget(self.dropMenuMoveRight)
        self.dropMenuTypeRight = QComboBox()
        self.dropMenuTypeRight.addItems(['Degrees', 'Steps'])
        layoutRight.addWidget(self.dropMenuTypeRight)
        self.amountRight = QLineEdit()
        layoutRight.addWidget(self.amountRight)
        self.buttenRL = QPushButton("↺")
        self.buttenRL.setStyleSheet("font-weight: bold")
        self.buttenRL.setStyleSheet("font-size: 24pt")
        self.buttenRL.setFixedSize(QSize(buttenSize[0], buttenSize[1]))
        self.buttenRR = QPushButton("↻")
        self.buttenRR.setStyleSheet("font-weight: bold")
        self.buttenRR.setStyleSheet("font-size: 24pt")
        self.buttenRR.setFixedSize(QSize(buttenSize[0], buttenSize[1]))
        layoutButtensRight.addWidget(self.buttenRL, 0, 0)
        layoutButtensRight.addWidget(self.buttenRR, 0, 1)
        layoutRight.addLayout(layoutButtensRight)
        #--------------------------------------------------------------------------------------------------------------#
        # collimators control layout constractor
        layoutLeftRight.addLayout(layoutControlsCollimator)
        self.labelCoolimator = QLabel("Collimator Controls")
        self.labelCoolimator.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.labelCoolimator.setAlignment(Qt.AlignCenter)
        self.labelCoolimator.setStyleSheet("font-weight: bold")
        self.labelCoolimator.setStyleSheet(f"font-size: {fontSizeText}pt")
        layoutControlsCollimator.addWidget(self.labelCoolimator)
        self.dropMenuSelectCollimator = QComboBox()
        self.dropMenuSelectCollimator.addItems(['top', 'left', 'center', 'right', 'bottom'])
        layoutButtensCollimator.addWidget(self.dropMenuSelectCollimator, 1, 0)
        self.dropMenuSelectAmount = QComboBox()
        self.dropMenuSelectAmount.addItems(['1 pixel', '½ pixel', '⅒ pixel', 'radians'])
        layoutButtensCollimator.addWidget(self.dropMenuSelectAmount, 2, 0)
        self.amountRadians = QLineEdit()
        layoutButtensCollimator.addWidget(self.amountRadians, 3, 0)
        self.buttenUP = QPushButton("")
        self.buttenUP.setStyleSheet("font-weight: bold")
        self.buttenUP.setStyleSheet("font-size: 16pt")
        self.buttenUP.setFixedSize(QSize(buttenSize[0] - 20, buttenSize[1] - 20))
        self.buttenLEFT = QPushButton("")
        self.buttenLEFT.setStyleSheet("font-weight: bold")
        self.buttenLEFT.setStyleSheet("font-size: 16pt")
        self.buttenLEFT.setFixedSize(QSize(buttenSize[0] - 20, buttenSize[1] - 20))
        self.buttenRIGHT = QPushButton("")
        self.buttenRIGHT.setStyleSheet("font-weight: bold")
        self.buttenRIGHT.setStyleSheet("font-size: 16pt")
        self.buttenRIGHT.setFixedSize(QSize(buttenSize[0] - 20, buttenSize[1] - 20))
        self.buttenDOWN = QPushButton("")
        self.buttenDOWN.setStyleSheet("font-weight: bold")
        self.buttenDOWN.setStyleSheet("font-size: 16pt")
        self.buttenDOWN.setFixedSize(QSize(buttenSize[0] - 20, buttenSize[1] - 20))
        self.buttenHOME = QPushButton("")  #   
        self.buttenHOME.setStyleSheet("font-weight: bold")
        self.buttenHOME.setStyleSheet("font-size: 16pt")

        self.buttenCENTER = QPushButton("")
        self.buttenCENTER.setStyleSheet("font-weight: bold")
        self.buttenCENTER.setStyleSheet("font-size: 16pt")
        self.buttenCENTER.setFixedSize(QSize(buttenSize[0] - 20, buttenSize[1] - 20))

        self.buttenHOME.setFixedSize(QSize(buttenSize[0] - 20, buttenSize[1] - 20))
        layoutButtensCollimator.addWidget(self.buttenUP, 1, 2)
        layoutButtensCollimator.addWidget(self.buttenLEFT, 2, 1)
        layoutButtensCollimator.addWidget(self.buttenRIGHT, 2, 4)
        layoutButtensCollimator.addWidget(self.buttenDOWN, 3, 2)
        layoutButtensCollimator.addWidget(self.buttenHOME, 2, 2)
        layoutButtensCollimator.addWidget(self.buttenCENTER, 3, 4)
        layoutControlsCollimator.addLayout(layoutButtensCollimator)
        layoutLeftRight.addStretch(0)
        #--------------------------------------------------------------------------------------------------------------#
        self.buttenExit = QPushButton("EXIT")
        self.buttenExit.setStyleSheet("font-weight: bold")
        self.buttenExit.setStyleSheet("font-size: 16pt")
        self.buttenExit.setStyleSheet("background-color:rgb(255, 87, 69)")  # !!!!
        self.buttenExit.setFixedSize(QSize(280, 50))
        layoutUpLow.addWidget(self.buttenExit, alignment=Qt.AlignHCenter)
        #--------------------------------------------------------------------------------------------------------------#
        # drop menus functionality assignment
        self.dropMenuMoveLeftChoise = 'MR'
        self.dropMenuMoveLeft.activated.connect(self.dropMenuMoveLeftUpdate)
        self.dropMenuMoveRightChoise = 'MR'
        self.dropMenuMoveRight.activated.connect(self.dropMenuMoveRightUpdate)
        self.dropMenutypeLeftChoise = 'Degrees'
        self.dropMenutypeLeft.activated.connect(self.dropMenutypeLeftUpdate)
        self.dropMenutypeRightChoise = 'Degrees'
        self.dropMenuTypeRight.activated.connect(self.dropMenutypeRightUpdate)
        self.dropMenuSelectCollimatorChoise = 'top'
        self.dropMenuSelectCollimator.activated.connect(self.dropMenuSelectCollimatorUpdate)
        self.dropMenuSelectAmountChoise = '1 pixel'
        self.dropMenuSelectAmount.activated.connect(self.dropMenuSelectAmountUpdate)
        #--------------------------------------------------------------------------------------------------------------#
        # buttens functionality assignment
        # left panel buttens
        self.buttenLL.clicked.connect(self.LLPushed)
        self.buttenLR.clicked.connect(self.LRPushed)
        # right panel buttens
        self.buttenRL.clicked.connect(self.RLPushed)
        self.buttenRR.clicked.connect(self.RRPushed)
        # exit butten
        self.buttenExit.clicked.connect(self.ExitPushed)
        # collimator panel buttens
        self.buttenUP.clicked.connect(self.UPPushed)
        self.buttenLEFT.clicked.connect(self.LEFTPushed)
        self.buttenRIGHT.clicked.connect(self.RIGHTPushed)
        self.buttenDOWN.clicked.connect(self.DOWNPushed)
        self.buttenHOME.clicked.connect(self.HOMEPushed)
        self.buttenCENTER.clicked.connect(self.CENTERPushed)
        #--------------------------------------------------------------------------------------------------------------#
        # open connection with frame grabber and aqcuire the first frame before movement for reference
        self.vidobjPath = FGCL.ConnectFGandCAM()
        FGCL.OpenLiveVideo(self.vidobjPath)
        #--------------------------------------------------------------------------------------------------------------#
        # main window constractor
        widget = QWidget()
        widget.setLayout(layoutUpLow)
        self.setCentralWidget(widget)
        # self.UpdateFrame()  # need to check if possble to put in a "while true" and remove from all other positions
        #--------------------------------------------------------------------------------------------------------------#
        # build the Mdrive objects
        self.HMdrive = MdriveDevice("Horizontal Mdrive", portH, baud)
        # self.VMdrive = MdriveDevice("Vertical Mdrive", portV, baud)
        #--------------------------------------------------------------------------------------------------------------#
        # build the collimators object and connect to all
        self.connection, self.dictCollimators = Colli.ConnectAndConfigure()
    #------------------------------------------------------------------------------------------------------------------#
    def dropMenuMoveLeftUpdate(self):
        self.dropMenuMoveLeftChoise = self.dropMenuMoveLeft.currentText()
    #------------------------------------------------------------------------------------------------------------------#
    def dropMenuMoveRightUpdate(self):
        self.dropMenuMoveRightChoise = self.dropMenuMoveRight.currentText()
    #------------------------------------------------------------------------------------------------------------------#
    def dropMenutypeLeftUpdate(self):
        self.dropMenutypeLeftChoise = self.dropMenutypeLeft.currentText()
    #------------------------------------------------------------------------------------------------------------------#
    def dropMenutypeRightUpdate(self):
        self.dropMenutypeRightChoise = self.dropMenuTypeRight.currentText()
    #------------------------------------------------------------------------------------------------------------------#
    def LLPushed(self): # rotate CCW the horizontal motor
        self.buttenLL.setEnabled(False)
        if self.dropMenuMoveLeftChoise == 'MR':
            print(f"MR {self.dropMenutypeLeftChoise} -{self.amountLeft.text()}")
            self.HMdrive.MR(self.amountLeft.text(), self.dropMenutypeLeftChoise, -1)
        else: # self.dropMenutypeLeft == 'MA'
            print(f"MA {self.dropMenutypeLeftChoise} -{self.amountLeft.text()}")
            self.HMdrive.MA(self.amountLeft.text(), self.dropMenutypeLeftChoise, -1)
        self.buttenLL.setEnabled(True)
        # self.UpdateFrame()
    #------------------------------------------------------------------------------------------------------------------#
    def LRPushed(self): # rotate CW the horizontal motor
        self.buttenLR.setEnabled(False)
        if self.dropMenuMoveLeftChoise == 'MR':
            print(f"MR {self.dropMenutypeLeftChoise} {self.amountLeft.text()}")
            self.HMdrive.MR(self.amountLeft.text(), self.dropMenutypeLeftChoise, 1)
        else:  # self.dropMenutypeLeft == 'MA'
            print(f"MA {self.dropMenutypeLeftChoise} {self.amountLeft.text()}")
            self.HMdrive.MA(self.amountLeft.text(), self.dropMenutypeLeftChoise, 1)
        self.buttenLR.setEnabled(True)
        # self.UpdateFrame()
    #------------------------------------------------------------------------------------------------------------------#
    def RLPushed(self): # rotate CCW the vertical motor
        self.buttenRL.setEnabled(False)
        if self.dropMenuMoveRightChoise == 'MR':
            print(f"MR {self.dropMenutypeRightChoise} -{self.amountRight.text()}")
            # self.VMdrive.MR(self.amountRight.text(), self.dropMenutypeRightChoise, -1)
        else:  # self.dropMenutypeLeft == 'MA'
            print(f"MA {self.dropMenutypeRightChoise} -{self.amountRight.text()}")
            # self.VMdrive.MA(self.amountRight.text(), self.dropMenutypeRightChoise, -1)
        self.buttenRL.setEnabled(True)
        # self.UpdateFrame()
    #------------------------------------------------------------------------------------------------------------------#
    def RRPushed(self): # rotate CW the vertical motor
        self.buttenRR.setEnabled(False)
        if self.dropMenuMoveRightChoise == 'MR':
            print(f"MR {self.dropMenutypeRightChoise} {self.amountRight.text()}")
            # self.VMdrive.MR(self.amountRight.text(), self.dropMenutypeRightChoise, 1)
        else:  # self.dropMenutypeLeft == 'MA'
            print(f"MA {self.dropMenutypeRightChoise} {self.amountRight.text()}")
            # self.VMdrive.MA(self.amountRight.text(), self.dropMenutypeRightChoise, 1)
        self.buttenRR.setEnabled(True)
        # self.UpdateFrame()
    #------------------------------------------------------------------------------------------------------------------#
    def ExitPushed(self): #close motors' serial sessions and close the gui
        self.HMdrive.ser.close()
        # self.VMdrive.ser.close()
        Colli.DisconnectAndReset(self.connection)
        FGCL.CloseLiveVideo(self.vidobjPath)
        self.close()
    #------------------------------------------------------------------------------------------------------------------#
    def dropMenuSelectCollimatorUpdate(self):
        self.dropMenuSelectCollimatorChoise = self.dropMenuSelectCollimator.currentText()
    #------------------------------------------------------------------------------------------------------------------#
    def dropMenuSelectAmountUpdate(self):
        self.dropMenuSelectAmountChoise = self.dropMenuSelectAmount.currentText()
    #------------------------------------------------------------------------------------------------------------------#
    def UPPushed(self):
        stepSelection = self.dropMenuSelectAmountChoise
        if stepSelection == '1 pixel':
            stepSize = 1 * factor
        if stepSelection == '½ pixel':
            stepSize = 0.5 * factor
        if stepSelection == '⅒ pixel':
            stepSize = 0.1 * factor
        if stepSelection == 'radians':
            stepSize = float(self.amountRadians.text())
        tag = self.dropMenuSelectCollimatorChoise
        currentCollimator = self.dictCollimators[tag]
        if tag == 'top':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_50field[1])
            deltas = (0, angleDegree)  # move positive phi
            Colli.MoveRelative(currentCollimator, deltas)
        if tag == 'left':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_60field[1])
            deltas = (-angleDegree, 0)  # move negative theta
            Colli.MoveRelative(currentCollimator, deltas)
        if tag == 'center':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_00field[1])
            deltas = (0, angleDegree)  # move negative phi
            Colli.MoveRelative(currentCollimator, deltas)
        if tag == 'right':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_60field[1])
            deltas = (-angleDegree, 0)  # move positive phi
            Colli.MoveRelative(currentCollimator, deltas)
        if tag == 'bottom':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_50field[1])
            deltas = (0, angleDegree)  # move negative phi
            Colli.MoveRelative(currentCollimator, deltas)
        #self.UpdateFrame()
    #------------------------------------------------------------------------------------------------------------------#
    def LEFTPushed(self):
        stepSelection = self.dropMenuSelectAmountChoise
        if stepSelection == '1 pixel':
            stepSize = 1 * factor
        if stepSelection == '½ pixel':
            stepSize = 0.5 * factor
        if stepSelection == '⅒ pixel':
            stepSize = 0.1 * factor
        if stepSelection == 'radians':
            stepSize = float(self.amountRadians.text())
        tag = self.dropMenuSelectCollimatorChoise
        currentCollimator = self.dictCollimators[tag]
        if tag == 'top':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_50field[1])
            deltas = (-angleDegree, 0)
            Colli.MoveRelative(currentCollimator, deltas)
        if tag == 'left':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_60field[1])
            deltas = (0, -angleDegree)
            Colli.MoveRelative(currentCollimator, deltas)
        if tag == 'center':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_00field[1])
            deltas = (-angleDegree, 0)
            Colli.MoveRelative(currentCollimator, deltas)
        if tag == 'right':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_60field[1])
            deltas = (0, -angleDegree)
            Colli.MoveRelative(currentCollimator, deltas)
        if tag == 'bottom':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_50field[1])
            deltas = (-angleDegree, 0)
            Colli.MoveRelative(currentCollimator, deltas)
        #self.UpdateFrame()
    #------------------------------------------------------------------------------------------------------------------#
    def RIGHTPushed(self):
        stepSelection = self.dropMenuSelectAmountChoise
        if stepSelection == '1 pixel':
            stepSize = 1 * factor
        if stepSelection == '½ pixel':
            stepSize = 0.5 * factor
        if stepSelection == '⅒ pixel':
            stepSize = 0.1 * factor
        if stepSelection == 'radians':
            stepSize = float(self.amountRadians.text())
        tag = self.dropMenuSelectCollimatorChoise
        currentCollimator = self.dictCollimators[tag]
        if tag == 'top':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_50field[1])
            deltas = (angleDegree, 0)
            Colli.MoveRelative(currentCollimator, deltas)
        if tag == 'left':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_60field[1])
            deltas = (0, angleDegree)
            Colli.MoveRelative(currentCollimator, deltas)
        if tag == 'center':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_00field[1])
            deltas = (angleDegree, 0)
            Colli.MoveRelative(currentCollimator, deltas)
        if tag == 'right':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_60field[1])
            deltas = (0, angleDegree)
            Colli.MoveRelative(currentCollimator, deltas)
        if tag == 'bottom':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_50field[1])
            deltas = (angleDegree, 0)
            Colli.MoveRelative(currentCollimator, deltas)
        #self.UpdateFrame()
    #------------------------------------------------------------------------------------------------------------------#
    def DOWNPushed(self):
        stepSelection = self.dropMenuSelectAmountChoise
        if stepSelection == '1 pixel':
            stepSize = 1 * factor
        if stepSelection == '½ pixel':
            stepSize = 0.5 * factor
        if stepSelection == '⅒ pixel':
            stepSize = 0.1 * factor
        if stepSelection == 'radians':
            stepSize = float(self.amountRadians.text())
        tag = self.dropMenuSelectCollimatorChoise
        currentCollimator = self.dictCollimators[tag]
        if tag == 'top':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_50field[1])
            deltas = (0, -angleDegree)  # move positive phi
            Colli.MoveRelative(currentCollimator, deltas)
        if tag == 'left':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_60field[1])
            deltas = (angleDegree, 0)  # move negative theta
            Colli.MoveRelative(currentCollimator, deltas)
        if tag == 'center':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_00field[1])
            deltas = (0, -angleDegree)  # move negative phi
            Colli.MoveRelative(currentCollimator, deltas)
        if tag == 'right':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_60field[1])
            deltas = (angleDegree, 0)  # move positive phi
            Colli.MoveRelative(currentCollimator, deltas)
        if tag == 'bottom':
            if stepSelection == 'radians':
                angleDegree = np.rad2deg(stepSize)
            else:
                angleDegree = np.rad2deg(stepSize * conversionConst_50field[1])
            deltas = (0, -angleDegree)  # move negative phi
            Colli.MoveRelative(currentCollimator, deltas)
        #self.UpdateFrame()
    #------------------------------------------------------------------------------------------------------------------#
    def HOMEPushed(self):
        tag = self.dropMenuSelectCollimatorChoise
        currentCollimator = self.dictCollimators[tag]
        Colli.MoveToStart(currentCollimator)
        #self.UpdateFrame()
    #------------------------------------------------------------------------------------------------------------------#
    def CENTERPushed(self):
        tag = self.dropMenuSelectCollimatorChoise
        currentCollimator = self.dictCollimators[tag]

        testpic = FGCL.GrabIMG(self.vidobjPath)
        imgMAT = np.array(testpic)
        refMAT = np.array(self.refpic)
        replacement = np.median(imgMAT)

        top_N = 8
        arr = refMAT
        idxMAX = np.column_stack(np.unravel_index(np.argpartition(arr, arr.size - top_N, axis=None)[-top_N:], arr.shape))
        idxMIN = np.column_stack(np.unravel_index(np.argpartition(arr, top_N, axis=None)[:top_N], arr.shape))
        mask = np.zeros(arr.shape, dtype=bool)
        mask[idxMAX[:, 0], idxMAX[:, 1]] = True
        mask[idxMIN[:, 0], idxMIN[:, 1]] = True
        imgMAT[mask] = replacement

        dictAngles = Calc.CalcCollimatorsAngles(imgMAT, False)
        Colli.MoveRelative(currentCollimator, tuple(-angle for angle in dictAngles[tag]))
        # Colli.MoveRelative(currentCollimator, dictAngles[tag])

        self.UpdateFrame()
    #------------------------------------------------------------------------------------------------------------------#
    def Plot(self, imgMAT):
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
        im = ax.imshow(imgMAT, cmap='gray')
        ax.axis('on')
        spotsDict = ImPros.FindSpotsCenters(imgMAT)
        # mark with circles the colomators' spots
        for inds in spotsDict.values():
            circle = plt.Circle((inds[1], inds[0]), 20, edgecolor='r', fill=False)
            plt.gca().add_patch(circle)
        axs = []
        for nn, (x, y) in enumerate([(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)]):
            ax = self.fig.add_subplot(GSright[x, y])
            if nn == 0:
                mat = self.CropRegion(topMAT)
                ax.imshow(mat, cmap='gray')
                plt.title('Blur=' + str(round(self.CalcBlur(mat), 4)), fontsize=10)
                plt.xlabel('Pixel ' + str((spotsDict['top'][1], spotsDict['top'][0])))
                ax.axes.xaxis.set_ticks([])
                ax.axes.yaxis.set_ticks([])
            if nn == 1:
                mat = self.CropRegion(leftMAT)
                ax.imshow(mat, cmap='gray')
                plt.title('Blur=' + str(round(self.CalcBlur(mat), 4)), fontsize=10)
                plt.xlabel('Pixel ' + str((spotsDict['left'][1], spotsDict['left'][0])))
                ax.axes.xaxis.set_ticks([])
                ax.axes.yaxis.set_ticks([])
            if nn == 2:
                mat = self.CropRegion(centerMAT)
                ax.imshow(mat, cmap='gray')
                plt.title('Blur=' + str(round(self.CalcBlur(mat), 4)), fontsize=10)
                plt.xlabel('Pixel ' + str((spotsDict['center'][1], spotsDict['center'][0])))
                ax.axes.xaxis.set_ticks([])
                ax.axes.yaxis.set_ticks([])
            if nn == 3:
                mat = self.CropRegion(rightMAT)
                ax.imshow(mat, cmap='gray')
                plt.title('Blur=' + str(round(self.CalcBlur(mat), 4)), fontsize=10)
                plt.xlabel('Pixel ' + str((spotsDict['right'][1], spotsDict['right'][0])))
                ax.axes.xaxis.set_ticks([])
                ax.axes.yaxis.set_ticks([])
            if nn == 4:
                mat = self.CropRegion(bottomMAT)
                ax.imshow(mat, cmap='gray')
                plt.title('Blur=' + str(round(self.CalcBlur(mat), 4)), fontsize=10)
                plt.xlabel('Pixel ' + str((spotsDict['bottom'][1], spotsDict['bottom'][0])))
                ax.axes.xaxis.set_ticks([])
                ax.axes.yaxis.set_ticks([])
            axs += [ax]
        plt.subplots_adjust(wspace=0.15, hspace=-0.15)
        # self.fig.tight_layout()  # meh..
        plt.colorbar(im, ax=axs)
        # draw and refresh the figure on the canvas
        self.canvas.draw()
        QApplication.processEvents()  # refreshes the drawing for each plot
    #------------------------------------------------------------------------------------------------------------------#
    def UpdateFrame(self):
        testpic = FGCL.GrabIMG(self.vidobjPath, enableNUC=True)
        imgMAT = np.array(testpic)
        # refMAT = np.array(self.refpic)
        # replacement = np.median(imgMAT)
        #
        # top_N = 8
        # arr = refMAT
        # idxMAX = np.column_stack(np.unravel_index(np.argpartition(arr, arr.size - top_N, axis=None)[-top_N:], arr.shape))
        # idxMIN = np.column_stack(np.unravel_index(np.argpartition(arr, top_N, axis=None)[:top_N], arr.shape))
        # mask = np.zeros(arr.shape, dtype=bool)
        # mask[idxMAX[:, 0], idxMAX[:, 1]] = True
        # mask[idxMIN[:, 0], idxMIN[:, 1]] = True
        # imgMAT[mask] = replacement

        self.Plot(imgMAT)

    #------------------------------------------------------------------------------------------------------------------#
    @staticmethod
    def CropRegion(pxMAT):
        I = np.where(pxMAT == np.amax(pxMAT))
        inds = list(set(zip(I[0], I[1])))
        radius = 7

        return pxMAT[inds[0][0] - radius:inds[0][0] + radius + 1,
                      inds[0][1] - radius:inds[0][1] + radius + 1]
    #------------------------------------------------------------------------------------------------------------------#
    @staticmethod
    def CalcBlur(pxMAT):
        [pxH, pxW] = pxMAT.shape
        center = pxH // 2
        AC = 1
        AB = 24
        AT = 9
        SC = pxMAT[center, center]
        SB = np.sum(pxMAT[center - 3:center + 4, center - 3:center + 4])\
           - np.sum(pxMAT[center - 2:center + 3, center - 2:center + 3])
        ST = np.sum(pxMAT[center - 1:center + 2, center - 1:center + 2])
        return (SC - AC / AB * SB) / (ST - AT / AB * SB)
    #------------------------------------------------------------------------------------------------------------------#
    @staticmethod
    def plsceholder():
        pass
#----------------------------------------------------------------------------------------------------------------------#
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    app.exec()
#----------------------------------------------------------------------------------------------------------------------#