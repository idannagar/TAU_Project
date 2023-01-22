import zaber_motion.binary
from zaber_motion.binary import Connection
from zaber_motion.binary import Device

from zaber_motion import Units
from zaber_motion import Library, DeviceDbSourceType
from zaber_motion import MotionLibException

#----------------------------------------------------------------------------------------------------------------------#
############################# Defines #############################
baud = 9600
port = "COM7"

Library.set_device_db_source(DeviceDbSourceType.FILE, r"C:\Users\admin\PycharmProjects\pythonProject1\EagleEyeProj\CurrentRev\devices-public.sqlite")
############################# Defines #############################
#----------------------------------------------------------------------------------------------------------------------#
class Collimatior():
    def __init__(self, tag, devicePhi, deviceTheta):
        self.tag = tag
        self.theta = deviceTheta
        self.phi = devicePhi

        # home collimator's axes at connection
        self.theta.home()
        self.phi.home()
        if self.tag != "center":
            self.theta.move_absolute(0, unit=Units.ANGLE_DEGREES)
            self.phi.move_absolute(0, unit=Units.ANGLE_DEGREES)
        else:
            self.theta.move_absolute(9126, unit=Units.NATIVE)
            self.phi.move_absolute(504, unit=Units.NATIVE)
        self.theta.wait_until_idle()
        self.phi.wait_until_idle()

        print(f"{self.tag}-> "
              f"theta: {self.theta.get_position(unit=Units.ANGLE_DEGREES)} ; "
              f"phi: {self.phi.get_position(unit=Units.ANGLE_DEGREES)}")
#----------------------------------------------------------------------------------------------------------------------#
'''
input:
output:
functionality:
remarks:
'''
def ConnectAndConfigure():
    connection = None
    try:
        connection = Connection.open_serial_port(port_name=port, baud_rate=baud)
        connection.default_request_timeout = 5000
    except MotionLibException as error:
        print(error)
    listOfDevices = connection.detect_devices(identify_devices=True)
    # build dictinary
    dictCollimators = {
        'top': Collimatior('top', listOfDevices[4], listOfDevices[5]),
        'left': Collimatior('left', listOfDevices[2], listOfDevices[3]),
        'center': Collimatior('center', listOfDevices[0], listOfDevices[1]),
        'right': Collimatior('right', listOfDevices[6], listOfDevices[7]),
        'bottom': Collimatior('bottom', listOfDevices[8], listOfDevices[9])
    }
    print("All collimators are connected and homed")

    return connection, dictCollimators
#----------------------------------------------------------------------------------------------------------------------#
'''
input:
output:
functionality:
remarks: targets is a list that - 
         targets[0] is the theta value to move to
         targets[1] is the phi value to move to 
'''
def MoveAbsolute(collimator, targets):
    collimator.theta.move_absolute(targets[0], unit=Units.ANGLE_DEGREES)
    collimator.phi.move_absolute(targets[1], unit=Units.ANGLE_DEGREES)
    collimator.theta.wait_until_idle()
    collimator.phi.wait_until_idle()

    print(f"{collimator.tag}-> "
          f"theta: {collimator.theta.get_position(unit=Units.ANGLE_DEGREES)} ; "
          f"phi: {collimator.phi.get_position(unit=Units.ANGLE_DEGREES)}")
#----------------------------------------------------------------------------------------------------------------------#
'''
input:
output:
functionality:
remarks: delta is a list that - 
         delta[0] is the amount of theta that needs to be moved
         delta[1] is the amount of phi that needs to be moved 
'''
def MoveRelative(collimator, deltas):
    collimator.theta.move_relative(deltas[0], unit=Units.ANGLE_DEGREES)
    collimator.phi.move_relative(deltas[1], unit=Units.ANGLE_DEGREES)
    collimator.theta.wait_until_idle()
    collimator.phi.wait_until_idle()

    print(f"{collimator.tag}-> "
          f"theta: {collimator.theta.get_position(unit=Units.ANGLE_DEGREES)} ; "
          f"phi: {collimator.phi.get_position(unit=Units.ANGLE_DEGREES)}")
#----------------------------------------------------------------------------------------------------------------------#
'''
input:
output:
functionality:
remarks:
'''
def MoveToStart(collimator):
    if collimator.tag != "center":
        collimator.theta.move_absolute(0, unit=Units.ANGLE_DEGREES)
        collimator.phi.move_absolute(0, unit=Units.ANGLE_DEGREES)
    else:
        collimator.theta.move_absolute(9126, unit=Units.NATIVE)
        collimator.phi.move_absolute(504, unit=Units.NATIVE)
    print(f"{collimator.tag}-> "
          f"theta: {collimator.theta.get_position(unit=Units.ANGLE_DEGREES)} ; "
          f"phi: {collimator.phi.get_position(unit=Units.ANGLE_DEGREES)}")
#----------------------------------------------------------------------------------------------------------------------#
'''
input:
output:
functionality:
remarks:
'''
def DisconnectAndReset(connection):
    connection.close()
#----------------------------------------------------------------------------------------------------------------------#