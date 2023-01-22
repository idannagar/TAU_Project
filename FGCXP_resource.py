import KYFGLib
from KYFGLib import *
#----------------------------------------------------------------------------------------------------------------------#
import numpy as np
import matplotlib.pyplot as plt
import ctypes
#----------------------------------------------------------------------------------------------------------------------#
############################# Callback Detection #############################
def Device_event_callback_func(userContext, event):
    if (isinstance(event, KYDEVICE_EVENT_CAMERA_CONNECTION_LOST) == True):
        print("KYDEVICE_EVENT_CAMERA_CONNECTION_LOST_ID event recognized")
        print("event_id: " + str(event.deviceEvent.eventId))
        print("cam_handle: " + format(event.camHandle.get(), '02x'))
        print("device_link: " + str(event.iDeviceLink))
        print("camera_link: " + str(event.iCameraLink))
    elif (isinstance(event, KYDEVICE_EVENT_CAMERA_START) == True):
        print("KYDEVICE_EVENT_CAMERA_START event recognized")
        print("event_id: " + str(event.deviceEvent.eventId))
        print("camHandle: " + format(event.camHandle.get(), '02x'))
    elif (isinstance(event, KYDEVICE_EVENT_SYSTEM_TEMPERATURE) == True):
        print("KYDEVICE_EVENT_SYSTEM_TEMPERATURE event recognized")
        print("event_id: " + str(event.deviceEvent.eventId))
        print("temperatureThresholdId: " + str(event.temperatureThresholdId))
    elif (isinstance(event, KYDEVICE_EVENT_CXP2_HEARTBEAT) == True):
        print("KYDEVICE_EVENT_CXP2_HEARTBEAT event recognized")
        print("event_id: " + str(event.deviceEvent.eventId))
        print("camHandle: " + format(event.camHandle.get(), '02x'))
    elif (isinstance(event, KYDEVICE_EVENT_CXP2_EVENT) == True):
        print("KYDEVICE_EVENT_CXP2_EVENT event recognized")
        print("event_id: " + str(event.deviceEvent.eventId))
        print("camHandle: " + format(event.camHandle.get(), '02x'))
    elif (isinstance(event, KYDEVICE_EVENT_GENCP_EVENT) == True):
        print("KYDEVICE_EVENT_GENCP_EVENT event recognized")
        print("event_id: " + str(event.deviceEvent.eventId))
    elif (isinstance(event, KYDEVICE_EVENT_GIGE_EVENTDATA) == True):
        print("KYDEVICE_EVENT_GIGE_EVENTDATA event recognized")
        print("event_id: " + str(event.deviceEvent.eventId))
    else:
        print("Unknown event recognized")
############################# Callback Detection #############################
#----------------------------------------------------------------------------------------------------------------------#
############################# Callback Function #############################
def Stream_callback_func(buffHandle, userContext):
    if (buffHandle == 0):
        Stream_callback_func.copyingDataFlag = 0
        return

    streamInfo = cast(userContext, py_object).value
    # print('buffer ' + str(format(buffHandle, '02x')) + ': height=' + str(streamInfo.height) + ', width=' + str(
    #    streamInfo.width) + ', callback count=' + str(streamInfo.callbackCount))
    streamInfo.callbackCount = streamInfo.callbackCount + 1

    (KYFG_BufferGetInfo_status, pInfoBase, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_BASE)  # PTR
    (KYFG_BufferGetInfo_status, pInfoPTR, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_USER_PTR)  # PTR
    (KYFG_BufferGetInfo_status, pInfoTimestamp, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_TIMESTAMP)  # UINT64
    (KYFG_BufferGetInfo_status, pInfoFPS, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_INSTANTFPS)  # FLOAT64
    (KYFG_BufferGetInfo_status, pInfoID, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_ID)  # UINT32
    # print("KYFG_BufferGetInfo_status: " + str(format(KYFG_BufferGetInfo_status, '02x')))
    print(
        "Buffer Info: Base " + str(pInfoBase) + ", Size " + str(pInfoSize) + ", Timestamp " + str(
            pInfoTimestamp) + ", FPS " + str(pInfoFPS)
        + ", ID " + str(pInfoID), end='\r')

    if (Stream_callback_func.copyingDataFlag == 0):
        Stream_callback_func.copyingDataFlag = 1

    sys.stdout.flush()
    Stream_callback_func.copyingDataFlag = 0
    return
