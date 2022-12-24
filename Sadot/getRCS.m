function [sigma] = getRCS(k, phi, phiIncident, radius, N, mode)
% inputs:
%   mode - get RCS of E Polarization or H Polarization
%   N    - number of samples of the 'infinte' sum

sigma    = 0;
[k, phi] = checkValues(k, phi, N);
epsilon  = [1 2*ones(1,N-1)];

switch lower(mode)
    case lower('E Polarization')
        for n = 0:N-1
            J = besselj(n, k * radius);
            H = besselh(n, 2, k * radius);
            sigma = sigma + ...
                epsilon(n+1) * (-1)^n .* J ./ H * cos(n .* (phi-phiIncident));
        end
    case lower('H Polarization')
        for n = 0:N-1
            dJ = 0.5 * (besselj(n-1, k * radius) - besselj(n+1, k * radius));
            dH = 0.5 * (besselh(n-1, k * radius) - besselh(n+1, k * radius));
            sigma = sigma + ...
                epsilon(n+1) * (-1)^n .* dJ ./ dH * cos(n .* (phi-phiIncident));
        end        
        
end
sigma = (abs(sigma)).^2;
sigma = sigma .* 4 ./ k ;


end

