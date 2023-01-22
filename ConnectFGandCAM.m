function [vidobjPath] = ConnectFGandCAM()
% connect to the frame grabber and configure the video settings 
vidobj = videoinput("dalsa", 1, "C:\Users\admin\Documents\BB1280_proxy_full_1280x1024.ccf");
triggerconfig(vidobj, 'manual')
vidobj.FramesPerTrigger = 1;
vidobj.PreviewFullBitDepth = 'on';
save("vidobj.mat", "vidobj")

vidobjPath = fullfile(pwd(), "vidobj.mat");
end