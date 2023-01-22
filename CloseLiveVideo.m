function [a] = CloseLiveVideo(vidobjPath)
vidobj = load(vidobjPath).vidobj; 
closepreview(vidobj)
a = 0; 
end