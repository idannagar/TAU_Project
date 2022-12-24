function main()



%% Problem 1 : Mie Solution (Reference Solution)
% Problem 1.1 : Current Distribution


% Problem 1.2 : Bi-static Radar Cross Section (RCS)
[k, a, radius, phi, phiIncident, N] = getDefaultCfg_sectionValues('Problem 1.2');
[sigma] = getRCS(k, phi, phiIncident, radius, N, 'E Polarization');
[sigma] = getRCS(k, phi, phiIncident, radius, N, 'H Polarization');

% Problem 1.3 : Mono-static Radar Cross Section (RCS)
[k, a, radius, phi, phiIncident, N] = getDefaultCfg_sectionValues('Problem 1.3');
[sigma] = getRCS(k, phi, phiIncident, radius, N, 'E Polarization');
[sigma] = getRCS(k, phi, phiIncident, radius, N, 'H Polarization');


%% Problem 2: A numeric MoM solution
% Problem 2.1 : Current Distribution


% Problem 2.2 : mono-static Radar Cross Section (RCS)


%% Problem 3 : Physical optics (PO) and geometrical optics (GO) approximations
% Problem 3.1 - PO approximation


% Problem 3.2 - GO approximation

end