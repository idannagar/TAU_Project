import KYFGLib
from KYFGLib import *
# ----------------------------------------------------------------------------------------------------------------------#
import numpy as np
import matplotlib.pyplot as plt
import ctypes


# ----------------------------------------------------------------------------------------------------------------------#
############################# Callback Detection #############################
def Device_event_callback_func(userContext, event):
    if (isinstance(event, KYDEVICE_EVENT_CAMERA_CONNECTION_LOST) == True):
        print("KYDEVICE_EVENT_CAMERA_CONNECTION_LOST_ID event recognized")
        print("event_id: " + str(event.deviceEvent.eventId))
        print("cam_handle: " + format(event.camHandle.get(), '02x'))
        print("device_link: " + str(event.iDeviceLink))
        print("camera_link: " + str(event.iCameraLink))
    elif (isinstance(event, KYDEVICE_EVENT_CAMERA_START_REQUEST) == True):
        print("KYDEVICE_EVENT_CAMERA_START_REQUEST event recognized")
    else:
        print("Unknown event recognized")


############################# Callback Detection #############################
# ----------------------------------------------------------------------------------------------------------------------#
############################# Callback Function #############################
def Stream_callback_func(buffHandle, userContext):
    totalFrames = 0
    buffSize = 0
    buffIndex = 0
    buffData = 0

    if (buffHandle == 0):
        Stream_callback_func.copyingDataFlag = 0
        return

    (status, totalFrames) = KYFG_GetGrabberValueInt(buffHandle, "RXFrameCounter")
    (buffSize,) = KYFG_StreamGetSize(buffHandle)
    (status, buffIndex) = KYFG_StreamGetFrameIndex(buffHandle)
    (buffData,) = KYFG_StreamGetPtr(buffHandle, buffIndex)

    if (Stream_callback_func.copyingDataFlag == 0):
        Stream_callback_func.copyingDataFlag = 1

    print('Good callback buffer handle: ' + str(format(buffHandle, '06x')) + ", current index: " + str(
        buffIndex) + ", total frames: " + str(totalFrames) + "         ", end='\r')
    sys.stdout.flush()

    Stream_callback_func.copyingDataFlag = 0
    return


############################# Callback Function #############################
# ----------------------------------------------------------------------------------------------------------------------#
Stream_callback_func.data = 0
Stream_callback_func.copyingDataFlag = 0
# ----------------------------------------------------------------------------------------------------------------------#
############################# Defines #############################
MAX_BOARDS = 4
handle = [0 for i in range(MAX_BOARDS)]
detectedCameras = []
camHandleArray = [[0 for x in range(0)] for y in range(MAX_BOARDS)]
buffHandle = STREAM_HANDLE()

WIDTH_BIN = 1280
HIEGHT_BIN = 1024
WIDTH_FF = 2560
HIEGHT_FF = 2048

grabberIndex = 0
cameraIndex = 0

num_frames_acq = 1  # 0 -> continues mode


############################# Defines #############################
# ----------------------------------------------------------------------------------------------------------------------#
############################# Control Functions #############################
def printErr(err, msg=""):
    print(msg)
    print("Error description: {0}".format(err))


def connectToGrabber(grabberIndex):
    global handle
    (connected_fghandle,) = KYFG_Open(grabberIndex)
    connected = connected_fghandle.get()
    handle[grabberIndex] = connected
    print("Good connection to grabber " + str(grabberIndex) + ", handle= " + str(format(connected, '02x')))
    return 0


