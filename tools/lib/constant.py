"""Physical constants common to post-processing tools.

CGS units are used unless otherwise stated. The universal constant does not change with the observation source;
Source distance is used to convert upstream imaging settings to angular scale and needs to be modified simultaneously when processing other observation sources."""

G = 6.674e-8  # Gravitational constant, unit cm^3 g^-1 s^-2
C = 2.99792458e10  # Speed of light in cm/s
M_SUN = 1.989e33  # Solar mass in g
M_E = 9.1093837e-28  # Electron mass, unit g
M_P = 1.6726219e-24  # Proton mass, unit g
K_B = 1.380649e-16  # Boltzmann's constant in erg/K
YEAR_SECONDS = 365.0 * 24.0 * 3600.0  # seconds in a year
PC = 3.086e18  # Parsec, unit cm
JY = 1.0e-23  # CGS flux density corresponding to 1 Jy
RAD_TO_UAS = 180.0 / 3.141592653589793 * 3600.0 * 1.0e6  # rad to uas
SOURCE_DISTANCE_PC = 16.9e6  # Source distance in pc; default value corresponds to M87.
