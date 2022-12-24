function [k, phi] = checkValues(k, phi, N)

if ~iscolumn(k)
    k = k';
end
if iscolumn(phi)
    phi = phi';
end
if N > 100
    error('Error: N should not exceed 100!')
end

end