############################# Control Functions #############################
# ----------------------------------------------------------------------------------------------------------------------#
############################# FG script #############################
try:
    ''' 
    initialize -> scan for -> retrive -> connect -> FG 0
    connect -> open connection -> set ROI -> CAM 0 
    '''


    def ConnectFGandCAM(debug_mode=False):
        print("\nInitializing frame grabber...\n")

        # Scan for availible grabbers
        (i1, infosize, i2) = KYFG_Scan()
        print("Number of scan results: " + str(infosize) + '\n')
        for x in range(infosize):
            # (status, dev_name) = KY_DeviceDisplayName(x) - Deprecated
            (status, dev_info) = KY_DeviceInfo(x)
            if (status != FGSTATUS_OK):
                print("Cant retrieve device #" + str(x) + " info")
                continue
            dev_name = dev_info.szDeviceDisplayName
            print("Device " + str(x) + ": " + dev_name)

        # Connect to FG 0
        connection = -1
        try:
            connection = connectToGrabber(grabberIndex)
        except KYException as err:
            print('\n')
            printErr(err, "Could not connect to grabber {0}".format(grabberIndex))
        if (connection == 0):
            (CallbackRegister_status,) = KYFG_CallbackRegister(handle[grabberIndex],
                                                               Stream_callback_func,
                                                               0)
            (KYDeviceEventCallBackRegister_status,) = KYDeviceEventCallBackRegister(handle[grabberIndex],
                                                                                    Device_event_callback_func,
                                                                                    0)
        # Scan for availible cameras
        (CameraScan_status, camHandleArray[grabberIndex]) = KYFG_UpdateCameraList(handle[grabberIndex])
        cams_num = len(camHandleArray[grabberIndex])
        print("Found " + str(cams_num) + " cameras\n");
        # If no cameras found -->  continue
        if (cams_num < 1):
            raise Exception("Please, connect at least one camera to continue")

        # Connect to camera 0
        (KYFG_CameraOpen2_status,) = KYFG_CameraOpen2(camHandleArray[grabberIndex][cameraIndex], None)
        if (KYFG_CameraOpen2_status == FGSTATUS_OK):
            print("Camera 0 was connected successfully")
        else:
            print("Something got wrong while camera connecting")

        if debug_mode:
            (Status, camInfo) = KYFG_CameraInfo(camHandleArray[grabberIndex][0])
            print("master_link: ", str(camInfo.master_link))
            print("link_mask: ", str(camInfo.link_mask))
            print("link_speed: ", str(camInfo.link_speed))
            print("stream_id: ", str(camInfo.stream_id))
            print("deviceVersion: ", str(camInfo.deviceVersion))
            print("deviceVendorName: ", str(camInfo.deviceVendorName))
            print("deviceManufacturerInfo: ", str(camInfo.deviceManufacturerInfo))
            print("deviceModelName: ", str(camInfo.deviceModelName))
            print("deviceID: ", str(camInfo.deviceID))
            print("deviceUserID: ", str(camInfo.deviceUserID))
            print("outputCamera: ", str(camInfo.outputCamera))
            print("virtualCamera: ", str(camInfo.virtualCamera))

        # # Set ROI Width
        # (SetCameraValue_status_width, ) = KYFG_SetCameraValue(camHandleArray[grabberIndex][0],
        #                                                       "Width",
        #                                                       WIDTH_BIN)
        # (GetCameraValueInt_status, width) = KYFG_GetCameraValue(camHandleArray[grabberIndex][0], "Width")
        # if debug_mode:
        #     print("\nWidth SetCameraValue_status_width: " + str(format(SetCameraValue_status_width, '02x')))
        #     print("Returned width: " + str(width))
        # # Set ROI Height
        # (SetCameraValue_status_height, ) = KYFG_SetCameraValue(camHandleArray[grabberIndex][0],
        #                                                        "Height",
        #                                                        HIEGHT_BIN)
        # (GetCameraValueInt_status, height) = KYFG_GetCameraValue(camHandleArray[grabberIndex][0], "Height")
        # if debug_mode:
        #     print("\nSetCameraValueInt_status_height: " + str(format(SetCameraValue_status_height, '02x')))
        #     print("Returned height: " + str(height))

        (StreamCreateAndAlloc_status, buffHandle) = KYFG_StreamCreateAndAlloc(camHandleArray[grabberIndex][0], 1, 0)
        # (CallbackRegister_status) = KYFG_StreamBufferCallbackRegister(buffHandle, Stream_callback_func, py_object(streamInfoStruct))

        return buffHandle


    '''
    start CAM -> take frame data + show frame (if in debug mode) -> stop CAM
    '''


    def GrabIMG(buffHandle, debug_mode=False):
        # Start camera
        (CameraStart_status,) = KYFG_CameraStart(camHandleArray[grabberIndex][cameraIndex],
                                                 buffHandle,
                                                 num_frames_acq)
        if debug_mode:
            print("\nCamera started")

        time.sleep(0.05)  # Without it, maybe it will work.. maybe it won't..

        # Take frame
        imgPTR = KYFG_StreamGetPtr(buffHandle, KYFG_StreamGetFrameIndex(buffHandle)[1])[0]
        imgSIZE = KYFG_StreamGetSize(buffHandle)[0]
        imgMAT = np.zeros(imgSIZE,
                          dtype=c_uint16)  # here we define the bit depth of the image
                                           # note: maybe add an outside control for this parameter

        if debug_mode:
            print(imgPTR)  # pointer to frame
            print(imgMAT.ctypes.data)  # pointer for the frame data to convert to ndarray

        ctypes.memmove(imgMAT.ctypes.data, imgPTR, imgSIZE)
        imgMAT = imgMAT.reshape(HIEGHT_BIN, WIDTH_BIN, -1)  # this is the mat of the grabbed image

        if debug_mode:
            print(imgMAT.shape)  # for sanity check
            print(imgMAT[:][:][0])  # for sanity check
            plt.figure()
            plt.imshow(imgMAT)
            plt.show()  # display the image of debugging

        # stop camera
        print('\r', end='')
        sys.stdout.flush()
        if (num_frames_acq == 0):  # if we are at contiunes mode we need to make the camera stop
            (CameraStop_status,) = KYFG_CameraStop(camHandleArray[grabberIndex][0])

        if debug_mode:
            print("Camera stopped")

        return imgMAT


    ''' 
    disconnect -> FG 0
    disconnect -> CAM 0 
    '''


    def DisconnectFGandCAM():
        # Disconnect camera and FG
        if (len(camHandleArray[grabberIndex]) > 0):
            (KYFG_CameraClose_status,) = KYFG_CameraClose(camHandleArray[grabberIndex][0])
        if (handle[grabberIndex] != 0):
            (CallbackRegister_status,) = KYFG_StreamBufferCallbackUnregister(handle[grabberIndex],
                                                                             Stream_callback_func)
            (KYFG_Close_status,) = KYFG_Close(handle[grabberIndex])
        print("\nFrame grabber disconnected.\n")

except KYException as KYe:
    print(f"KYException occurred:\n{KYe}")
    raise
############################# FG script #############################
# ----------------------------------------------------------------------------------------------------------------------#