############################# Callback Function #############################
#----------------------------------------------------------------------------------------------------------------------#
Stream_callback_func.data = 0
Stream_callback_func.copyingDataFlag = 0
#----------------------------------------------------------------------------------------------------------------------#
############################# Classes #############################
class StreamInfoStruct:
    def __init__(self):
        self.width = 640
        self.height = 480
        self.callbackCount = 0
        return
############################# Classes #############################
#----------------------------------------------------------------------------------------------------------------------#
############################# Defines #############################
MAX_BOARDS = 4
handle = [0 for i in range(MAX_BOARDS)]
detectedCameras = []
grabberIndex = 0
camHandleArray = [[] for y in range(MAX_BOARDS)]
buffHandle = STREAM_HANDLE()

# Create an instance of 'StreamInfoStruct' struct and pass it later to KYFG_StreamBufferCallbackRegister function as userContext
streamInfoStruct = StreamInfoStruct()
############################# Defines #############################
#----------------------------------------------------------------------------------------------------------------------#
############################# Control Functions #############################
def printErr(err, msg=""):
    print(msg)
    print("Error description: {0}".format(err))

def connectToGrabber(grabberIndex):
    global handle
    (connected_fghandle,) = KYFG_Open(grabberIndex)
    connected = connected_fghandle.get()
    handle[grabberIndex] = connected
    (status, tested_dev_info) = KYFGLib.KY_DeviceInfo(grabberIndex)
    print("Good connection to grabber " + str(grabberIndex) + ": " + tested_dev_info.szDeviceDisplayName + ", handle= " + str(format(connected, '02x')))
    return 0
