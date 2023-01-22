function [frame] = GrabIMG(vidobjPath, isNUC)
vidobj = load(vidobjPath).vidobj; 
% acquire the frame(or frames) from the detector 
start(vidobj) 
trigger(vidobj)
data = getdata(vidobj, 1, 'uint16', 'numeric'); 
stop(vidobj)
% save the data in "frame" to be passed to the python script 
if(isNUC == true)
    frame = NUC(data); 
else
    frame = data;
end
end