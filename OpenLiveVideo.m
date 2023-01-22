function [h, a] = OpenLiveVideo(vidobjPath)
vidobj = load(vidobjPath).vidobj; 

vidRes = get(vidobj, 'VideoResolution');
W = vidRes(1);
H = vidRes(2);
nBands = get(vidobj, 'NumberOfBands');
himage = image(zeros(H, W, nBands));

% % option #1 
% setappdata(himage, 'FrameAcquiredFcn', @fcn);

% option #2
im = preview(vidobj, himage);
ax = im.Parent;
im.CDataMapping = 'scaled';
ax.CLim = [2500, 5000];
frame = NUC(im.CData);
set(himage, 'CData', frame);
h = frame;

% % original
% h = preview(vidobj, himage);
% % h = preview(vidobj);
% a = ancestor(h, 'axes');
% set(h, 'CDataMapping', 'Scaled');
% set(a, 'CLim', [3000, 6000]); 

end

% function fcn(obj, event, himage)
%     data  = event.Data;
%     frame = NUC(data);
%     set(himage, 'CData', frame);
% end