############################# Control Functions #############################
#----------------------------------------------------------------------------------------------------------------------#
############################# FG script #############################
try:
    ''' 
    initialize -> scan for -> retrive -> connect -> FG 0
    connect -> open connection -> set ROI -> CAM 0 
    '''
    def ConnectFGandCAM(debug_mode = False):
        print("\nInitializing frame grabber...\n")
        # Initialize grabber parameters
        initParams = KYFGLib_InitParameters()
        KYFGLib_Initialize(initParams)
        # Scan for availible grabbers
        (KYFG_Scan_status, fgAmount) = KY_DeviceScan()
        if debug_mode:
            if (KYFG_Scan_status != FGSTATUS_OK):
                print("KY_DeviceScan() status: " + str(format(KYFG_Scan_status, '02x')))
            # Print available grabbers params
            for x in range(fgAmount):
                (status, dev_info) = KYFGLib.KY_DeviceInfo(x)
                if (status != FGSTATUS_OK):
                    print("Cant retrieve device #" + str(x) + " info")
                    continue
                print("Device " + str(x) + ": " + dev_info.szDeviceDisplayName)
        # Retrive FG 0 - the only one connected
        if debug_mode:
            print("Selected grabber: " + str(grabberIndex))
            print("\nGetting info about the grabber: ")
            (status, dev_info) = KY_DeviceInfo(grabberIndex)
            if (status != FGSTATUS_OK):
                raise Exception("Cant retrieve device #" + str(grabberIndex) + " info")
            else:
                print("DeviceDisplayName: " + dev_info.szDeviceDisplayName)
                print("Bus: " + str(dev_info.nBus))
                print("Slot: " + str(dev_info.nSlot))
                print("Function: " + str(dev_info.nFunction))
                print("DevicePID: " + str(dev_info.DevicePID))
                print("isVirtual: " + str(dev_info.isVirtual))
        # Connect to FG
        connection = -1
        try:
            connection = connectToGrabber(grabberIndex)
        except KYException as err:
            print('\n')
            printErr(err, "Could not connect to grabber {0}".format(grabberIndex))
        if (connection == 0):
            (KYDeviceEventCallBackRegister_status,) = KYDeviceEventCallBackRegister(handle[grabberIndex], Device_event_callback_func, 0)
        # Connect to camera 0 - the only one connected
        (CameraScan_status, camHandleArray[grabberIndex]) = KYFG_UpdateCameraList(handle[grabberIndex])
        cams_num = len(camHandleArray[grabberIndex])
        if debug_mode:
            print("Found " + str(cams_num) + " cameras\n");
            # If no cameras found -->  continue
            if (cams_num < 1):
                raise Exception("Please, connect at least one camera to continue")
        # open a connection to camera 0
        (KYFG_CameraOpen2_status,) = KYFG_CameraOpen2(camHandleArray[grabberIndex][0], None)
        if debug_mode:
            if (KYFG_CameraOpen2_status == FGSTATUS_OK):
                print("Camera 0 was connected successfully")
            else:
                print("Something got wrong while camera connecting")
        if debug_mode:
            (Status, camInfo) = KYFG_CameraInfo2(camHandleArray[grabberIndex][0])
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
        # Set ROI Width
        (SetCameraValue_status_width,) = KYFG_SetCameraValue(camHandleArray[grabberIndex][0], "Width",
                                                             streamInfoStruct.width)
        if debug_mode:
            print("\nWidth SetCameraValue_status_width: " + str(format(SetCameraValue_status_width, '02x')))
        (GetCameraValueInt_status, width) = KYFG_GetCameraValue(camHandleArray[grabberIndex][0], "Width")
        if debug_mode:
            print("Returned width: " + str(width))
        # Set ROI Height
        (SetCameraValue_status_height,) = KYFG_SetCameraValue(camHandleArray[grabberIndex][0], "Height",
                                                              streamInfoStruct.height)
        if debug_mode:
            print("\nSetCameraValueInt_status_height: " + str(format(SetCameraValue_status_height, '02x')))
        (GetCameraValueInt_status, height) = KYFG_GetCameraValue(camHandleArray[grabberIndex][0], "Height")
        if debug_mode:
            print("Returned height: " + str(height))
        (StreamCreateAndAlloc_status, buffHandle) = KYFG_StreamCreateAndAlloc(camHandleArray[grabberIndex][0], 1, 0)
        (CallbackRegister_status) = KYFG_StreamBufferCallbackRegister(buffHandle, Stream_callback_func, py_object(streamInfoStruct))

        return buffHandle
    '''
    start CAM -> take frame data + show frame (if in debug mode) -> stop CAM
    '''
    def GrabIMG(buffHandle, debug_mode = False):
        # Start camera
        num_frames_acq = 1  # 0 -> continues mode
        (CameraStart_status,) = KYFG_CameraStart(camHandleArray[grabberIndex][0], buffHandle, num_frames_acq)
        if debug_mode:
            print("\nCamera started")
        time.sleep(0.05)  # Without it, maybe it will work.. maybe it won't..
        # Take frame
        imgPTR = KYFG_StreamGetPtr(buffHandle, KYFG_StreamGetFrameIndex(buffHandle)[1])[0]
        imgSIZE = KYFG_StreamGetSize(buffHandle)[0]
        imgMAT = np.zeros(imgSIZE, dtype=c_uint8) # here we define the bit depth of the image # note: maybe add an outside control for this parameter
        if debug_mode:
            print(imgPTR)  # pointer to frame
            print(imgMAT.ctypes.data)  # pointer for the frame data to convert to ndarray
        ctypes.memmove(imgMAT.ctypes.data, imgPTR, imgSIZE)
        imgMAT = imgMAT.reshape(streamInfoStruct.height, streamInfoStruct.width, -1)  # this is the mat of the grabbed image
        if debug_mode:
            print(imgMAT.shape)  # for sanity check
            print(imgMAT[:][:][0])  # for sanity check
            plt.imshow(imgMAT)
            plt.show() # display the image of debugging
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
    def DisconnectFGandCAM(debug_mode = False):
        # Disconnect camera and FG
        if (len(camHandleArray[grabberIndex]) > 0):
            (KYFG_CameraClose_status,) = KYFG_CameraClose(camHandleArray[grabberIndex][0])
        if (handle[grabberIndex] != 0):
            (CallbackRegister_status,) = KYFG_StreamBufferCallbackUnregister(handle[grabberIndex], Stream_callback_func)
            (KYFG_Close_status,) = KYFG_Close(handle[grabberIndex])
        print("\nFrame grabber disconnected.\n")

except KYException as KYe:
    print("KYException occurred: ")
    raise
############################# FG script #############################
#----------------------------------------------------------------------------------------------------------------------#

