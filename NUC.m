function [corrected] = NUC(frame)

gain = load("gain_table.mat").Gain;
offset = load("offset_table.mat").Offset;

corrected = uint16(gain .* double(frame) + offset);

end