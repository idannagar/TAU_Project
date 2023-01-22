function [frame] = GrabIMGMean(vidobjPath, amount, isNUC)
vidobj = load(vidobjPath).vidobj; 
% acquire the frame(or frames) from the detector 
vidobj.FramesPerTrigger = amount;
start(vidobj) 
trigger(vidobj)
data = getdata(vidobj, amount, 'uint16', 'numeric'); 
stop(vidobj)
% save the data in "frame" to be passed to the python script 
data = mean(data, 4);
if(isNUC == true)
    frame = NUC(data); 
else
    frame = data;
end