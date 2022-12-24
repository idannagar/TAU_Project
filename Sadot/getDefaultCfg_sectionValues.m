function varargout = getDefaultCfg_sectionValues(section)

switch lower(section)
    case lower('Problem 1.1')
        k           = [0.1 0.5 1 5 10];
        k           = linspace(0.1,20,1000);
        a           = 1;
        radius      = 1;
        phi         = linspace(0, pi, 1000);
        phiIncident = 0;
        N           = 100;
        varargout = {};
    case lower('Problem 1.2')
        k           = [0.1 0.5 1 5 10];
        a           = 1;
        radius      = 1;
        phi         = linspace(0, pi, 1000);
        phiIncident = 0;
        N           = 100;
        varargout = {k, a, radius, phi, phiIncident, N};
    case lower('Problem 1.3')
        k           = linspace(0.1,20,1000);
        a           = 1;
        radius      = 1;
        phi         = 0;
        phiIncident = 0;
        N           = 100;
        varargout = {k, a, radius, phi, phiIncident, N};
end