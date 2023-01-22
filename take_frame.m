% This is a Matlab function that is used by the main python script to acquire an image
% for the detector.
% The function connects to the frame grabber, configures the video settings, acquires
% a frame (or a set of frames) and saves the average to a variable that will be transfered
% to the main python script for further analysis. 
function [frame] = take_frame()
% connect to the frame grabber and configure the video settings 
vidobj = videoinput("dalsa", 1, "D:\Eagles_eye\config_files\BB1280_proxy_full_1280x1024.ccf");
triggerconfig(vidobj, 'manual')
frameAmount = 1; % can be changed to a higher value, and then the mean operation is meaningful 
vidobj.FramesPerTrigger = frameAmount; 
% acquire the frame(or frames) from the detector 
start(vidobj) 
trigger(vidobj)
data = getdata(vidobj, frameAmount, 'uint16', 'numeric'); 
stop(vidobj)
% save the data in "frame" to be passed to the python script 
frame = mean(data, 4);
% disconnect from the grabber and clear the local data in the Matlab workspace
delete(vidobj)
clear vidobj
clear all 
end