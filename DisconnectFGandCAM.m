function [a] = DisconnectFGandCAM(vidobjPath)
vidobj = load(vidobjPath).vidobj;
% disconnect from the grabber and clear the local data in the Matlab workspace
delete(vidobj)
clear vidobj
clear all 
a = 0; 
end